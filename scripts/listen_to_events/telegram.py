import json
import os

import aiohttp
from scripts.listen_to_events.strategies import escape_markdown, parse_event_name
from workspaces.core.src.balpy.core.utils import get_explorer_link
from urllib.parse import quote

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def format_telegram_message(data: dict):
    message_text = f"Event: {parse_event_name(data['event']).name} \\([{data['chain'].name}\\#{data['event']['blockNumber']}]({escape_markdown(get_explorer_link(data['chain'], data['event']['transactionHash'].hex()))})\\)"
    if data["topics"].get("poolId"):
        message_text += f""" \\- [open in Balancer]({escape_markdown(
            f"https://app.balancer.fi/#/{CHAIN_NAMES[chain]}/pool/{topics['poolId']}"
        )})\r\n"""
    else:
        message_text += "\r\n"
    message_text += f"""{escape_markdown(json.dumps(
        {
            **data['topics'],
            **data['info'],
        },
        indent=2
        ))}"""
    return message_text


async def send_telegram_notification(data: dict):
    message_text = format_telegram_message(data)
    print(f"Sending telegram notification: {quote(message_text)}")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={quote(message_text)}&parse_mode=MarkdownV2&disable_web_page_preview=True"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"Error sending message: {resp.status} {await resp.text()}")
