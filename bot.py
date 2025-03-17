from pyrogram import Client
from config import *
import os
import asyncio
from fastapi import FastAPI
import uvicorn

# Create download location if not exists
if not os.path.isdir(DOWNLOAD_LOCATION):
    os.makedirs(DOWNLOAD_LOCATION)

# FastAPI for Render Web Service
app = FastAPI()

@app.get("/")
async def home():
    return {"status": "Bot is Running!"}

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="simple-renamer",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=100,
            plugins={"root": "main"},
            sleep_threshold=10,
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        print(f"{me.first_name} | @{me.username} 𝚂𝚃𝙰𝚁𝚃𝙴𝙳...⚡️")

    async def stop(self, *args):
        await super().stop()
        print("Bot Restarting........")

bot = Bot()

# Run the bot and web service together
async def main():
    await bot.start()
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
