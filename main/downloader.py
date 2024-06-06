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

def download_progress_callback(stream, chunk, bytes_remaining, message, start_time):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = (bytes_downloaded / total_size) * 100
    elapsed_time = time.time() - start_time
    speed = bytes_downloaded / elapsed_time
    estimated_total_time = total_size / speed
    time_remaining = estimated_total_time - elapsed_time

    progress_message = (
        f"Download Progress: {bytes_downloaded} of {total_size} ({percentage:.2f}%)\n"
        f"Speed: {humanbytes(speed)}/s\n"
        f"Estimated Time Remaining: {time_remaining:.2f} seconds"
    )
    message.edit_text(progress_message)

@Client.on_callback_query(filters.regex(r'^yt_\d+_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler(bot, query):
    data = query.data.split('_')
    itag = int(data[1])
    url = '_'.join(data[2:])  # Join the rest of the data as URL in case it contains underscores

    yt = YouTube(url)
    stream = yt.streams.get_by_itag(itag)

    sts = await query.message.reply_text("🔄 Downloading video.....📥")
    c_time = time.time()

    # Register the progress callback
    yt.register_on_progress_callback(lambda stream, chunk, bytes_remaining: download_progress_callback(stream, chunk, bytes_remaining, sts, c_time))
    
    # Download the video
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

# Helper function to format file sizes
def humanbytes(size):
    # Returns the human-readable file size
    if not size:
        return "0 B"
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {power_labels[n]}B"
