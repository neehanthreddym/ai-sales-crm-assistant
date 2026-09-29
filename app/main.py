from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.leads import router as leads_router
from app.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    yield
    service = getattr(app.state, "lead_service", None)
    if service is not None:
        await service.aclose()


app = FastAPI(
    title="AI Sales CRM Assistant",
    version="0.1.0",
    description="Human-reviewed AI assistance for synthetic automotive sales leads.",
    lifespan=lifespan,
)
app.include_router(health_router)
app.include_router(leads_router)


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    get_logger().warning(
        "request_failed",
        path=request.url.path,
        error_code=exc.code,
        http_status=exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.public_message}},
    )
