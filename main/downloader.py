import os
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pytube import YouTube
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes

# Initialize Pyrogram client
app = Client("youtube_downloader_bot")

# Dictionary to store resolution options for each YouTube video
resolution_options = {}

# /ytdl command handler
@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def youtube_download(bot, msg):
    chat_id = msg.chat.id
    await msg.reply_text("🔄 Please send your YouTube video link to download.")

# Handler for receiving YouTube video link
@app.on_message(filters.private & filters.text & filters.user(ADMIN))
async def receive_youtube_link(bot, msg: Message):
    chat_id = msg.chat.id
    link = msg.text.strip()
    try:
        yt = YouTube(link)
        title = yt.title
        views = yt.views
        likes = yt.likes

        resolutions = yt.streams.filter(progressive=True)
        options = []
        for res in resolutions:
            option = f"{res.resolution} ({humanbytes(res.filesize)})"
            options.append(option)
            resolution_options[chat_id] = resolutions

        caption = f"🎥 YouTube Video\n\n📺 Title: {title}\n👀 Views: {views}\n👍 Likes: {likes}\n\nSelect your resolution:"

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(option, callback_data=f"resolution_{index}")]
            for index, option in enumerate(options)
        ])

        await msg.reply_photo(
            photo=yt.thumbnail_url,
            caption=caption,
            reply_markup=reply_markup
        )
    except Exception as e:
        await msg.reply_text(f"❌ Error: {e}")

# Callback query handler for resolution selection
@app.on_callback_query(filters.regex(r"resolution_\d+") & filters.user(ADMIN))
async def select_resolution(bot, query: CallbackQuery):
    chat_id = query.message.chat.id
    resolution_index = int(query.data.split("_")[1])
    resolutions = resolution_options.get(chat_id)
    if resolutions:
        resolution = resolutions[resolution_index]

        await query.message.reply_text("🔄 Downloading video...")
        sts = await query.message.reply_text("📥 Downloading...")
        c_time = time.time()
        try:
            downloaded = await asyncio.get_running_loop().run_in_executor(None, resolution.download, output_path=DOWNLOAD_LOCATION, filename=f"{resolution.default_filename}.mp4", timeout=30)
            filesize = humanbytes(os.path.getsize(downloaded))
            await sts.edit("🚀 Uploading video... 📤")
            c_time = time.time()
            await bot.send_video(
                chat_id,
                video=downloaded,
                thumb=yt.thumbnail_url,
                caption=f"🎥 YouTube Video\n\n📺 Title: {yt.title}\n👀 Views: {yt.views}\n👍 Likes: {yt.likes}\n\n💽 Size: {filesize}",
                progress=progress_message,
                progress_args=("🚀 Uploading video...", sts, c_time)
            )
        except Exception as e:
            await sts.edit(f"❌ Error during download/upload: {e}")
        finally:
            os.remove(downloaded)
            await sts.delete()
