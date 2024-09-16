import os
import time
import requests
import yt_dlp as youtube_dl
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from moviepy.editor import VideoFileClip
from PIL import Image
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import humanbytes
import math


async def progress_message(current, total, message, start_time):
    """Generates a progress bar for the file upload process."""
    now = time.time()
    diff = now - start_time

    if total == 0:
        percentage = 0
    else:
        percentage = current * 100 / total

    speed = current / diff if diff > 0 else 0
    time_remaining = (total - current) / speed if speed > 0 else 0

    current_human = humanbytes(current)
    total_human = humanbytes(total)

    progress_bar = "[{0}{1}]".format(
        ''.join(["●" for i in range(math.floor(percentage / 10))]),
        ''.join(["○" for i in range(10 - math.floor(percentage / 10))])
    )

    estimated_time = time.strftime("%M:%S", time.gmtime(time_remaining))

    await message.edit_text(
        f"**Progress:** {progress_bar} {percentage:.2f}%\n"
        f"**Downloaded:** {current_human} / {total_human}\n"
        f"**Speed:** {humanbytes(speed)}/s\n"
        f"**Estimated Time Remaining:** {estimated_time}"
    )


def download_progress_hook(d, message, start_time):
    """Progress hook to be used in yt-dlp for synchronous progress tracking."""
    if d['status'] == 'downloading':
        current = d['downloaded_bytes']
        total = d.get('total_bytes', 0)
        loop = message._client.loop
        loop.create_task(progress_message(current, total, message, start_time))


@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def ytdl(bot, msg):
    await msg.reply_text("🎥 **Please send your YouTube links to download.**")


@Client.on_message(filters.private & filters.user(ADMIN) & filters.regex(r'https?://(www\.)?youtube\.com/watch\?v='))
async def youtube_link_handler(bot, msg):
    url = msg.text.strip()

    processing_message = await msg.reply_text("🔄 **Processing your request...**")

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
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

    available_resolutions = []
    available_audio = []

    for f in formats:
        if f['ext'] == 'mp4' and f.get('vcodec') != 'none':
            resolution = f"{f['height']}p"
            fps = f.get('fps', None)
            if fps in [50, 60]:
                resolution += f"{fps}fps"
            filesize = f.get('filesize')
            if filesize:
                filesize_str = humanbytes(filesize)
                format_id = f['format_id']
                available_resolutions.append((resolution, filesize_str, format_id))
        elif f['ext'] in ['m4a', 'webm'] and f.get('acodec') != 'none':
            audio_bitrate = f.get('abr', 'N/A')
            filesize = f.get('filesize')
            if filesize:
                filesize_str = humanbytes(filesize)
                format_id = f['format_id']
                available_audio.append((audio_bitrate, filesize_str, format_id))

    buttons = []
    row = []
    for resolution, size, format_id in available_resolutions:
        button_text = f"🎬 {resolution} - {size}"
        callback_data = f"yt_{format_id}_{resolution}_{url}"
        row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    if available_audio:
        buttons.append([InlineKeyboardButton("🎧 Audio", callback_data=f"audio_{url}")])

    buttons.append([InlineKeyboardButton("🖼️ Thumbnail", callback_data=f"thumb_{url}")])
    buttons.append([InlineKeyboardButton("📝 Description", callback_data=f"desc_{url}")])
    
    markup = InlineKeyboardMarkup(buttons)

    caption = (
        f"**🎬 Title:** {title}\n"
        f"**👀 Views:** {views}\n"
        f"**👍 Likes:** {likes}\n\n"
        f"📥 **Select your resolution or audio format:**"
    )

    thumb_response = requests.get(thumb_url)
    thumb_path = os.path.join(DOWNLOAD_LOCATION, 'thumb.jpg')
    with open(thumb_path, 'wb') as thumb_file:
        thumb_file.write(thumb_response.content)
    await bot.send_photo(chat_id=msg.chat.id, photo=thumb_path, caption=caption, reply_markup=markup)
    os.remove(thumb_path)

    await msg.delete()
    await processing_message.delete()


@Client.on_callback_query(filters.regex(r'^yt_\d+_\d+p(?:\d+fps)?_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler(bot, query):
    data = query.data.split('_')
    format_id = data[1]
    resolution = data[2]
    url = query.data.split('_', 3)[3]

    title = query.message.caption.split('🎬 ')[1].split('\n')[0]

    download_message = await query.message.edit_text(f"⬇️ **Download started...**\n\n**🎬 {title}**\n\n**📹 {resolution}**")

    start_time = time.time()

    ydl_opts = {
        'format': f"{format_id}+bestaudio[ext=m4a]",
        'outtmpl': os.path.join(DOWNLOAD_LOCATION, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'progress_hooks': [lambda d: download_progress_hook(d, download_message, start_time)]
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_path = ydl.prepare_filename(info_dict)
        await download_message.edit_text("✅ **Download completed!**")
    except Exception as e:
        await download_message.edit_text(f"❌ **Error during download:** {e}")
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
        f"📹 **Resolution:** {resolution}\n"
        f"**[🔗 URL]({url})**\n\n"
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
            progress_args=(f"Upload Started... ❤️\n\n**🎬{info_dict['title']}**", query.message, c_time)
        )
    except Exception as e:
        await query.message.edit_text(f"❌ **Error during upload:** {e}")
        return

    await uploading_message.delete()

    if os.path.exists(downloaded_path):
        os.remove(downloaded_path)
    if thumb_path and os.path.exists(thumb_path):
        os.remove(thumb_path)


@Client.on_callback_query(filters.regex(r'^thumb_https?://(www\.)?youtube\.com/watch\?v='))
async def thumb_callback_handler(bot, query):
    url = '_'.join(query.data.split('_')[1:])
    ydl_opts = {'quiet': True}

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        thumb_url = info_dict.get('thumbnail', None)

    if not thumb_url:
        await query.message.edit_text("❌ **No thumbnail found for this video.**")
        return

    thumb_response = requests.get(thumb_url)
    if thumb_response.status_code == 200:
        thumb_path = os.path.join(DOWNLOAD_LOCATION, 'thumb.jpg')
        with open(thumb_path, 'wb') as thumb_file:
            thumb_file.write(thumb_response.content)
        await bot.send_photo(chat_id=query.message.chat.id, photo=thumb_path)
        os.remove(thumb_path)
    else:
        await query.message.edit_text("❌ **Failed to download thumbnail.**")


@Client.on_callback_query(filters.regex(r'^desc_https?://(www\.)?youtube\.com/watch\?v='))
async def description_callback_handler(bot, query):
    url = '_'.join(query.data.split('_')[1:])

    ydl_opts = {'quiet': True}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        description = info_dict.get('description', 'No description available.')

    if len(description) > 4096:
        description = description[:4093] + "..."

    await bot.send_message(chat_id=query.message.chat.id, text=f"**📝 Description:**\n\n{description}")
