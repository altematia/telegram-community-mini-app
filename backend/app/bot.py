import hmac
from typing import Any


WELCOME_TEXT = (
    "Добро пожаловать в ClosedClub — закрытое инвестиционное сообщество.\n\n"
    "Нажмите кнопку ниже, чтобы открыть приложение и оставить заявку."
)

ADMIN_TEXT = (
    "Админ-панель пока не подключена. Сейчас доступна заявка на вступление в "
    "ClosedClub."
)


def webhook_secret_matches(provided: str | None, expected: str) -> bool:
    try:
        provided_bytes = (provided or "").encode("ascii")
        expected_bytes = expected.encode("ascii")
    except UnicodeEncodeError:
        return False

    return hmac.compare_digest(provided_bytes, expected_bytes)


def build_webhook_response(
    update: dict[str, Any],
    web_app_url: str,
) -> dict[str, Any] | None:
    """Build a Bot API method response for a Telegram webhook update."""

    message = update.get("message")
    if not isinstance(message, dict):
        return None

    sender = message.get("from")
    chat = message.get("chat")
    text = message.get("text")

    if (
        not isinstance(sender, dict)
        or sender.get("is_bot") is True
        or not isinstance(chat, dict)
        or chat.get("type") != "private"
        or not isinstance(chat.get("id"), int)
        or not isinstance(text, str)
    ):
        return None

    stripped_text = text.strip()
    if not stripped_text:
        return None

    command = (
        stripped_text.split(maxsplit=1)[0].split("@", maxsplit=1)[0].casefold()
    )
    if command not in {"/start", "/help", "/admin"}:
        return None

    response: dict[str, Any] = {
        "method": "sendMessage",
        "chat_id": chat["id"],
        "text": ADMIN_TEXT if command == "/admin" else WELCOME_TEXT,
    }
    if command != "/admin":
        response["reply_markup"] = {
            "inline_keyboard": [
                [
                    {
                        "text": "Открыть ClosedClub",
                        "web_app": {"url": web_app_url},
                    }
                ]
            ]
        }

    return response
