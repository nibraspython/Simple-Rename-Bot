import os
import time
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes

urls_to_download = {}

@Client.on_message(filters.private & filters.command("get") & filters.user(ADMIN))
async def get_url(bot, msg):
    chat_id = msg.chat.id
    urls_to_download[chat_id] = None
    await msg.reply_text("🌐 **Send the URL to upload:**")

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def receive_url(bot, msg):
    chat_id = msg.chat.id
    if chat_id in urls_to_download and urls_to_download[chat_id] is None:
        url = msg.text.strip()
        urls_to_download[chat_id] = url

        buttons = [
            [InlineKeyboardButton("Confirm ✔️", callback_data="url_confirm")],
            [InlineKeyboardButton("Cancel 🚫", callback_data="url_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await msg.reply_text(f"🌐 **URL:** `{url}`\n\nDo you want to proceed?", reply_markup=reply_markup)

@Client.on_callback_query(filters.regex("url_confirm") & filters.user(ADMIN))
async def url_confirm_callback(bot, query):
    chat_id = query.message.chat.id
    url = urls_to_download.get(chat_id)

    if url:
        await query.message.edit_text("🔄 **Initializing download...**")
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(DOWNLOAD_LOCATION, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: download_hook(d, query.message, time.time())],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info_dict)

            file_size = humanbytes(os.path.getsize(file_path))
            await query.message.edit_text(f"🚀 **Uploading started...**\n\n**File:** `{os.path.basename(file_path)}`\n**Size:** `{file_size}`")

            c_time = time.time()
            if file_path.endswith(('.mp4', '.mkv')):
                await bot.send_video(
                    chat_id,
                    video=file_path,
                    caption=f"**{os.path.basename(file_path)}**\n**Size:** `{file_size}`",
                    progress=progress_message,
                    progress_args=("⬆️ **Uploading...**", query.message, c_time)
                )
            else:
                await bot.send_document(
                    chat_id,
                    document=file_path,
                    caption=f"**{os.path.basename(file_path)}**\n**Size:** `{file_size}`",
                    progress=progress_message,
                    progress_args=("⬆️ **Uploading...**", query.message, c_time)
                )

            os.remove(file_path)
            await query.message.delete()
        except Exception as e:
            await query.message.edit(f"❌ **Error:** {e}")

@Client.on_callback_query(filters.regex("url_cancel") & filters.user(ADMIN))
async def url_cancel_callback(bot, query):
    chat_id = query.message.chat.id
    if chat_id in urls_to_download:
        del urls_to_download[chat_id]
    await query.message.edit_text("❌ **Download canceled.**")

def download_hook(d, message, start_time):
    if d['status'] == 'downloading':
        total_size = d.get('total_bytes') or d.get('total_bytes_estimate')
        progress_message(d['downloaded_bytes'], total_size, "⬇️ **Downloading...**", message, start_time)
    elif d['status'] == 'finished':
        print('Done downloading, now converting ...')
