import asyncio
import hashlib
import hmac
import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException, status

from app.config import settings


@dataclass(frozen=True, slots=True)
class TelegramUser:
    id: int
    username: str | None


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Telegram authorization",
    )


def validate_init_data(init_data: str) -> TelegramUser:
    if not init_data:
        raise _unauthorized()

    try:
        values = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
        received_hash = values.pop("hash")
        auth_date = int(values["auth_date"])
        user_data = json.loads(values["user"])
        user_id = int(user_data["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise _unauthorized() from exc

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(values.items()))
    secret_key = hmac.new(
        b"WebAppData",
        settings.telegram_bot_token.get_secret_value().encode(),
        hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise _unauthorized()

    now = int(time.time())
    if auth_date > now + 30 or now - auth_date > settings.telegram_auth_max_age_seconds:
        raise _unauthorized()

    if user_id <= 0:
        raise _unauthorized()

    username = user_data.get("username")
    if not isinstance(username, str) or not username:
        username = None

    return TelegramUser(id=user_id, username=username[:64] if username else None)


async def require_telegram_user(
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> TelegramUser:
    return validate_init_data(x_telegram_init_data or "")


class ApplicationRateLimiter:
    def __init__(self, limit: int = 3, window_seconds: int = 3600) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[int, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, user_id: int) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        async with self._lock:
            requests = self._requests[user_id]
            while requests and requests[0] < cutoff:
                requests.popleft()

            if len(requests) >= self.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many applications",
                )

            requests.append(now)


application_rate_limiter = ApplicationRateLimiter()
