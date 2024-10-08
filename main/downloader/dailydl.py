import time, os, subprocess
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

# Function to extract audio streams from video
async def extract_audio(video_path, video_title, sts, bot, msg):
    extract_dir = os.path.dirname(video_path) + "/extract"
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)
    
    # Probe the video file for audio streams
    video_streams_data = ffmpeg.probe(video_path)
    audios = []

    for stream in video_streams_data.get("streams"):
        if stream["codec_type"] == "audio":
            audios.append(stream)

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
            progress=progress_message,
            progress_args=(f"🎧 Uploading {video_title}.mka... 📤", sts, c_time),
        )
        os.remove(extracted_audio_path)
        await sts.edit(f"✅ Audio extracted and uploaded: {video_title}.mka")
    else:
        await sts.edit(f"❌ Failed to extract audio from {video_title}")

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

            # Extract audio and upload after video
            await extract_audio(downloaded, video_title, sts, bot, msg)
            
            # Clean up video and thumbnail
            os.remove(downloaded)
            if thumbnail_path:
                os.remove(thumbnail_path)

            await sts.edit(f"✅ Successfully processed: {video_title}")

        except Exception as e:
            await msg.reply_text(f"❌ Failed to process {url}. Error: {str(e)}")

    await msg.reply_text("🎉 All URLs processed successfully!")
