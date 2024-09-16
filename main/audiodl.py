import os
import time
import asyncio
import yt_dlp as youtube_dl
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION
from main.utils import progress_message, humanbytes

# Hook function to show download progress using asyncio
async def download_progress_hook(d, download_message, bot, query, last_update_time):
    if d['status'] == 'downloading':
        current = d.get('downloaded_bytes', 0) or 0
        total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0) or 0
        speed = d.get('speed', 0) or 0
        eta = d.get('eta', 0) or 0
        percent = (current / total) * 100 if total > 0 else 0

        # Only update every 5 seconds to avoid flooding logs
        if time.time() - last_update_time > 5:
            message = (
                f"⬇️ **Downloading audio...**\n\n"
                f"**Progress:** {percent:.2f}%\n"
                f"**Downloaded:** {humanbytes(current)} of {humanbytes(total)}\n"
                f"**Speed:** {humanbytes(speed)}/s\n"
                f"**ETA:** {eta}s"
            )

            try:
                await download_message.edit_text(message)
            except Exception as e:
                pass  # Ignore errors in editing messages (e.g., message deleted)

            return time.time()  # Return the current time as the last update time

    return last_update_time  # Return unchanged if it's not time to update

@Client.on_callback_query(filters.regex(r'^audio_https?://(www\.)?youtube\.com/watch\?v='))
async def audio_callback_handler(bot, query):
    url = '_'.join(query.data.split('_')[1:])

    # Get the title from the original message caption
    title = query.message.caption.split('🎬 ')[1].split('\n')[0]

    # Send initial download started message with title and "Audio"
    download_message = await query.message.edit_text(f"⬇️ **Download started...**\n\n**🎬 {title}**\n\n**🎧 Audio**")

    last_update_time = time.time()  # Track the last time the message was updated

    # YTDL options including progress hooks with asyncio
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]',  # Only audio format
        'outtmpl': os.path.join(DOWNLOAD_LOCATION, '%(title)s.%(ext)s'),
        'progress_hooks': [lambda d: asyncio.run_coroutine_threadsafe(download_progress_hook(d, download_message, bot, query, last_update_time), asyncio.get_event_loop())],  # Progress hook with asyncio
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
