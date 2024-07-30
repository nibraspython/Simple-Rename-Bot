import time
import os
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip
import youtube_dl

@Client.on_message(filters.private & filters.command("dailymotion") & filters.user(ADMIN))
async def download_dailymotion_video(bot, msg):
    if len(msg.command) < 2:
        return await msg.reply_text("Please provide a Dailymotion video URL.")
    
    url = msg.text.split(" ", 1)[1]
    sts = await msg.reply_text("🔄 Trying to Download.....📥")
    c_time = time.time()

    # Download the video using youtube-dl
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_LOCATION, '%(title)s.%(ext)s'),
        'progress_hooks': [lambda d: progress_message(d, sts, c_time)]
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        downloaded = ydl.prepare_filename(info_dict)
        video_title = info_dict.get('title', 'video').replace(' ', '_') + '.' + info_dict.get('ext', 'mp4')
        new_name = os.path.join(DOWNLOAD_LOCATION, video_title)
        os.rename(downloaded, new_name)
        filesize = humanbytes(os.path.getsize(new_name))

    # Get video duration
    video_clip = VideoFileClip(new_name)
    duration = int(video_clip.duration)
    video_clip.close()

    if CAPTION:
        try:
            cap = CAPTION.format(file_name=video_title, file_size=filesize, duration=duration)
        except Exception as e:
            return await sts.edit(text=f"Your caption Error: unexpected keyword ●> ({e})")
    else:
        cap = f"{video_title}\n\n💽 size: {filesize}\n🕒 duration: {duration} seconds"

    dir = os.listdir(DOWNLOAD_LOCATION)
    if len(dir) == 0:
        file_thumb = None
    else:
        try:
            og_thumbnail = f"{DOWNLOAD_LOCATION}/thumbnail.jpg"
        except Exception as e:
            print(e)
            og_thumbnail = None

    await sts.edit("🚀 Uploading started..... 📤**Thanks To All Who Supported ❤**")
    c_time = time.time()
    try:
        await bot.send_video(msg.chat.id, video=new_name, thumb=og_thumbnail, caption=cap, duration=duration, progress=progress_message, progress_args=("Upload Started..... **Thanks To All Who Supported ❤**", sts, c_time))
    except Exception as e:
        return await sts.edit(f"Error: {e}")
    try:
        if file_thumb:
            os.remove(file_thumb)
        os.remove(new_name)
    except:
        pass
    await sts.delete()
