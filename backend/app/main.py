import logging
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import build_webhook_response, webhook_secret_matches
from app.config import settings
from app.database import engine, get_session
from app.models import Application
from app.schemas import ApplicationCreate, ApplicationCreated, HealthResponse
from app.telegram import TelegramUser, application_rate_limiter, require_telegram_user

logger = logging.getLogger("closedclub.api")

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    try:
        async with engine.connect() as connection:
            await connection.execute(select(1))
    except SQLAlchemyError as exc:
        logger.warning("Database health check failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc

    return HealthResponse(status="ok", database="ok")


@app.post(
    "/api/telegram/webhook",
    include_in_schema=False,
    response_model=None,
)
async def telegram_webhook(
    update: dict[str, Any],
    telegram_secret: Annotated[
        str | None,
        Header(alias="X-Telegram-Bot-Api-Secret-Token"),
    ] = None,
) -> dict[str, Any] | Response:
    expected_secret = settings.telegram_webhook_secret.get_secret_value()
    if not webhook_secret_matches(telegram_secret, expected_secret):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook secret",
        )

    bot_response = build_webhook_response(
        update,
        str(settings.telegram_web_app_url),
    )
    if bot_response is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return bot_response


@app.post(
    "/api/applications",
    response_model=ApplicationCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_application(
    payload: ApplicationCreate,
    telegram_user: TelegramUser = Depends(require_telegram_user),
    session: AsyncSession = Depends(get_session),
) -> Application:
    await application_rate_limiter.check(telegram_user.id)

    application = Application(
        **payload.model_dump(),
        telegram_user_id=telegram_user.id,
        telegram_username=telegram_user.username,
    )
    session.add(application)

    try:
        await session.commit()
        await session.refresh(application)
    except SQLAlchemyError as exc:
        await session.rollback()
        logger.error("Failed to persist an application: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application storage is temporarily unavailable",
        ) from exc

    return application
