```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter middleware
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    Limiter,
    key_func=get_remote_address,
    default_limits=["60/minute"]
)

# Add global exception handler
@app.exception_handler(Exception)
async def catch_all_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=400, content={"error": str(exc), "status": 400})

# Wire up router includes (empty stubs initially)
from api.routers import *

# Lifespan context manager
@app.on_event("startup")
async def startup_event():
    pass

@app.on_event("shutdown")
async def shutdown_event():
    pass
```