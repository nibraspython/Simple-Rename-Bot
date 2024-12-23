import time
import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from yt_dlp import YoutubeDL
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip
import ffmpeg
import requests

# Temporary storage for callback query data
callback_data_store = {}

# Function to download Dailymotion videos
def download_dailymotion(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{DOWNLOAD_LOCATION}/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        video_title = info.get('title')
        duration = info.get('duration', 0)
        file_size = info.get('filesize', 0)
        resolution = info.get('height')
        thumbnail_url = info.get('thumbnail')
        return file_path, video_title, duration, file_size, resolution, thumbnail_url

# Function to extract audio streams from video
async def extract_audio(video_path, video_title, sts, bot, msg):
    extract_dir = os.path.dirname(video_path) + "/extract"
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)
    
    video_streams_data = ffmpeg.probe(video_path)
    audios = []
    audio_duration = 0

    for stream in video_streams_data.get("streams"):
        if stream["codec_type"] == "audio":
            audios.append(stream)
            audio_duration = int(float(stream['duration']))

    for audio in audios:
        extract_cmd = [
            "ffmpeg", "-hide_banner", "-i", video_path,
            "-map", f"0:{audio['index']}", "-c", "copy",
            f"{extract_dir}/{video_title}.mka"
        ]
        subprocess.call(extract_cmd)

    extracted_audio_path = f"{extract_dir}/{video_title}.mka"
    if os.path.exists(extracted_audio_path):
        await sts.edit(f"🎧 Extracting audio from {video_title}... 🔄")
        c_time = time.time()
        await bot.send_audio(
            msg.chat.id,
            audio=extracted_audio_path,
            caption=f"🎧 **Extracted Audio**: {video_title}.mka",
            duration=audio_duration,
            progress=progress_message,
            progress_args=(f"🎧 Uploading {video_title}.mka... 📤", sts, c_time),
        )
        os.remove(extracted_audio_path)
    else:
        await sts.edit(f"❌ Failed to extract audio from {video_title}")

# Function to generate thumbnail from video
def generate_thumbnail(video_path):
    thumbnail_path = f"{video_path}_thumbnail.jpg"
    try:
        video_clip = VideoFileClip(video_path)
        video_clip.save_frame(thumbnail_path, t=video_clip.duration / 2)
        video_clip.close()
        return thumbnail_path
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None

# Function to download thumbnail from a URL
def download_thumbnail(thumbnail_url, title):
    if not thumbnail_url:
        return None
    thumbnail_path = f"{DOWNLOAD_LOCATION}/{title}_thumbnail.jpg"
    response = requests.get(thumbnail_url)
    if response.status_code == 200:
        with open(thumbnail_path, 'wb') as f:
            f.write(response.content)
        return thumbnail_path
    return None

@Client.on_message(filters.private & filters.command("dailydl") & filters.user(ADMIN))
async def dailymotion_download(bot, msg):
    reply = msg.reply_to_message
    if not reply or not reply.text:
        return await msg.reply_text("Please reply to a message containing one or more Dailymotion URLs.")
    
    urls = reply.text.split()
    if not urls:
        return await msg.reply_text("Please provide valid Dailymotion URLs.")
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("With Extract Audio 🎬🎧", callback_data="with_audio")],
        [InlineKeyboardButton("Only Video 🎬", callback_data="only_video")]
    ])
    sent_message = await msg.reply("Select your method:", reply_markup=keyboard)
    callback_data_store[sent_message.id] = urls

@Client.on_callback_query(filters.regex("with_audio|only_video"))
async def method_selection(bot, callback_query):
    method = callback_query.data
    message_id = callback_query.message.id
    urls = callback_data_store.get(message_id)
    if not urls:
        return await callback_query.answer("Session expired or invalid request!", show_alert=True)

    await callback_query.answer(f"Selected: {'Extract Audio' if method == 'with_audio' else 'Only Video'}")
    await callback_query.message.delete()
    await process_dailymotion_download(bot, callback_query.message, urls, method)
    del callback_data_store[message_id]

async def process_dailymotion_download(bot, msg, urls, method):
    for url in urls:
        try:
            # Show downloading progress text directly
            downloading_message = await msg.reply_text("📥 Starting download... 🔄")
            c_time = time.time()

            # Start downloading the video
            downloaded, video_title, duration, file_size, resolution, thumbnail_url = download_dailymotion(url)
            human_size = humanbytes(file_size)

            # Update the downloading progress
            await downloading_message.edit(
                f"📥 Downloading: {video_title}\n💽 Size: {human_size}\n📹 Resolution: {resolution}p"
            )

            # Generate or download thumbnail
            thumbnail_path = download_thumbnail(thumbnail_url, video_title)
            if not thumbnail_path:
                thumbnail_path = generate_thumbnail(downloaded)

            # After download is completed, delete the downloading message
            await downloading_message.delete()

            # Show new uploading progress text
            uploading_message = await msg.reply_text(f"🚀 Uploading: {video_title}... 📤")
            c_time = time.time()

            # Upload the video to Telegram
            await bot.send_video(
                msg.chat.id,
                video=downloaded,
                thumb=thumbnail_path if thumbnail_path else None,
                caption=(
                    f"🎬 **{video_title}**\n\n"
                    f"💽 Size: {human_size}\n"
                    f"🕒 Duration: {duration // 60} mins {duration % 60} secs\n"
                    f"📹 Resolution: {resolution}p"
                ),
                duration=duration,
                progress=progress_message,
                progress_args=(f"🚀 Uploading Started\n\n🎬 {video_title} 📤", uploading_message, c_time),
            )

            # Extract audio if the method is "with_audio"
            if method == "with_audio":
                await extract_audio(downloaded, video_title, uploading_message, bot, msg)

            # Clean up files
            os.remove(downloaded)
            if thumbnail_path:
                os.remove(thumbnail_path)

        except Exception as e:
            await msg.reply(f"❌ Failed to process {url}. Error: {str(e)}")

    # Send final completion message
    await msg.reply_text("🎉 All URLs processed successfully!")
