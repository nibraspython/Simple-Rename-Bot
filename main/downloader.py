import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pytube import YouTube
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes

# Initialize Pyrogram client
app = Client("youtube_downloader_bot")

# /ytdl command handler
@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def youtube_download(bot, msg):
    chat_id = msg.chat.id
    await msg.reply_text("🔄 Please send your YouTube video link to download.")

# Handler for receiving the YouTube video link
@app.on_message(filters.private & filters.text & filters.user(ADMIN))
async def receive_youtube_link(bot, msg: Message):
    chat_id = msg.chat.id
    link = msg.text.strip()
    try:
        yt = YouTube(link)
        title = yt.title
        views = yt.views
        likes = yt.likes
        filesize = yt.streams.get_highest_resolution().filesize

        caption = f"🎥 YouTube Video\n\n📺 Title: {title}\n👀 Views: {views}\n👍 Likes: {likes}\n💽 Size: {humanbytes(filesize)}"

        await msg.reply_photo(
            photo=yt.thumbnail_url,
            caption=caption,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Download", callback_data=f"download_{link}")]
            ])
        )
    except Exception as e:
        await msg.reply_text(f"❌ Error: {e}")

# Callback query handler for download process
@app.on_callback_query(filters.regex(r"download_") & filters.user(ADMIN))
async def initiate_download(bot, query: CallbackQuery):
    chat_id = query.message.chat.id
    link = query.data.split("_", 1)[1]
    try:
        yt = YouTube(link)
        stream = yt.streams.get_highest_resolution()
        await query.message.reply_text("🔄 Downloading video...")
        sts = await query.message.reply_text("📥 Downloading...")
        c_time = time.time()
        try:
            downloaded = await bot.download_media(stream.url, progress=progress_message, progress_args=("📥 Downloading...", sts, c_time))
            filesize = humanbytes(os.path.getsize(downloaded))
            await sts.edit("🚀 Uploading video... 📤")
            c_time = time.time()
            await bot.send_video(
                chat_id,
                video=downloaded,
                thumb=yt.thumbnail_url,
                caption=f"🎥 YouTube Video\n\n📺 Title: {yt.title}\n👀 Views: {yt.views}\n👍 Likes: {yt.likes}\n💽 Size: {filesize}",
                progress=progress_message,
                progress_args=("🚀 Uploading video...", sts, c_time)
            )
        except Exception as e:
            await sts.edit(f"❌ Error during download/upload: {e}")
        finally:
            os.remove(downloaded)
            await sts.delete()
    except Exception as e:
        await query.message.reply_text(f"❌ Error: {e}")
