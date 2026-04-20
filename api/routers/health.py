from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", response_model=dict[str, str])
def health() -> dict[str, str]:
    return {"status": "ok"}
