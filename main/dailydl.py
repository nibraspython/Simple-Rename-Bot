import time
import os
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip
import youtube_dl

@Client.on_message(filters.private & filters.command("download") & filters.user(ADMIN))
async def download_video(bot, msg):
    if len(msg.command) < 2:
        return await msg.reply_text("Please provide a video URL to download.")
    video_url = msg.text.split(" ", 1)[1]
    new_name = video_url.split("/")[-1] + ".mp4"
    
    sts = await msg.reply_text("🔄 Trying to Download.....📥")
    ydl_opts = {
        'outtmpl': os.path.join(DOWNLOAD_LOCATION, new_name),
        'format': 'best'
    }
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            elapsed_time = time.time() - c_time
            progress = d['_percent_str']
            downloaded = humanbytes(d['downloaded_bytes'])
            speed = humanbytes(d['speed'])
            remaining_time = d['eta']
            progress_text = (
                f"**Download Started..... **Thanks To All Who Supported ❤**\n\n"
                f"**Progress:** {progress}\n"
                f"**Downloaded:** {downloaded}\n"
                f"**Speed:** {speed}/s\n"
                f"**Elapsed Time:** {int(elapsed_time)}s\n"
                f"**Estimated Time:** {remaining_time}s"
            )
            await sts.edit(text=progress_text)

    ydl_opts['progress_hooks'] = [progress_hook]
    
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        downloaded = os.path.join(DOWNLOAD_LOCATION, new_name)
    except Exception as e:
        return await sts.edit(f"Error: {e}")
    
    filesize = humanbytes(os.path.getsize(downloaded))

    # Get video duration
    video_clip = VideoFileClip(downloaded)
    duration = int(video_clip.duration)
    video_clip.close()

    if CAPTION:
        try:
            cap = CAPTION.format(file_name=new_name, file_size=filesize, duration=duration)
        except Exception as e:
            return await sts.edit(text=f"Your caption Error: unexpected keyword ●> ({e})")
    else:
        cap = f"{new_name}\n\n💽 size: {filesize}\n🕒 duration: {duration} seconds"

    dir = os.listdir(DOWNLOAD_LOCATION)
    if len(dir) == 0:
        og_thumbnail = None
    else:
        try:
            og_thumbnail = f"{DOWNLOAD_LOCATION}/thumbnail.jpg"
        except Exception as e:
            print(e)
            og_thumbnail = None

    await sts.edit("🚀 Uploading started..... 📤**Thanks To All Who Supported ❤**")
    c_time = time.time()
    try:
        await bot.send_video(msg.chat.id, video=downloaded, thumb=og_thumbnail, caption=cap, duration=duration, progress=progress_message, progress_args=("Upload Started..... **Thanks To All Who Supported ❤**", sts, c_time))
    except Exception as e:
        return await sts.edit(f"Error: {e}")
    try:
        os.remove(downloaded)
    except:
        pass
    await sts.delete()
