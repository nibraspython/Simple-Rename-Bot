import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytube import YouTube
from moviepy.editor import VideoFileClip
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import humanbytes

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

async def download_video(url, filename, sts):
    yt = YouTube(url)
    stream = yt.streams.filter(file_extension='mp4').order_by('resolution').first()
    total_size = stream.filesize
    bytes_downloaded = 0

    # Open the video file for writing in binary mode
    with open(filename, 'wb') as video_file:
        # Stream the video file from the internet and write to local file
        response = requests.get(stream.url, stream=True)
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                video_file.write(chunk)
                bytes_downloaded += len(chunk)
                progress = f"Downloaded {humanbytes(bytes_downloaded)} of {humanbytes(total_size)} ({(bytes_downloaded / total_size) * 100:.2f}%)"
                try:
                    await sts.edit_text(progress)
                except:
                    pass

@Client.on_callback_query(filters.regex(r'^yt_\d+_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler(bot, query):
    data = query.data.split('_')
    itag = int(data[1])
    url = '_'.join(data[2:])  # Join the rest of the data as URL in case it contains underscores

    sts = await query.message.reply_text("🔄 Downloading video.....📥")

    filename = f"{DOWNLOAD_LOCATION}/video.mp4"

    # Download the video
    await download_video(url, filename, sts)
    
    duration = int(VideoFileClip(filename).duration)
    filesize = humanbytes(os.path.getsize(filename))

    cap = f"**Video File**\n\n💽 Size: {filesize}\n🕒 Duration: {duration} seconds"

    await sts.edit("🚀 Uploading started..... 📤")

    try:
        await bot.send_video(query.message.chat.id, video=filename, caption=cap, duration=duration)
    except Exception as e:
        return await sts.edit(f"Error: {e}")

    # Clean up downloaded files
    os.remove(filename)
    await sts.delete()
