import os
import time
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes

@Client.on_message(filters.private & filters.command("urldl") & filters.user(ADMIN))
async def urldl_command(bot, msg):
    await msg.reply_text("📥 **Send me the direct download URL.**")

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def handle_url(bot, msg):
    url = msg.text.strip()
    if not url.startswith("http"):
        return await msg.reply_text("⚠️ **Invalid URL. Please send a valid direct download link.**")
    
    # Ask for confirmation
    buttons = [
        [InlineKeyboardButton("Confirm ✔️", callback_data=f"urldl_confirm|{url}")],
        [InlineKeyboardButton("Cancel 🚫", callback_data="urldl_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await msg.reply_text(f"**URL:** {url}\n\n**Do you want to download this file?**", reply_markup=reply_markup)

@Client.on_callback_query(filters.regex(r"urldl_confirm\|") & filters.user(ADMIN))
async def urldl_confirm(bot, query):
    url = query.data.split("|")[1]
    await query.message.edit_text("🔄 **Starting download...**")

    file_name = url.split("/")[-1]
    file_path = os.path.join(DOWNLOAD_LOCATION, file_name)

    try:
        start_time = time.time()
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0

        with open(file_path, 'wb') as file:
            for data in response.iter_content(chunk_size=1024):
                file.write(data)
                downloaded_size += len(data)
                await progress_message(downloaded_size, total_size, "📥 Downloading...", query.message, start_time)

        file_size = humanbytes(os.path.getsize(file_path))
        await query.message.edit_text(f"✅ **Downloaded successfully!**\n\n**File:** {file_name}\n**Size:** {file_size}")

        # Determine if the file is a video
        if file_name.lower().endswith((".mp4", ".mkv")):
            await bot.send_video(
                query.message.chat.id,
                video=file_path,
                caption=f"**{file_name}**\n**Size:** {file_size}",
                progress=progress_message,
                progress_args=("📤 Uploading...", query.message, start_time)
            )
        else:
            await bot.send_document(
                query.message.chat.id,
                document=file_path,
                caption=f"**{file_name}**\n**Size:** {file_size}",
                progress=progress_message,
                progress_args=("📤 Uploading...", query.message, start_time)
            )

        os.remove(file_path)
    except Exception as e:
        await query.message.edit_text(f"❌ **Error downloading file:** {e}")

@Client.on_callback_query(filters.regex("urldl_cancel") & filters.user(ADMIN))
async def urldl_cancel(bot, query):
    await query.message.edit_text("❌ **Download cancelled.**")
