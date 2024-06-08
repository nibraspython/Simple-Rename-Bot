import os
import time
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pytube import YouTube
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

    yt = YouTube(url)

    # Fetch video details
    title = yt.title
    views = yt.views
    likes = yt.rating  # Note: YouTube API might require a different way to fetch likes
    thumb_url = yt.thumbnail_url

    # Get unique resolutions
    unique_resolutions = set(stream.resolution for stream in yt.streams.filter(file_extension='mp4'))

    buttons = []
    for resolution in sorted(unique_resolutions, key=lambda x: int(x[:-1]), reverse=True):
        streams_with_resolution = [stream for stream in yt.streams.filter(file_extension='mp4', resolution=resolution)]
        if streams_with_resolution:
            # Sort streams by file size within the same resolution
            streams_with_resolution.sort(key=lambda x: x.filesize, reverse=True)
            highest_size_stream = streams_with_resolution[0]
            size = humanbytes(highest_size_stream.filesize) if highest_size_stream.filesize else "Unknown size"
            buttons.append([InlineKeyboardButton(f"📹 {resolution} - {size}", callback_data=f"yt_{highest_size_stream.itag}_{url}")])

    markup = InlineKeyboardMarkup(buttons)

    caption = (
        f"**🎬 Title:** {title}\n"
        f"**👀 Views:** {views}\n"
        f"**👍 Likes:** {likes}\n\n"
        f"📥 **Select your resolution:**"
    )

    # Edit the processing message to show the available resolutions
    await processing_message.edit_text(caption, reply_markup=markup)

def download_progress_callback(stream, chunk, bytes_remaining, message, start_time):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = (bytes_downloaded / total_size) * 100
    elapsed_time = time.time() - start_time
    speed = bytes_downloaded / elapsed_time
    estimated_total_time = total_size / speed
    time_remaining = estimated_total_time - elapsed_time

    progress_message = (
        f"⬇️ **Download Progress:** {bytes_downloaded} of {total_size} ({percentage:.2f}%)\n"
        f"⚡️ **Speed:** {humanbytes(speed)}/s\n"
        f"⏳ **Estimated Time Remaining:** {time_remaining:.2f} seconds"
    )
    message.edit_text(progress_message)

@Client.on_callback_query(filters.regex(r'^yt_\d+_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler(bot, query):
    data = query.data.split('_')
    itag = int(data[1])
    url = '_'.join(data[2:])  # Join the rest of the data as URL in case it contains underscores

    yt = YouTube(url)
    stream = yt.streams.get_by_itag(itag)

    if not stream:
        await query.message.edit_text("❌ **Error:** Selected resolution not available. Please try again.")
        return

    # Log stream details for debugging
    print(f"Selected stream: {stream}")
    print(f"Resolution: {stream.resolution}")
    print(f"FPS: {stream.fps}")
    print(f"Filesize: {stream.filesize}")
    print(f"Mime Type: {stream.mime_type}")

    # Edit the original message to remove resolution buttons
    await query.message.edit_text("🔄 **Downloading video...** 📥")

    sts = await query.message.reply_text("🔄 **Downloading video...** 📥")
    c_time = time.time()

    # Register the progress callback
    yt.register_on_progress_callback(lambda stream, chunk, bytes_remaining: download_progress_callback(stream, chunk, bytes_remaining, sts, c_time))
    
    try:
        # Download the video
        downloaded = stream.download(output_path=DOWNLOAD_LOCATION)
    except Exception as e:
        return await sts.edit(f"❌ **Error during download:** {e}")
    
    video = VideoFileClip(downloaded)
    duration = int(video.duration)
    video_width, video_height = video.size
    filesize = humanbytes(os.path.getsize(downloaded))

    # Log downloaded file size for comparison
    print(f"Downloaded file size: {filesize}")

    # Download the thumbnail
    thumb_url = yt.thumbnail_url
    thumb_path = os.path.join(DOWNLOAD_LOCATION, 'thumb.jpg')
    response = requests.get(thumb_url)
    if response.status_code == 200:
        with open(thumb_path, 'wb') as thumb_file:
            thumb_file.write(response.content)
        
        # Resize and crop the thumbnail to match the video's aspect ratio and dimensions
        with Image.open(thumb_path) as img:
            img_width, img_height = img.size
            # Calculate the scale factor to cover the video dimensions
            scale_factor = max(video_width / img_width, video_height / img_height)
            new_size = (int(img_width * scale_factor), int(img_height * scale_factor))
            img = img.resize(new_size, Image.ANTIALIAS)
            # Crop the image to the video dimensions
            left = (img.width - video_width) / 2
            top = (img.height - video_height) / 2
            right = (img.width + video_width) / 2
            bottom = (img.height + video_height) / 2
            img = img.crop((left, top, right, bottom))
            img.save(thumb_path)
    else:
        thumb_path = None

    cap = (
        f"**🎬 {yt.title}**\n\n"
        f"💽 **Size:** {filesize}\n"
        f"🕒 **Duration:** {duration} seconds"
    )

    await sts.edit("🚀 **Uploading started...** 📤")
    c_time = time.time()

    try:
        await bot.send_video(query.message.chat.id, video=downloaded, thumb=thumb_path, caption=cap, duration=duration, progress=download_progress_callback, progress_args=("📤 **Upload Started...** 🙏 **Thanks To All Who Supported** ❤️", sts, c_time))
    except Exception as e:
        return await sts.edit(f"❌ **Error:** {e}")

    # Clean up downloaded files
    os.remove(downloaded)
    if thumb_path:
        os.remove(thumb_path)

    await sts.delete()
