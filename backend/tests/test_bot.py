import unittest

from app.bot import (
    ADMIN_TEXT,
    WELCOME_TEXT,
    build_webhook_response,
    webhook_secret_matches,
)


WEB_APP_URL = "https://109.172.6.81/"


def message_update(text: str, *, chat_type: str = "private") -> dict:
    return {
        "update_id": 1,
        "message": {
            "message_id": 2,
            "from": {"id": 10, "is_bot": False},
            "chat": {"id": 10, "type": chat_type},
            "text": text,
        },
    }


class BuildWebhookResponseTests(unittest.TestCase):
    def test_start_returns_web_app_button(self) -> None:
        response = build_webhook_response(message_update("/start"), WEB_APP_URL)

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["method"], "sendMessage")
        self.assertEqual(response["chat_id"], 10)
        self.assertEqual(response["text"], WELCOME_TEXT)
        self.assertEqual(
            response["reply_markup"]["inline_keyboard"][0][0]["web_app"]["url"],
            WEB_APP_URL,
        )

    def test_command_suffix_and_payload_are_supported(self) -> None:
        response = build_webhook_response(
            message_update("/start@tgwebappp_bot referral"),
            WEB_APP_URL,
        )

        self.assertIsNotNone(response)

    def test_admin_explains_that_admin_panel_is_not_available(self) -> None:
        response = build_webhook_response(message_update("/admin"), WEB_APP_URL)

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["text"], ADMIN_TEXT)
        self.assertNotIn("reply_markup", response)

    def test_webhook_secret_comparison_rejects_invalid_values(self) -> None:
        expected = "a" * 64

        self.assertTrue(webhook_secret_matches(expected, expected))
        self.assertFalse(webhook_secret_matches(None, expected))
        self.assertFalse(webhook_secret_matches("wrong", expected))
        self.assertFalse(webhook_secret_matches("секрет", expected))

    def test_irrelevant_updates_are_ignored(self) -> None:
        ignored_updates = (
            {},
            message_update(""),
            message_update("hello"),
            message_update("/start", chat_type="group"),
            {
                "message": {
                    "from": {"id": 10, "is_bot": True},
                    "chat": {"id": 10, "type": "private"},
                    "text": "/start",
                }
            },
        )

        for update in ignored_updates:
            with self.subTest(update=update):
                self.assertIsNone(build_webhook_response(update, WEB_APP_URL))


if __name__ == "__main__":
    unittest.main()
