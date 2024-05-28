import time, os
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

@Client.on_message(filters.private & filters.command("trim") & filters.user(ADMIN))
async def trim_video(bot, msg):
    reply = msg.reply_to_message
    if len(msg.command) < 3 or not reply:
        return await msg.reply_text("Please reply to a video with the command: /trim start_time end_time (format: HH:MM:SS)")
    media = reply.video
    if not media:
        return await msg.reply_text("Please reply to a video with the command: /trim start_time end_time (format: HH:MM:SS)")
    
    start_time_str = msg.command[1]
    end_time_str = msg.command[2]

    try:
        start_time = sum(x * int(t) for x, t in zip([3600, 60, 1], start_time_str.split(":")))
        end_time = sum(x * int(t) for x, t in zip([3600, 60, 1], end_time_str.split(":")))
    except ValueError:
        return await msg.reply_text("Invalid time format. Please use HH:MM:SS.")

    sts = await msg.reply_text("Trying to Download.....")
    c_time = time.time()
    downloaded = await reply.download(progress=progress_message, progress_args=("Download Started.....", sts, c_time))
    output_video = f"{os.path.splitext(downloaded)[0]}_trimmed.mp4"

    try:
        # Exclude subtitle streams
        ffmpeg_extract_subclip(downloaded, start_time, end_time, targetname=output_video, codec="copy")
    except Exception as e:
        return await sts.edit(f"Error during trimming: {e}")

    video_clip = VideoFileClip(output_video)
    duration = int(video_clip.duration)
    video_clip.close()

    filesize = humanbytes(os.path.getsize(output_video))
    cap = f"Trimmed Video\n\n💽 size: {filesize}\n🕒 duration: {duration} seconds"

    dir = os.listdir(DOWNLOAD_LOCATION)
    if len(dir) == 0:
        file_thumb = await bot.download_media(media.thumbs[0].file_id)
        og_thumbnail = file_thumb
    else:
        try:
            og_thumbnail = f"{DOWNLOAD_LOCATION}/thumbnail.jpg"
        except Exception as e:
            print(e)
            og_thumbnail = None

    await sts.edit("Uploading started.....")
    c_time = time.time()
    try:
        await bot.send_video(msg.chat.id, video=output_video, thumb=og_thumbnail, caption=cap, duration=duration, progress=progress_message, progress_args=("Upload Started.....", sts, c_time))
    except Exception as e:
        return await sts.edit(f"Error: {e}")
    try:
        if file_thumb:
            os.remove(file_thumb)
        os.remove(downloaded)
        os.remove(output_video)
    except:
        pass
    await sts.delete()
