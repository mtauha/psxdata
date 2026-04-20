from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import router_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


for router in router_registry:
    # TODO: first router PR should populate router_registry.
    app.include_router(router)
