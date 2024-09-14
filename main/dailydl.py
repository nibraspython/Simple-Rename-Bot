import os
import time
import asyncio
import random  # For selecting a random timestamp
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes
from yt_dlp import YoutubeDL
from moviepy.editor import VideoFileClip

# Dictionary to track state of chat
chat_state = {}

@Client.on_message(filters.private & filters.command("daily") & filters.user(ADMIN))
async def dailymotion_download(bot, msg):
    chat_state[msg.chat.id] = 'awaiting_url'
    await msg.reply_text("Send your Dailymotion video URL to download.")

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def process_dailymotion_url(bot, msg):
    chat_id = msg.chat.id
    if chat_state.get(chat_id) == 'awaiting_url':
        url = msg.text
        sts = await msg.reply_text(f"🔄 Processing your URL: {url}")

        # Setting up yt-dlp options for highest resolution
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'{DOWNLOAD_LOCATION}/%(title)s.%(ext)s',
            'progress_hooks': [lambda d: download_progress_hook(d, sts, msg)]
        }

        try:
            # Downloading the video using yt-dlp
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                video_title = info_dict.get('title', 'video')
                video_filename = ydl.prepare_filename(info_dict)

            await sts.edit(f"✅ Download completed: {video_title}\n🔄 Now starting to upload...")

            # Get video info (size, duration)
            video_clip = VideoFileClip(video_filename)
            duration = int(video_clip.duration)
            filesize = humanbytes(os.path.getsize(video_filename))

            # Capture a random thumbnail from the video
            random_time = random.uniform(1, duration)  # Pick a random time within video duration
            thumbnail_path = f"{DOWNLOAD_LOCATION}/{video_title}_thumb.jpg"
            video_clip.save_frame(thumbnail_path, t=random_time)  # Save the frame at random timestamp
            video_clip.close()

            # Customize caption with emojis
            cap = f"📁 **Video Name:** {video_title}\n🕒 **Duration:** {duration} seconds"

            # Uploading the video
            await upload_video(bot, msg, video_filename, thumbnail_path, cap, duration, sts)

        except Exception as e:
            await sts.edit(f"❌ Error: {e}")

        # Reset chat state after processing
        chat_state[chat_id] = 'idle'
    else:
        await msg.reply_text("Please send the `/daily` command first to start the download process.")

def download_progress_hook(d, sts, msg):
    if d['status'] == 'downloading':
        percent = d['_percent_str']
        total_size = humanbytes(d['total_bytes'])
        speed = d['_speed_str']
        filename = d['filename']
        c_time = time.time()
        download_text = f"Downloading {filename}\n\nProgress: {percent}\nTotal Size: {total_size}\nSpeed: {speed}"
        asyncio.create_task(sts.edit(download_text))

async def upload_video(bot, msg, video_path, thumbnail, caption, duration, sts):
    c_time = time.time()
    try:
        await bot.send_video(
            msg.chat.id,
            video=video_path,
            thumb=thumbnail,
            caption=caption,  # Caption with emojis
            duration=duration,
            progress=progress_message,
            progress_args=(f"Uploading {os.path.basename(video_path)}... Thanks To All Who Supported ❤", sts, c_time)
        )
    except Exception as e:
        await sts.edit(f"❌ Error during upload: {e}")
    finally:
        # Clean up the downloaded files
        try:
            os.remove(video_path)
            if thumbnail:
                os.remove(thumbnail)
        except:
            pass
        await sts.delete()
