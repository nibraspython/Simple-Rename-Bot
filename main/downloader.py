import os
import time
import requests
import subprocess
from pytube import YouTube
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from moviepy.editor import VideoFileClip
from PIL import Image
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes

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

    yt = YouTube(url)

    title = yt.title
    views = yt.views
    likes = yt.rating
    thumb_url = yt.thumbnail_url

    streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
    unique_resolutions = sorted({stream.resolution for stream in streams}, reverse=True)

    buttons = []
    for resolution in unique_resolutions:
        stream = streams.filter(res=resolution).first()
        video_size = stream.filesize
        size_text = humanbytes(video_size)
        button_text = f"🎬 {resolution} - {size_text}"
        callback_data = f"yt_{resolution}_{url}"
        buttons.append(InlineKeyboardButton(button_text, callback_data=callback_data))

    buttons = [buttons[i:i+2] for i in range(0, len(buttons), 2)]  # Split buttons into rows of 2

    markup = InlineKeyboardMarkup(buttons)

    caption = (
        f"**🎬 Title:** {title}\n"
        f"**👀 Views:** {views}\n"
        f"**👍 Likes:** {likes}\n\n"
        f"📥 **Select your resolution:**"
    )

    thumb_response = requests.get(thumb_url)
    thumb_path = os.path.join(DOWNLOAD_LOCATION, 'thumb.jpg')
    with open(thumb_path, 'wb') as thumb_file:
        thumb_file.write(thumb_response.content)
    await bot.send_photo(chat_id=msg.chat.id, photo=thumb_path, caption=caption, reply_markup=markup)
    os.remove(thumb_path)

    await processing_message.delete()

def download_progress_callback(stream, chunk, bytes_remaining, message, c_time, update_interval=5):
    total_size = stream.filesize
    downloaded = total_size - bytes_remaining
    percentage = downloaded / total_size * 100
    speed = downloaded / (time.time() - c_time)
    eta = bytes_remaining / speed

    current_time = time.time()
    if current_time - c_time >= update_interval:
        progress_message_text = (
            f"⬇️ **Download Progress:** {humanbytes(downloaded)} of {humanbytes(total_size)} ({percentage:.2f}%)\n"
            f"⚡️ **Speed:** {humanbytes(speed)}/s\n"
            f"⏳ **Estimated Time Remaining:** {eta:.2f} seconds"
        )
        try:
            message.edit_text(progress_message_text)
        except Exception as e:
            print(f"Error updating progress message: {e}")
        return current_time  # Return the updated c_time
    return c_time  # Return the unchanged c_time if update_interval has not passed

@Client.on_callback_query(filters.regex(r'^yt_\d+p?_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler(bot, query):
    data = query.data.split('_')
    resolution = data[1]
    url = '_'.join(data[2:])

    c_time = time.time()
    await query.message.edit_text("⬇️ **Download started...**")

    yt = YouTube(url, on_progress_callback=lambda stream, chunk, bytes_remaining: download_progress_callback(stream, chunk, bytes_remaining, query.message, c_time))

    stream = yt.streams.filter(progressive=True, res=resolution, file_extension='mp4').first()
    if not stream:
        await query.message.edit_text("❌ **No suitable stream found.**")
        return

    downloaded_path = os.path.join(DOWNLOAD_LOCATION, stream.default_filename)
    stream.download(output_path=DOWNLOAD_LOCATION)

    video = VideoFileClip(downloaded_path)
    duration = int(video.duration)
    video_width, video_height = video.size
    filesize = humanbytes(os.path.getsize(downloaded_path))

    thumb_url = yt.thumbnail_url
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

    button_text = query.data.split('_')[1]

    caption = (
        f"**🎬 {yt.title}**\n\n"
        f"💽 **Size:** {filesize}\n"
        f"🕒 **Duration:** {duration} seconds\n"
        f"📹 **Resolution:** {button_text}\n\n"
        f"✅ **Download completed!**"
    )

    await query.message.edit_text("🚀 **Uploading started...** 📤")

    c_time = time.time()
    try:
        await bot.send_video(
            chat_id=query.message.chat.id,
            video=downloaded_path,
            thumb=thumb_path,
            caption=caption,
            duration=duration,
            progress=progress_message,
            progress_args=("Upload Started..... Thanks To All Who Supported ❤", query.message, c_time)
        )
    except Exception as e:
        await query.message.edit_text(f"❌ **Error during upload:** {e}")
        return

    os.remove(downloaded_path)
    if thumb_path:
        os.remove(thumb_path)

    await query.message.delete()
