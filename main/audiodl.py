import os
import time
import asyncio
import yt_dlp as youtube_dl
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_LOCATION
from main.utils import progress_message, humanbytes

# Store progress info to update upon button click
progress_data = {}

# Helper function to format progress updates
def format_progress_message(d):
    current = d.get('downloaded_bytes', 0)
    total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
    percent = (current / total) * 100 if total else 0
    speed = d.get('speed', 0)
    eta = d.get('eta', 0)

    return (
        f"**Total:** {humanbytes(total)}\n"
        f"**Downloaded:** {humanbytes(current)}\n"
        f"**Completed:** {percent:.2f}%\n"
        f"**Speed:** {humanbytes(speed)}/s\n"
        f"**ETA:** {eta}s"
    )

# yt-dlp progress hook with asyncio integration
async def download_progress_hook(d, download_message):
    if d['status'] == 'downloading':
        # Update the global progress_data dictionary
        progress_data['status'] = format_progress_message(d)

@Client.on_callback_query(filters.regex(r'^audio_https?://(www\.)?youtube\.com/watch\?v='))
async def audio_callback_handler(bot, query):
    global progress_data
    url = '_'.join(query.data.split('_')[1:])

    # Get the title from the original message caption
    title = query.message.caption.split('🎬 ')[1].split('\n')[0]

    # Reset progress data for new download
    progress_data = {}

    # Create inline keyboard button for progress
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Progress", callback_data="progress")]
    ])

    # Send initial download started message with inline button
    download_message = await query.message.edit_text(
        f"⬇️ **Download started...**\n\n**🎬 {title}**\n\n**🎧 Audio**",
        reply_markup=keyboard
    )

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]',  # Only audio format
        'outtmpl': os.path.join(DOWNLOAD_LOCATION, '%(title)s.%(ext)s'),
        'progress_hooks': [lambda d: asyncio.run_coroutine_threadsafe(
            download_progress_hook(d, download_message),
            asyncio.get_event_loop()
        )],
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
            'preferredquality': '192'
        }]
    }

    try:
        # Start download with progress tracking
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_path = ydl.prepare_filename(info_dict)
        await download_message.edit_text("✅ **Download completed!**")
    except Exception as e:
        await download_message.edit_text(f"❌ **Error during download:** {e}")
        return

    final_filesize = os.path.getsize(downloaded_path)
    filesize = humanbytes(final_filesize)
    duration = int(info_dict['duration'])

    caption = (
        f"**🎧 {info_dict['title']}**\n\n"
        f"💽 **Size:** {filesize}\n"
        f"🔉 **Format:** Audio\n"
        f"🕒 **Duration:** {duration} seconds\n"
        f"✅ **Download completed!**"
    )

    uploading_message = await query.message.edit_text("🚀 **Uploading started...** 📤")

    c_time = time.time()
    try:
        # Send audio with upload progress
        await bot.send_audio(
            chat_id=query.message.chat.id,
            audio=downloaded_path,
            caption=caption,
            duration=duration,
            progress=progress_message,
            progress_args=(f"Uploading audio... 🎧 {info_dict['title']}", query.message, c_time)
        )
    except Exception as e:
        await query.message.edit_text(f"❌ **Error during upload:** {e}")
        return

    await uploading_message.delete()

    # Clean up the downloaded audio file after sending
    if os.path.exists(downloaded_path):
        os.remove(downloaded_path)

@Client.on_callback_query(filters.regex('progress'))
async def show_progress_popup(bot, query):
    global progress_data
    # Check if there's progress data available
    if 'status' in progress_data:
        # Display progress in pop-up
        await query.answer(progress_data['status'], show_alert=True)
    else:
        # Placeholder message if progress isn't available yet
        await query.answer("Progress not available yet. Please wait...", show_alert=True)
