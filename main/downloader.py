import os
import requests
import yt_dlp as youtube_dl
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from moviepy.editor import VideoFileClip
from PIL import Image
from config import DOWNLOAD_LOCATION, ADMIN
import logging

logging.basicConfig(level=logging.INFO)

def humanbytes(size):
    if not size:
        return "0 B"
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {power_labels[n]}B"

@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def ytdl(bot, msg):
    await msg.reply_text("🎥 Please send your YouTube links to download.")

@Client.on_message(filters.private & filters.user(ADMIN) & filters.regex(r'https?://(www\.)?youtube\.com/watch\?v='))
async def youtube_link_handler(bot, msg):
    url = msg.text.strip()
    logging.info(f"Received URL: {url}")

    # Send processing message
    processing_message = await msg.reply_text("🔄 **Processing your request...**")

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'quiet': True
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = info_dict.get('title', 'Unknown Title')
            views = info_dict.get('view_count', 'N/A')
            likes = info_dict.get('like_count', 'N/A')
            thumb_url = info_dict.get('thumbnail', None)
            formats = info_dict.get('formats', [])
            logging.info("Fetched video info successfully.")
    except Exception as e:
        logging.error(f"Error fetching video info: {e}")
        await processing_message.edit_text(f"❌ **Error fetching video info:** {e}")
        return

    unique_resolutions = set()
    for f in formats:
        try:
            if f['vcodec'] != 'none' and f.get('filesize'):
                unique_resolutions.add(f['height'])
        except KeyError:
            continue

    buttons = []
    for resolution in sorted(unique_resolutions, reverse=True):
        video_streams = [f for f in formats if f.get('height') == resolution and f['vcodec'] != 'none']
        audio_streams = [f for f in formats if 'acodec' in f and f['acodec'] != 'none']

        if video_streams and audio_streams:
            best_video_stream = max(video_streams, key=lambda x: x.get('filesize') or 0)
            best_audio_stream = max(audio_streams, key=lambda x: x.get('filesize') or 0)
            video_size = best_video_stream.get('filesize') or 0
            audio_size = best_audio_stream.get('filesize') or 0
            if video_size and audio_size:
                total_size = video_size + audio_size
                size = humanbytes(total_size)
                buttons.append([InlineKeyboardButton(f"📹 {resolution}p - {size}", callback_data=f"yt_{best_video_stream['format_id']}_{best_audio_stream['format_id']}_{url}")])

    if not buttons:
        await processing_message.edit_text("❌ **No suitable video or audio streams found.**")
        return

    markup = InlineKeyboardMarkup(buttons)

    caption = (
        f"**🎬 Title:** {title}\n"
        f"**👀 Views:** {views}\n"
        f"**👍 Likes:** {likes}\n\n"
        f"📥 **Select your resolution:**"
    )

    # Send thumbnail with caption
    try:
        thumb_response = requests.get(thumb_url)
        thumb_path = os.path.join(DOWNLOAD_LOCATION, 'thumb.jpg')
        with open(thumb_path, 'wb') as thumb_file:
            thumb_file.write(thumb_response.content)
        await bot.send_photo(chat_id=msg.chat.id, photo=thumb_path, caption=caption, reply_markup=markup)
    except Exception as e:
        logging.error(f"Error fetching thumbnail: {e}")
        await processing_message.edit_text(f"❌ **Error fetching thumbnail:** {e}")
        return

    await processing_message.delete()

def download_progress_callback(d, message):
    if d['status'] == 'downloading':
        total_size = d.get('total_bytes', 0) or 0
        downloaded = d.get('downloaded_bytes', 0) or 0
        percentage = downloaded / total_size * 100 if total_size else 0
        speed = d.get('speed', 0) or 0
        eta = d.get('eta', 0) or 0

        progress_message = (
            f"⬇️ **Download Progress:** {humanbytes(downloaded)} of {humanbytes(total_size)} ({percentage:.2f}%)\n"
            f"⚡️ **Speed:** {humanbytes(speed)}/s\n"
            f"⏳ **Estimated Time Remaining:** {eta} seconds"
        )
        message.edit_text(progress_message)

@Client.on_callback_query(filters.regex(r'^yt_\d+_\d+_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler(bot, query):
    data = query.data.split('_')
    video_format_id = data[1]
    audio_format_id = data[2]
    url = '_'.join(data[3:])

    # Create a wrapper for the progress hook to pass additional context
    def progress_hook(d):
        download_progress_callback(d, query.message)

    ydl_opts = {
        'format': f'{video_format_id}+{audio_format_id}',
        'outtmpl': os.path.join(DOWNLOAD_LOCATION, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook]
    }

    await query.message.edit_text("⬇️ **Download started...**")

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_path = ydl.prepare_filename(info_dict)
            logging.info(f"Downloaded path: {downloaded_path}")
    except Exception as e:
        logging.error(f"Error during download: {e}")
        await query.message.edit_text(f"❌ **Error during download:** {e}")
        return

    try:
        video = VideoFileClip(downloaded_path)
        duration = int(video.duration)
        video_width, video_height = video.size
        filesize = humanbytes(os.path.getsize(downloaded_path))

        thumb_url = info_dict.get('thumbnail', None)
        thumb_path = os.path.join(DOWNLOAD_LOCATION, 'thumb.jpg')
        response = requests.get(thumb_url)
        if response.status_code == 200:
            with open(thumb_path, 'wb') as thumb_file:
                thumb_file.write(response.content)

            with Image.open(thumb_path) as img:
                img_width, img_height = img.size
                scale_factor = max(video_width / img_width, video_height / img_height)
                new_size = (int(img_width * scale_factor), int(img_height * scale_factor))
                img = img.resize(new_size, Image.ANTIALIAS)
                left = (img.width - video_width) / 2
                top = (img.height - video_height) / 2
                right = (img.width + video_width) / 2
                bottom = (img.height + video_height) / 2
                img = img.crop((left, top, right, bottom))
                img.save(thumb_path)
        else:
            thumb_path = None

        caption = (
            f"**🎬 {info_dict['title']}**\n\n"
            f"💽 **Size:** {filesize}\n"
            f"🕒 **Duration:** {duration} seconds\n"
            f"✅ **Download completed!**"
        )

        await query.message.edit_text("🚀 **Uploading started...** 📤")

        try:
            await bot.send_video(query.message.chat.id, video=downloaded_path, thumb=thumb_path, caption=caption, duration=duration)
        except Exception as e:
            logging.error(f"Error during upload: {e}")
            await query.message.edit_text(f"❌ **Error:** {e}")
            return

        os.remove(downloaded_path)
        if thumb_path:
            os.remove(thumb_path)

        await query.message.delete()
    except Exception as e:
        logging.error(f"Error handling video: {e}")
        await query.message.edit_text(f"❌ **Error handling video:** {e}")
