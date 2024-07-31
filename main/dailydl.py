import time
import os
import youtube_dl
from pyrogram import Client, filters
from config import ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

bot = Client("my_bot")

# Function to download Dailymotion video
def download_dailymotion_video(url, output_path='.'):
    ydl_opts = {
        'outtmpl': f'{output_path}/%(title)s.%(ext)s',
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

@bot.on_message(filters.private & filters.command("video") & filters.user(ADMIN))
async def ask_for_video_url(bot, msg):
    await msg.reply_text("Please send me the Dailymotion video URL.")

@bot.on_message(filters.private & filters.user(ADMIN))
async def download_and_upload_video(bot, msg):
    video_url = msg.text
    if not video_url.startswith("https://www.dailymotion.com/embed/video/"):
        return await msg.reply_text("Invalid URL. Please provide a valid Dailymotion video URL.")
    
    output_directory = "/content"
    await msg.reply_text("🔄 Downloading the video from Dailymotion.....📥")
    
    try:
        download_dailymotion_video(video_url, output_directory)
    except Exception as e:
        return await msg.reply_text(f"Error during download: {e}")
    
    # Find the downloaded file
    video_files = [f for f in os.listdir(output_directory) if f.endswith(('.mp4', '.mkv'))]
    if not video_files:
        return await msg.reply_text("Failed to download the video.")
    
    video_path = os.path.join(output_directory, video_files[0])
    sts = await msg.reply_text("🔄 Trying to Upload.....📤")
    c_time = time.time()
    
    video_title = os.path.basename(video_path)
    filesize = humanbytes(os.path.getsize(video_path))
    
    # Get video duration
    video_clip = VideoFileClip(video_path)
    duration = int(video_clip.duration)
    video_clip.close()
    
    cap = f"{video_title}\n\n💽 size: {filesize}\n🕒 duration: {duration} seconds"
    
    await sts.edit("🚀 Uploading started..... 📤**Thanks To All Who Supported ❤**")
    c_time = time.time()
    try:
        await bot.send_video(msg.chat.id, video=video_path, caption=cap, duration=duration, progress=progress_message, progress_args=("Upload Started..... **Thanks To All Who Supported ❤**", sts, c_time))
    except Exception as e:
        return await sts.edit(f"Error: {e}")
    
    try:
        os.remove(video_path)
    except:
        pass
    
    await sts.delete()
