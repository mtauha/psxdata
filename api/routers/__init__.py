from fastapi import APIRouter

from api.routers.health import router as health_router
from api.routers.indices import router as indices_router
from api.routers.market import router as market_router
from api.routers.sectors import router as sectors_router
from api.routers.stocks import router as stocks_router

router_registry: list[APIRouter] = [
    health_router,
    stocks_router,
    indices_router,
    sectors_router,
    market_router,
]
