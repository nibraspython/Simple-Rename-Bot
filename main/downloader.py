import os
import time
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytube import YouTube
from moviepy.editor import VideoFileClip
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_bar_style, humanbytes

@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def ytdl(bot, msg):
    await msg.reply_text("🎥 Please send your YouTube links to download.")

@Client.on_message(filters.private & filters.user(ADMIN) & filters.regex(r'https?://(www\.)?youtube\.com/watch\?v='))
async def youtube_link_handler(bot, msg):
    url = msg.text.strip()
    yt = YouTube(url)

    # Fetch video details
    title = yt.title
    views = yt.views
    likes = yt.rating  # Note: YouTube API might require a different way to fetch likes
    thumb_url = yt.thumbnail_url

    # Combine progressive and adaptive streams
    streams = yt.streams.filter(file_extension='mp4').order_by('resolution')
    buttons = []
    for stream in streams:
        if stream.resolution:  # Only include streams with a resolution
            res = stream.resolution
            size = humanbytes(stream.filesize) if stream.filesize else "Unknown size"
            buttons.append([InlineKeyboardButton(f"{res} - {size}", callback_data=f"yt_{stream.itag}_{url}")])

    markup = InlineKeyboardMarkup(buttons)

    caption = f"**Title:** {title}\n**Views:** {views}\n**Likes:** {likes}\n\nSelect your resolution:"

    await bot.send_photo(msg.chat.id, thumb_url, caption=caption, reply_markup=markup)

def download_video(url, filename):
    yt = YouTube(url)
    stream = yt.streams.filter(file_extension='mp4').order_by('resolution').first()
    total_size = stream.filesize
    bytes_downloaded = 0

    # Open the video file for writing in binary mode
    with open(filename, 'wb') as video_file, progress_bar_style(
            desc=f"Downloading {filename}",
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            ascii=True,
            miniters=1,
            ncols=100
    ) as progress_bar:
        # Stream the video file from the internet and write to local file
        for chunk in stream.stream().iter_content(chunk_size=1024):
            if chunk:
                video_file.write(chunk)
                bytes_downloaded += len(chunk)
                progress_bar.update(len(chunk))

@Client.on_callback_query(filters.regex(r'^yt_\d+_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler(bot, query):
    data = query.data.split('_')
    itag = int(data[1])
    url = '_'.join(data[2:])  # Join the rest of the data as URL in case it contains underscores

    sts = await query.message.reply_text("🔄 Downloading video.....📥")
    c_time = time.time()
    filename = f"{DOWNLOAD_LOCATION}/video.mp4"

    # Download the video
    download_video(url, filename)
    
    duration = int(VideoFileClip(filename).duration)
    filesize = humanbytes(os.path.getsize(filename))

    # Download the thumbnail
    yt = YouTube(url)
    thumb_url = yt.thumbnail_url
    thumb_path = f"{DOWNLOAD_LOCATION}/thumbnail.jpg"
    response = requests.get(thumb_url)
    if response.status_code == 200:
        with open(thumb_path, 'wb') as thumb_file:
            thumb_file.write(response.content)
    else:
        thumb_path = None

    cap = f"**{yt.title}**\n\n💽 Size: {filesize}\n🕒 Duration: {duration} seconds"

    await sts.edit("🚀 Uploading started..... 📤")
    c_time = time.time()

    try:
        await bot.send_video(query.message.chat.id, video=filename, thumb=thumb_path, caption=cap, duration=duration, progress=progress_message, progress_args=("Upload Started..... Thanks To All Who Supported ❤", sts, c_time))
    except Exception as e:
        return await sts.edit(f"Error: {e}")

    # Clean up downloaded files
    os.remove(filename)
    if thumb_path:
        os.remove(thumb_path)
    await sts.delete()
