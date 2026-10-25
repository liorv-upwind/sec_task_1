from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/info")
def info(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"name": settings.app_name, "environment": settings.app_env}
