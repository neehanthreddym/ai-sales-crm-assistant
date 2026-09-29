from fastapi import APIRouter

router = APIRouter()


@router.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "name": "AI Sales CRM Assistant",
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
