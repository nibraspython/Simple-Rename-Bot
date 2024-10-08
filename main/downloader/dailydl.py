import time, os
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from yt_dlp import YoutubeDL
import requests
from moviepy.editor import VideoFileClip
import ffmpeg  # For fast audio extraction

# Dailymotion Download Function with Resolution and Thumbnail URL
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

# Function to generate thumbnail from the video if no thumbnail is available
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

# Function to download the thumbnail if available
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

# Function to extract audio in MKA format using ffmpeg
def extract_audio(video_path, audio_path):
    try:
        stream = ffmpeg.input(video_path)
        audio = ffmpeg.output(stream, audio_path, format='mka', acodec='copy')  # Fast extraction
        ffmpeg.run(audio)
        return audio_path
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return None

@Client.on_message(filters.private & filters.command("dailydl") & filters.user(ADMIN))
async def dailymotion_download(bot, msg):
    reply = msg.reply_to_message
    if not reply or not reply.text:
        return await msg.reply_text("Please reply to a message containing one or more Dailymotion URLs.")
    
    urls = reply.text.split()
    if not urls:
        return await msg.reply_text("Please provide valid Dailymotion URLs.")

    for url in urls:
        try:
            sts = await msg.reply_text(f"🔄 Processing your request for {url}...")

            # Start downloading the video
            c_time = time.time()
            downloaded, video_title, duration, file_size, resolution, thumbnail_url = download_dailymotion(url)
            human_size = humanbytes(file_size)

            # Display Downloading Text
            await sts.edit(f"📥 Downloading: {video_title}\nResolution: {resolution}p\n💽 Size: {human_size}")

            # Generate or download thumbnail
            thumbnail_path = download_thumbnail(thumbnail_url, video_title)
            if not thumbnail_path:
                thumbnail_path = generate_thumbnail(downloaded)

            await sts.edit("✅ Download Completed! 📥")

            # Prepare the caption
            cap = f"🎬 **{video_title}**\n\n💽 Size: {human_size}\n🕒 Duration: {duration // 60} mins {duration % 60} secs\n📹 Resolution: {resolution}p"

            # Upload video to Telegram
            await sts.edit(f"🚀 Uploading: {video_title} 📤")
            c_time = time.time()
            await bot.send_video(
                msg.chat.id,
                video=downloaded,
                thumb=thumbnail_path if thumbnail_path else None,
                caption=cap,
                duration=duration,
                progress=progress_message,
                progress_args=(f"🚀 Uploading {video_title}... 📤", sts, c_time),
            )

            await sts.edit(f"🔄 Extracting audio from {video_title}... 🎧")

            # Extract audio
            audio_path = f"{DOWNLOAD_LOCATION}/{video_title}.mka"
            extracted_audio = extract_audio(downloaded, audio_path)

            if extracted_audio:
                # Upload audio with progress
                await sts.edit(f"🚀 Uploading audio for {video_title} 📤")
                c_time = time.time()
                await bot.send_audio(
                    msg.chat.id,
                    audio=extracted_audio,
                    title=video_title,
                    progress=progress_message,
                    progress_args=(f"🚀 Uploading audio for {video_title}... 📤", sts, c_time),
                )
                os.remove(extracted_audio)  # Remove audio file after upload

            # Clean up video and thumbnail
            os.remove(downloaded)
            if thumbnail_path:
                os.remove(thumbnail_path)

            await sts.edit(f"✅ Successfully processed: {video_title}")

        except Exception as e:
            await msg.reply_text(f"❌ Failed to process {url}. Error: {str(e)}")

    await msg.reply_text("🎉 All URLs processed successfully!")
