import os
import time
import requests
import yt_dlp as youtube_dl
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from moviepy.editor import VideoFileClip
from PIL import Image
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes

@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def ytdl(bot, msg):
    await msg.reply_text("🎥 **Please send your YouTube links to download.**")

@Client.on_message(filters.private & filters.user(ADMIN) & filters.regex(r'https?://(www\.)?youtube\.com/watch\?v='))
async def youtube_link_handler(bot, msg):
    url = msg.text.strip()

    # Send processing message
    processing_message = await msg.reply_text("🔄 **Processing your request...**")

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',  # Prefer AVC/AAC format
        'noplaylist': True,
        'quiet': True
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        title = info_dict.get('title', 'Unknown Title')
        views = info_dict.get('view_count', 'N/A')
        likes = info_dict.get('like_count', 'N/A')
        thumb_url = info_dict.get('thumbnail', None)
        description = info_dict.get('description', 'No description available.')
        formats = info_dict.get('formats', [])

    # Extract all available resolutions with their sizes
    available_resolutions = []

    for f in formats:
        if f['ext'] == 'mp4' and f.get('vcodec') != 'none':  # Check for video formats
            resolution = f"{f['height']}p"  # e.g., '720p'
            filesize = f.get('filesize')  # Fetch the filesize
            if filesize:  # Only process if filesize is not None
                filesize_str = humanbytes(filesize)  # Convert size to human-readable format
                format_id = f['format_id']
                available_resolutions.append((resolution, filesize_str, format_id))

    buttons = []
    row = []
    for resolution, size, format_id in available_resolutions:
        button_text = f"🎬 {resolution} - {size}"
        callback_data = f"yt_{format_id}_{resolution}_{url}"
        row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        if len(row) == 2:  # Adjust the number of buttons per row if needed
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("📝 Description", callback_data=f"desc_{url}")])
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

    await msg.delete()
    await processing_message.delete()

@Client.on_callback_query(filters.regex(r'^yt_\d+_\d+p_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler(bot, query):
    data = query.data.split('_')
    format_id = data[1]
    resolution = data[2]
    url = '_'.join(data[3:])

    await query.message.edit_text("⬇️ **Download started...**")

    ydl_opts = {
        'format': f"{format_id}+bestaudio[ext=m4a]",  # Ensure AVC video and AAC audio
        'outtmpl': os.path.join(DOWNLOAD_LOCATION, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        }]
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_path = ydl.prepare_filename(info_dict)
        await query.message.edit_text("✅ **Download completed!**")
    except Exception as e:
        await query.message.edit_text(f"❌ **Error during download:** {e}")
        return

    final_filesize = os.path.getsize(downloaded_path)
    video = VideoFileClip(downloaded_path)
    duration = int(video.duration)
    video_width, video_height = video.size
    filesize = humanbytes(final_filesize)

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
        f"📹 **Resolution:** {resolution}\n\n"
        f"✅ **Download completed!**"
    )

    uploading_message = await query.message.edit_text("🚀 **Uploading started...** 📤")

    c_time = time.time()
    try:
        await bot.send_video(
            chat_id=query.message.chat.id,
            video=downloaded_path,
            thumb=thumb_path,
            caption=caption,
            duration=duration,
            progress=progress_message,
            progress_args=("Upload Started..... Thanks To All Who Supported ❤️"
                          "{info_dict['title']}" , query.message, c_time)
        )
    except Exception as e:
        await query.message.edit_text(f"❌ **Error during upload:** {e}")
        return

    # Remove the progress message after the video is uploaded
    await uploading_message.delete()

    os.remove(downloaded_path)
    if thumb_path:
        os.remove(thumb_path)

@Client.on_callback_query(filters.regex(r'^desc_https?://(www\.)?youtube\.com/watch\?v='))
async def description_callback_handler(bot, query):
    url = ''.join(query.data.split('_')[1:])
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'quiet': True
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        description = info_dict.get('description', 'No description available.')

    await query.message.reply_text(f"📝 Description:\n\n{description}")
