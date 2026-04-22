from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.routers import router_registry
from psxdata.exceptions import InvalidSymbolError, PSXUnavailableError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan — startup and shutdown events."""
    # TODO: initialise cache / Redis on startup, close on shutdown.
    yield


app = FastAPI(title="psxdata", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # TODO: replace wildcard origin with explicit origins before production.
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_ERROR_CODES: dict[int, str] = {
    400: "bad_request",
    404: "not_found",
    422: "bad_request",
    429: "rate_limited",
    503: "psx_unavailable",
    500: "internal_error",
}


@app.exception_handler(PSXUnavailableError)
async def psx_unavailable_handler(request: Request, exc: PSXUnavailableError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": {"status": 503, "code": _ERROR_CODES[503], "message": str(exc)}},
    )


@app.exception_handler(InvalidSymbolError)
async def invalid_symbol_handler(request: Request, exc: InvalidSymbolError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": {"status": 404, "code": _ERROR_CODES[404], "message": str(exc)}},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _ERROR_CODES.get(exc.status_code, "internal_error")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"status": exc.status_code, "code": code, "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    parts = []
    for e in exc.errors():
        loc = " -> ".join(str(part) for part in e.get("loc", []) if part != "body")
        msg = e.get("msg", "invalid value")
        parts.append(f"{loc}: {msg}" if loc else msg)
    message = "; ".join(parts) if parts else "invalid input"
    return JSONResponse(
        status_code=422,
        content={"error": {"status": 422, "code": "bad_request", "message": message}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"status": 500, "code": "internal_error", "message": "Internal Server Error"}},  # noqa: E501
    )


for router in router_registry:
    app.include_router(router)
