from fastapi import APIRouter

from api.routers.health import router as health_router

router_registry: list[APIRouter] = [health_router]
