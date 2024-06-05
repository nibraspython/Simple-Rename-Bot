import os
import time
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytube import YouTube
from moviepy.editor import VideoFileClip
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import humanbytes, progress_bar

@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def ytdl(bot, msg):
    await msg.reply_text("🎥 Please send your YouTube links to download.")

async def download_progress_callback(stream, chunk, bytes_remaining, sts, start_time):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = (bytes_downloaded / total_size) * 100
    elapsed_time = time.time() - start_time
    speed = bytes_downloaded / elapsed_time
    estimated_total_time = total_size / speed
    time_remaining = estimated_total_time - elapsed_time

    progress_message = (
        f"**Download Progress:** {humanbytes(bytes_downloaded)} of {humanbytes(total_size)} ({percentage:.2f}%)\n"
        f"**Speed:** {humanbytes(speed)}/s\n"
        f"**Estimated Time Remaining:** {time_remaining:.2f} seconds\n"
        f"{progress_bar(percentage)}"  # Include progress bar
    )
    await sts.edit_text(progress_message)

@Client.on_callback_query(filters.regex(r'^yt_\d+_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler(bot, query):
    data = query.data.split('_')
    itag = int(data[1])
    url = '_'.join(data[2:])  # Join the rest of the data as URL in case it contains underscores

    yt = YouTube(url)
    stream = yt.streams.get_by_itag(itag)

    sts = await query.message.reply_text("🔄 Downloading video.....📥")
    c_time = time.time()
    
    # Define the progress callback function
    def progress_callback(stream, chunk, bytes_remaining):
        download_progress_callback(stream, chunk, bytes_remaining, sts, c_time)
    
    # Download the video with the progress callback
    downloaded = stream.download(output_path=DOWNLOAD_LOCATION, on_progress_callback=progress_callback)
    
    duration = int(VideoFileClip(downloaded).duration)
    filesize = os.path.getsize(downloaded)

    # Download the thumbnail
    thumb_url = yt.thumbnail_url
    thumb_path = os.path.join(DOWNLOAD_LOCATION, 'thumb.jpg')
    response = requests.get(thumb_url)
    if response.status_code == 200:
        with open(thumb_path, 'wb') as thumb_file:
            thumb_file.write(response.content)
    else:
        thumb_path = None

    cap = f"**{yt.title}**\n\n💽 Size: {humanbytes(filesize)}\n🕒 Duration: {duration} seconds"

    await sts.edit("🚀 Uploading started..... 📤")
    c_time = time.time()

    try:
        # Upload the video with the progress callback
        await bot.send_video(
            query.message.chat.id,
            video=downloaded,
            thumb=thumb_path,
            caption=cap,
            duration=duration,
            progress=upload_progress_callback,
            progress_args=(filesize, sts, c_time)  # Pass additional arguments
        )
    except Exception as e:
        return await sts.edit(f"Error: {e}")

    # Clean up downloaded files
    os.remove(downloaded)
    if thumb_path:
        os.remove(thumb_path)
    await sts.delete()
