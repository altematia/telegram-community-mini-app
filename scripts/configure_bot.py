#!/usr/bin/env python3
"""Configure the ClosedClub bot without exposing its token in command output."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import string
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


BOT_NAME = "ClosedClub"
BOT_DESCRIPTION = (
    "Закрытое инвестиционное сообщество. Откройте приложение и оставьте заявку."
)
BOT_SHORT_DESCRIPTION = "Заявка в закрытое инвестиционное сообщество."


def bot_api_call(token: str, method: str, payload: dict[str, Any]) -> Any:
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Telegram API request failed for {method}") from exc

    if not result.get("ok"):
        description = result.get("description", "unknown Telegram API error")
        raise RuntimeError(f"{method}: {description}")

    return result.get("result")


def require_https_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise argparse.ArgumentTypeError("Web App URL must be an absolute HTTPS URL")
    return value.rstrip("/") + "/"


def read_secret(name: str, prompt: str) -> str:
    value = os.environ.get(name) or getpass.getpass(prompt)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def validate_webhook_secret(secret: str) -> None:
    allowed = set(string.ascii_letters + string.digits + "_-")
    if not 32 <= len(secret) <= 256 or any(char not in allowed for char in secret):
        raise SystemExit(
            "TELEGRAM_WEBHOOK_SECRET must be 32-256 URL-safe characters"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--web-app-url",
        type=require_https_url,
        default=os.environ.get("TELEGRAM_WEB_APP_URL"),
        help="Public HTTPS URL of the ClosedClub Mini App",
    )
    parser.add_argument(
        "--drop-pending-updates",
        action="store_true",
        help="Discard updates queued before webhook registration",
    )
    args = parser.parse_args()

    if not args.web_app_url:
        parser.error("--web-app-url or TELEGRAM_WEB_APP_URL is required")

    token = read_secret("TELEGRAM_BOT_TOKEN", "Telegram bot token: ")
    webhook_secret = read_secret(
        "TELEGRAM_WEBHOOK_SECRET",
        "Telegram webhook secret: ",
    )
    validate_webhook_secret(webhook_secret)

    web_app_url = require_https_url(args.web_app_url)
    webhook_url = f"{web_app_url.rstrip('/')}/api/telegram/webhook"
    web_app_button = {
        "type": "web_app",
        "text": "Открыть ClosedClub",
        "web_app": {"url": web_app_url},
    }

    bot_api_call(token, "setMyName", {"name": BOT_NAME})
    bot_api_call(token, "setMyDescription", {"description": BOT_DESCRIPTION})
    bot_api_call(
        token,
        "setMyShortDescription",
        {"short_description": BOT_SHORT_DESCRIPTION},
    )
    bot_api_call(
        token,
        "setMyCommands",
        {
            "commands": [
                {"command": "start", "description": "Открыть ClosedClub"},
                {"command": "help", "description": "Помощь"},
            ]
        },
    )
    bot_api_call(token, "setChatMenuButton", {"menu_button": web_app_button})
    webhook_configured_at = int(time.time())
    bot_api_call(
        token,
        "setWebhook",
        {
            "url": webhook_url,
            "secret_token": webhook_secret,
            "allowed_updates": ["message"],
            "max_connections": 4,
            "drop_pending_updates": args.drop_pending_updates,
        },
    )

    bot = bot_api_call(token, "getMe", {})
    menu = bot_api_call(token, "getChatMenuButton", {})
    webhook = bot_api_call(token, "getWebhookInfo", {})

    print(f"Bot: @{bot.get('username', 'unknown')} ({bot.get('first_name', BOT_NAME)})")
    print(
        "Menu: "
        f"{menu.get('type', 'unknown')} -> "
        f"{menu.get('web_app', {}).get('url', 'missing')}"
    )
    print(
        "Webhook: "
        f"{webhook.get('url', 'missing')}; "
        f"pending={webhook.get('pending_update_count', 0)}"
    )
    if webhook.get("last_error_message"):
        print(f"Webhook last error: {webhook['last_error_message']}", file=sys.stderr)
        if webhook.get("last_error_date", 0) >= webhook_configured_at:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
