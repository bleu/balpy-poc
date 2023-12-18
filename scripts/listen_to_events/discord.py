import logging
import os
from typing import List

import discord
from discord.ext.commands import Bot

from scripts.listen_to_events.strategies import (
    camel_case_to_capitalize,
    escape_markdown,
    parse_event_name,
)
from workspaces.core.src.balpy.core.utils import get_explorer_link

intents = discord.Intents.all()
intents.typing = False
intents.presences = False

bot_client = Bot(
    "}", intents=intents
)  # Bot don't use commands, this character was choose to avoid try to read commands


@bot_client.event
async def on_ready():
    logging.info(f"We have logged in as {bot_client.user}")


async def start_discord_bot():
    await bot_client.start(os.getenv(f"DISCORD_BOT_TOKEN"))


def create_embed(data: dict):
    description = (
        f"""[Open in Balancer]({escape_markdown(
        f"https://app.balancer.fi/#/{data['chain'].value}/pool/{data['topics']['poolId']}"
    )})\r\n"""
        if data["topics"].get("poolId")
        else None
    )
    embed = discord.Embed(
        title=" - ".join(
            [
                parse_event_name(data["event"]).name,
                f"{data['chain'].name.capitalize()} scanner tx",
            ]
        ),
        url=get_explorer_link(data["chain"], data["event"]["transactionHash"].hex()),
        description=description,
    )
    for key, value in {**data["topics"], **data["info"]}.items():
        if type(value) == list:
            value = "\n".join(value)
        embed.add_field(name=camel_case_to_capitalize(key), value=value, inline=False)

    return embed


async def send_discord_embed(channels: List[str], data: dict):
    print(f"Sending discord notification: {data}")
    embed = create_embed(data)
    print(f"Sending to channels: {channels}")
    for channel_id in channels:
        if not channel_id:
            continue
        channel = await bot_client.fetch_channel(int(channel_id))
        await channel.send(embed=embed)
