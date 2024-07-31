import time
import os
from pyrogram import Client, filters
from config import ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

bot = Client("my_bot")

@bot.on_message(filters.private & filters.command("upload") & filters.user(ADMIN))
async def upload_video(bot, msg):
    await msg.reply_text("Please send me the path to your video in Colab.")

@bot.on_message(filters.private & filters.text & filters.user(ADMIN))
async def get_video_path(bot, msg):
    video_path = msg.text
    if not os.path.exists(video_path):
        return await msg.reply_text("File not found. Please provide a valid path.")
    
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
    
    await sts.delete()

if __name__ == "__main__":
    bot.run()
