from fastapi import APIRouter

from api.routers.health import router as health_router
from api.routers.indices import router as indices_router
from api.routers.stocks import router as stocks_router

router_registry: list[APIRouter] = [health_router, stocks_router, indices_router]
