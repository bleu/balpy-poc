import discord
from discord.ext.commands import Bot
from urllib.parse import quote


import os


intents = discord.Intents.all()
intents.typing = False
intents.presences = False

bot_client = Bot(None, intents=intents)

async def send_discord_notification(message_text: str):
    print(f"Sending discord notification: {quote(message_text)}")
    channel = await bot_client.fetch_channel(
            int(os.getenv(f"DISCORD_CHANNEL_ID"))
        )
    return await channel.send(content=message_text)
    
