import os

import aiohttp

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def truncate(s: str, show_last: int = 0, max_length: int = 100) -> str:
    if len(s) > max_length:
        return s[: max_length - show_last] + "..." + s[-show_last:]
    return s


def escape_markdown(text: str) -> str:
    """Escape Telegram markdown special characters."""
    characters = [
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]
    for char in characters:
        text = text.replace(char, "\\" + char)
    return text


async def send_telegram_notification(message_text: str):
    escaped_text = escape_markdown(message_text)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={escaped_text}&parse_mode=MarkdownV2&disable_web_page_preview=True"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"Error sending message: {resp.status} {await resp.text()}")
