import time, os
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from yt_dlp import YoutubeDL
import requests

# Dailymotion Download Function
def download_dailymotion(url):
    ydl_opts = {
        'format': 'best',  # download the best quality
        'outtmpl': f'{DOWNLOAD_LOCATION}/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        thumbnail_url = info.get('thumbnail')  # Get the thumbnail URL from the info
        return file_path, info.get('title'), info.get('duration', 0), info.get('filesize', 0), thumbnail_url

# Function to download the thumbnail
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
    
    urls = reply.text.split()  # Split the message to extract multiple URLs
    if not urls:
        return await msg.reply_text("Please provide valid Dailymotion URLs.")

    # Iterate over each URL
    for url in urls:
        try:
            # Display processing message
            sts = await msg.reply_text(f"🔄 Processing your request for {url}...")

            # Start downloading the video
            c_time = time.time()
            downloaded, video_title, duration, file_size, thumbnail_url = download_dailymotion(url)
            human_size = humanbytes(file_size)
            
            await sts.edit(f"📥 Downloading: {video_title}\nResolution: Highest\n💽 Size: {human_size}")
            
            # Download complete message
            await sts.edit("✅ Download Completed! 📥")
            
            # Download the thumbnail from the video
            thumbnail_path = download_thumbnail(thumbnail_url, video_title)

            # Prepare the caption with emojis
            cap = f"🎬 **{video_title}**\n\n💽 Size: {human_size}\n🕒 Duration: {duration // 60} mins {duration % 60} secs"
            
            # Upload to Telegram
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
            
            # Remove downloaded files
            os.remove(downloaded)
            if thumbnail_path:
                os.remove(thumbnail_path)
                
            await sts.edit(f"✅ Successfully uploaded: {video_title}")

        except Exception as e:
            await msg.reply_text(f"❌ Failed to process {url}. Error: {str(e)}")

    # All URLs processed
    await msg.reply_text("🎉 All URLs processed successfully!")
