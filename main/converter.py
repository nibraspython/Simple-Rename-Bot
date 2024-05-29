import time
import os
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

# Dictionary to keep track of users awaiting confirmation after sending a video or link
user_convert_requests = {}

@Client.on_message(filters.private & filters.command("convert") & filters.user(ADMIN))
async def convert_command(bot, msg):
    await msg.reply_text("Please send the video or direct link to the video you want to convert to MP3.")

@Client.on_message(filters.private & filters.user(ADMIN) & (filters.video | filters.text))
async def handle_video_or_link(bot, msg):
    user_id = msg.from_user.id
    if msg.video:
        media = msg.video
        file_name = media.file_name
        user_convert_requests[user_id] = {'type': 'video', 'media': media}
    elif msg.text and msg.text.lower().startswith("http"):
        file_name = os.path.basename(msg.text.split("?")[0])  # Get file name from URL
        user_convert_requests[user_id] = {'type': 'link', 'url': msg.text}
    else:
        return await msg.reply_text("Please send a valid video file or direct link to a video.")

    await msg.reply_text(
        f"**Convert to MP3 🎵**\n\nFile: {file_name}\n\nAre you sure you want to convert this file?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{user_id}"), InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
        ])
    )

@Client.on_callback_query(filters.regex(r"^(confirm|cancel)_(\d+)$"))
async def confirm_or_cancel(bot, query):
    action, user_id = query.data.split("_")
    user_id = int(user_id)

    if query.from_user.id != user_id:
        return await query.answer("This action is not for you!", show_alert=True)

    if action == "cancel":
        del user_convert_requests[user_id]
        return await query.message.edit_text("❌ Conversion cancelled.")

    if user_id not in user_convert_requests:
        return await query.message.edit_text("Request expired or invalid.")

    request = user_convert_requests.pop(user_id)

    if request['type'] == 'video':
        media = request['media']
        sts = await query.message.edit_text("🔄 Trying to Download.....📥")
        c_time = time.time()
        downloaded = await bot.download_media(media, file_name=os.path.join(DOWNLOAD_LOCATION, media.file_name), progress=progress_message, progress_args=("Download Started..... **Thanks To All Who Supported ❤**", sts, c_time))
    else:
        url = request['url']
        # Handle direct link download (you might use a library like `requests` to download the file)
        sts = await query.message.edit_text("🔄 Trying to Download from link.....📥")
        c_time = time.time()
        response = requests.get(url, stream=True)
        downloaded = os.path.join(DOWNLOAD_LOCATION, os.path.basename(url.split("?")[0]))
        with open(downloaded, 'wb') as f:
            total_length = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            for data in response.iter_content(chunk_size=4096):
                f.write(data)
                downloaded_size += len(data)
                progress_message(downloaded_size, total_length, sts, c_time)
    
    try:
        # Convert video to MP3
        video_clip = VideoFileClip(downloaded)
        audio_path = os.path.join(DOWNLOAD_LOCATION, "output.mp3")
        await sts.edit("🎥 Converting to MP3..... 🎵")
        video_clip.audio.write_audiofile(audio_path)
        duration = int(video_clip.duration)
        video_clip.close()

        # Get file size of the new audio file
        file_size = humanbytes(os.path.getsize(audio_path))

        if CAPTION:
            try:
                cap = CAPTION.format(file_name="output.mp3", file_size=file_size, duration=duration)
            except Exception as e:
                return await sts.edit(text=f"Your caption Error: unexpected keyword ●> ({e})")
        else:
            cap = f"output.mp3\n\n💽 size: {file_size}\n🕒 duration: {duration} seconds"

        await sts.edit("🚀 Uploading started..... 📤**Thanks To All Who Supported ❤**")
        c_time = time.time()
        await bot.send_audio(
            query.message.chat.id,
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
