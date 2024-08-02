import os
import time
import logging
import yt_dlp as youtube_dl
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from moviepy.editor import VideoFileClip
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def ytdl_command(bot, msg):
    logger.info(f"Received /ytdl command from {msg.from_user.id}")
    await msg.reply_text("📥 **Send your YouTube links to download**")

@Client.on_message(filters.private & filters.text & filters.user(ADMIN) & ~filters.command("ytdl"))
async def handle_youtube_link(bot, msg):
    urls = msg.text.split()
    for url in urls:
        ydl_opts = {
            'format': 'bestvideo+bestaudio',
            'noplaylist': True
        }
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown Title')
                thumbnail_url = info.get('thumbnail', '')
                views = info.get('view_count', 'Unknown')
                likes = info.get('like_count', 'Unknown')
                formats = info.get('formats', [])

                buttons = []
                for fmt in formats:
                    if fmt.get('vcodec') != 'none':
                        resolution = fmt.get('format_note', 'Unknown Resolution')
                        size = humanbytes(fmt.get('filesize', 0))
                        buttons.append(InlineKeyboardButton(f"{resolution} - {size}", callback_data=f"{fmt['format_id']}|{url}"))

                # Arrange buttons in a grid
                grid_buttons = []
                for i in range(0, len(buttons), 2):
                    grid_buttons.append(buttons[i:i+2])

                inline_kb_markup = InlineKeyboardMarkup(grid_buttons)

                await bot.send_photo(
                    msg.chat.id,
                    thumbnail_url,
                    caption=f"📹 **{title}**\n👀 Views: {views} | 👍 Likes: {likes}\n\n📊 **Select your resolution:**",
                    reply_markup=inline_kb_markup
                )

                # Add resolution buttons to the menu
                kb_markup = ReplyKeyboardMarkup(
                    [[KeyboardButton(button.text)] for button in buttons],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
                await bot.send_message(
                    msg.chat.id,
                    "📲 **Select resolution from the menu below:**",
                    reply_markup=kb_markup
                )
        except Exception as e:
            logger.error(f"Error extracting info: {e}")
            await msg.reply_text(f"⚠️ **Error extracting information from URL:** {e}")

@Client.on_callback_query(filters.regex(r'^\d+\|.+$'))
async def download_video(bot, callback_query):
    data = callback_query.data
    format_id, url = data.split('|')

    ydl_opts = {
        'format': format_id,
        'outtmpl': os.path.join(DOWNLOAD_LOCATION, '%(title)s.%(ext)s'),
        'progress_hooks': [lambda d: progress_hook(d, bot, callback_query.message)]
    }

    msg = callback_query.message
    c_time = time.time()

    await msg.edit_text("🔄 **Download started...** 📥")

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            filepath = ydl.prepare_filename(info)
            title = info.get('title', 'Unknown Title')
            thumbnail_url = info.get('thumbnail', '')

        await msg.edit_text(f"✅ **Download finished. Now starting upload...** 📤\n\n📹 **{title}**")

        video_clip = VideoFileClip(filepath)
        duration = int(video_clip.duration) if video_clip.duration else 0
        video_clip.close()

        await bot.send_video(
            msg.chat.id,
            video=filepath,
            thumb=thumbnail_url,
            caption=f"📹 **{title}**",
            duration=duration,
            progress=progress_message,
            progress_args=("🚀 **Upload Started...** ❤️ Thanks To All Who Supported", msg, c_time)
        )

        os.remove(filepath)
        await msg.delete()

    except Exception as e:
        await msg.edit_text(f"⚠️ **Error:** {e}")

def progress_hook(d, bot, message):
    if d['status'] == 'downloading':
        current = d.get('downloaded_bytes', 0)
        total = d.get('total_bytes', 1)  # Avoid division by zero
        percent = current * 100 / total
        time.sleep(1)
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text=f"⬇️ **Downloading... {percent:.2f}%**"
        )
    elif d['status'] == 'finished':
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text="✅ **Download finished. Now starting upload...**"
        )
