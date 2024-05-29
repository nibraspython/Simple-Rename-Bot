import time
import os
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

# Dictionary to keep track of users awaiting video input after /convert command
user_convert_requests = {}

@Client.on_message(filters.private & filters.command("convert") & filters.user(ADMIN))
async def convert_command(bot, msg):
    user_id = msg.from_user.id
    user_convert_requests[user_id] = True
    await msg.reply_text("Please send the video you want to convert to MP3.")

@Client.on_message(filters.private & filters.user(ADMIN) & filters.video)
async def convert_to_mp3(bot, msg):
    user_id = msg.from_user.id
    if user_id not in user_convert_requests:
        return

    # Remove the user from the conversion request list
    del user_convert_requests[user_id]

    reply = msg
    media = reply.video
    if not media:
        return await msg.reply_text("Please send a valid video file to convert to MP3.")
    
    og_media = getattr(reply, reply.media.value)
    new_name = "output.mp3"  # Default name for the output file
    sts = await msg.reply_text("🔄 Trying to Download.....📥")
    c_time = time.time()
    downloaded = await reply.download(file_name=os.path.join(DOWNLOAD_LOCATION, new_name), progress=progress_message, progress_args=("Download Started..... **Thanks To All Who Supported ❤**", sts, c_time))

    try:
        # Extract audio from video
        video_clip = VideoFileClip(downloaded)
        audio_path = os.path.join(DOWNLOAD_LOCATION, new_name)
        video_clip.audio.write_audiofile(audio_path)
        duration = int(video_clip.duration)
        video_clip.close()

        # Get file size of the new audio file
        file_size = humanbytes(os.path.getsize(audio_path))

        if CAPTION:
            try:
                cap = CAPTION.format(file_name=new_name, file_size=file_size, duration=duration)
            except Exception as e:
                return await sts.edit(text=f"Your caption Error: unexpected keyword ●> ({e})")
        else:
            cap = f"{new_name}\n\n💽 size: {file_size}\n🕒 duration: {duration} seconds"

        await sts.edit("🚀 Uploading started..... 📤**Thanks To All Who Supported ❤**")
        c_time = time.time()
        await bot.send_audio(
            msg.chat.id,
            audio=audio_path,
            caption=cap,
            progress=progress_message,
            progress_args=("Upload Started..... **Thanks To All Who Supported ❤**", sts, c_time)
        )
    except Exception as e:
        return await sts.edit(f"Error: {e}")
    finally:
        try:
            os.remove(downloaded)
            os.remove(audio_path)
        except:
            pass
        await sts.delete()

# Ensure you run your Pyrogram Client here
