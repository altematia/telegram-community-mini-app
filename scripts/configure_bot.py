#!/usr/bin/env python3
"""Configure the ClosedClub bot without exposing its token in command output."""

from __future__ import annotations

import argparse
import getpass
import http.client
import json
import os
import socket
import ssl
import string
import sys
import time
import urllib.parse
from functools import partial
from typing import Any


BOT_NAME = "ClosedClub"
BOT_DESCRIPTION = (
    "Закрытое инвестиционное сообщество. Откройте приложение и оставьте заявку."
)
BOT_SHORT_DESCRIPTION = "Заявка в закрытое инвестиционное сообщество."


def bot_api_call(
    token: str,
    method: str,
    payload: dict[str, Any],
    *,
    source_address: str | None = None,
) -> Any:
    tls_context = ssl.create_default_context()
    connection = http.client.HTTPSConnection(
        "api.telegram.org",
        timeout=30,
        context=tls_context,
    )
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    path = f"/bot{urllib.parse.quote(token, safe=':_-')}/{method}"

    try:
        telegram_ipv4 = socket.gethostbyname("api.telegram.org")
        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_socket.settimeout(30)
        if source_address:
            raw_socket.bind((source_address, 0))
        try:
            raw_socket.connect((telegram_ipv4, 443))
            connection.sock = tls_context.wrap_socket(
                raw_socket,
                server_hostname="api.telegram.org",
            )
        except BaseException:
            raw_socket.close()
            raise

        connection.request(
            "POST",
            path,
            body=body,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        response_body = response.read()
        try:
            result = json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise RuntimeError(f"{method}: HTTP {response.status}") from None
    except (OSError, TimeoutError) as exc:
        raise RuntimeError(f"Telegram API request failed for {method}") from exc
    finally:
        connection.close()

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
        "--webhook-url",
        default=os.environ.get("TELEGRAM_WEBHOOK_URL"),
        help="Public HTTPS Telegram webhook endpoint",
    )
    parser.add_argument(
        "--drop-pending-updates",
        action="store_true",
        help="Discard updates queued before webhook registration",
    )
    parser.add_argument(
        "--source-address",
        help="Local IPv4 address used for outbound Bot API connections",
    )
    args = parser.parse_args()

    if not args.web_app_url:
        parser.error("--web-app-url or TELEGRAM_WEB_APP_URL is required")

    if not args.webhook_url:
        parser.error("--webhook-url or TELEGRAM_WEBHOOK_URL is required")

    parsed_webhook_url = urllib.parse.urlparse(args.webhook_url)
    try:
        webhook_port = parsed_webhook_url.port
    except ValueError:
        parser.error("--webhook-url contains an invalid port")
    if (
        parsed_webhook_url.scheme != "https"
        or not parsed_webhook_url.hostname
        or parsed_webhook_url.username is not None
        or parsed_webhook_url.password is not None
        or webhook_port not in (None, 443)
        or parsed_webhook_url.path != "/api/telegram/webhook"
        or parsed_webhook_url.params
        or parsed_webhook_url.query
        or parsed_webhook_url.fragment
    ):
        parser.error(
            "--webhook-url must be an HTTPS URL on port 443 with the exact "
            "path /api/telegram/webhook and no query or fragment"
        )

    token = read_secret("TELEGRAM_BOT_TOKEN", "Telegram bot token: ")
    webhook_secret = read_secret(
        "TELEGRAM_WEBHOOK_SECRET",
        "Telegram webhook secret: ",
    )
    validate_webhook_secret(webhook_secret)
    api = partial(
        bot_api_call,
        token,
        source_address=args.source_address,
    )

    web_app_url = require_https_url(args.web_app_url)
    webhook_url = args.webhook_url
    web_app_button = {
        "type": "web_app",
        "text": "Открыть ClosedClub",
        "web_app": {"url": web_app_url},
    }

    api("setMyName", {"name": BOT_NAME})
    api("setMyDescription", {"description": BOT_DESCRIPTION})
    api(
        "setMyShortDescription",
        {"short_description": BOT_SHORT_DESCRIPTION},
    )
    api(
        "setMyCommands",
        {
            "commands": [
                {"command": "start", "description": "Открыть ClosedClub"},
                {"command": "help", "description": "Помощь"},
            ]
        },
    )
    api("setChatMenuButton", {"menu_button": web_app_button})
    webhook_configured_at = int(time.time())
    api(
        "setWebhook",
        {
            "url": webhook_url,
            "secret_token": webhook_secret,
            "allowed_updates": ["message"],
            "max_connections": 4,
            "drop_pending_updates": args.drop_pending_updates,
        },
    )

    bot = api("getMe", {})
    menu = api("getChatMenuButton", {})
    webhook = api("getWebhookInfo", {})

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
