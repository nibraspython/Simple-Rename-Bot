from pyrogram import Client, filters
from config import ADMIN

# Command from trim.py
@Client.on_message(filters.private & filters.command("trim") & filters.user(ADMIN))
async def start_trim_process(bot, msg):
    # This is where the logic for the /trim command will go.
    await msg.reply_text("🔄 **Trimming process initiated.**")

# Command from downloader.py
@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def ytdl(bot, msg):
    # This is where the logic for the /ytdl command will go.
    await msg.reply_text("🎥 **YouTube download initiated.**")
