import os
import time
import requests
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytube import YouTube
from moviepy.editor import VideoFileClip
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes

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

    # Generate resolution options
    streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution')
    buttons = []
    for stream in streams:
        res = stream.resolution
        size = humanbytes(stream.filesize)
        buttons.append([InlineKeyboardButton(f"{res} - {size}", callback_data=f"yt_{stream.itag}_{url}")])

    markup = InlineKeyboardMarkup(buttons)

    caption = f"**Title:** {title}\n**Views:** {views}\n**Likes:** {likes}\n\nSelect your resolution:"

    await bot.send_photo(msg.chat.id, thumb_url, caption=caption, reply_markup=markup)

@Client.on_callback_query(filters.regex(r'^yt_\d+_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler(bot, query):
    data = query.data.split('_')
    itag = int(data[1])
    url = '_'.join(data[2:])  # Join the rest of the data as URL in case it contains underscores

    yt = YouTube(url)
    stream = yt.streams.get_by_itag(itag)

    sts = await query.message.reply_text("🔄 Downloading video.....📥")
    c_time = time.time()
    downloaded = stream.download(output_path=DOWNLOAD_LOCATION)
    duration = int(VideoFileClip(downloaded).duration)
    filesize = humanbytes(os.path.getsize(downloaded))

    # Download the thumbnail
    thumb_url = yt.thumbnail_url
    thumb_path = os.path.join(DOWNLOAD_LOCATION, 'thumb.jpg')
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
        await bot.send_video(query.message.chat.id, video=downloaded, thumb=thumb_path, caption=cap, duration=duration, progress=progress_message, progress_args=("Upload Started..... Thanks To All Who Supported ❤", sts, c_time))
    except Exception as e:
        return await sts.edit(f"Error: {e}")

    # Clean up downloaded files
    os.remove(downloaded)
    if thumb_path:
        os.remove(thumb_path)
    await sts.delete()
