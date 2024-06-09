import os
import time
import requests
import yt_dlp as youtube_dl
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from moviepy.editor import VideoFileClip
from PIL import Image
from config import DOWNLOAD_LOCATION, ADMIN

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

    # Send processing message
    processing_message = await msg.reply_text("🔄 **Processing your request...**")

    ydl_opts = {
        'format': 'best',
        'noplaylist': True,
        'quiet': True
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        title = info_dict.get('title', 'Unknown Title')
        views = info_dict.get('view_count', 'N/A')
        likes = info_dict.get('like_count', 'N/A')
        thumb_url = info_dict.get('thumbnail', None)
        formats = info_dict.get('formats', [])

    unique_resolutions = set()
    for f in formats:
        try:
            if f['ext'] == 'mp4' and f.get('filesize'):
                unique_resolutions.add(f['height'])
        except KeyError:
            continue

    buttons = []
    for resolution in sorted(unique_resolutions, reverse=True):
        streams_with_resolution = [f for f in formats if f.get('height') == resolution and f['ext'] == 'mp4']
        if streams_with_resolution:
            streams_with_resolution = sorted(streams_with_resolution, key=lambda x: x['filesize'], reverse=True)
            highest_size_stream = streams_with_resolution[0]
            size = humanbytes(highest_size_stream['filesize']) if highest_size_stream['filesize'] else "Unknown size"
            buttons.append([InlineKeyboardButton(f"📹 {resolution}p - {size}", callback_data=f"yt_{highest_size_stream['format_id']}_{url}")])

    markup = InlineKeyboardMarkup(buttons)

    caption = (
        f"**🎬 Title:** {title}\n"
        f"**👀 Views:** {views}\n"
        f"**👍 Likes:** {likes}\n\n"
        f"📥 **Select your resolution:**"
    )

    await processing_message.edit_text(caption, reply_markup=markup)

def download_progress_callback(d):
    if d['status'] == 'downloading':
        total_size = d.get('total_bytes', 0)
        downloaded = d.get('downloaded_bytes', 0)
        percentage = downloaded / total_size * 100 if total_size else 0
        speed = d.get('speed', 0)
        eta = d.get('eta', 0)

        progress_message = (
            f"⬇️ **Download Progress:** {humanbytes(downloaded)} of {humanbytes(total_size)} ({percentage:.2f}%)\n"
            f"⚡️ **Speed:** {humanbytes(speed)}/s\n"
            f"⏳ **Estimated Time Remaining:** {eta:.2f} seconds"
        )
        d['message'].edit_text(progress_message)

@Client.on_callback_query(filters.regex(r'^yt_\d+_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler(bot, query):
    data = query.data.split('_')
    format_id = data[1]
    url = '_'.join(data[2:])

    ydl_opts = {
        'format': format_id,
        'outtmpl': os.path.join(DOWNLOAD_LOCATION, '%(title)s.%(ext)s'),
        'progress_hooks': [download_progress_callback]
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_path = ydl.prepare_filename(info_dict)
    except Exception as e:
        await query.message.edit_text(f"❌ **Error during download:** {e}")
        return

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
        f"🕒 **Duration:** {duration} seconds"
    )

    await query.message.edit_text("🚀 **Uploading started...** 📤")

    try:
        await bot.send_video(query.message.chat.id, video=downloaded_path, thumb=thumb_path, caption=caption, duration=duration)
    except Exception as e:
        await query.message.edit_text(f"❌ **Error:** {e}")
        return

    os.remove(downloaded_path)
    if thumb_path:
        os.remove(thumb_path)

    await query.message.delete()
