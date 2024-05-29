import time
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

# Only handle messages with the "/convert" command and from the authorized user
@Client.on_message(filters.private & filters.command("convert") & filters.user(ADMIN))
async def convert_to_mp3(bot, msg):
    await msg.reply_text("Please send a video or provide a direct link to convert to MP3. 😊")

# Handle media messages or text links after the "/convert" command
@Client.on_message(filters.private & (filters.video | filters.document | filters.text) & filters.reply & filters.user(ADMIN))
async def handle_conversion(bot, msg):
    reply_to_msg = msg.reply_to_message

    # Check if the original message is the conversion command
    if not reply_to_msg or not reply_to_msg.text or "/convert" not in reply_to_msg.text:
        return

    # Determine if the message contains media or a text link
    media = msg.video or msg.document if isinstance(msg, Message) else None
    media_link = msg.text if msg.text and msg.text.startswith("http") else None

    # Ensure the message is either media or a valid URL
    if not media and not media_link:
        return await msg.reply_text("Please reply to a video message or provide a direct link to convert to MP3.")

    new_name = "converted_audio.mp3"
    sts = await msg.reply_text("Trying to Download! 📥")

    c_time = time.time()

    # Download the media if it's a message
    if media:
        downloaded = await bot.download_media(media, file_name=new_name, progress=progress_message, progress_args=("Download Started..... 😅", sts, c_time))
    # Otherwise, download the file directly from the link
    else:
        downloaded = await bot.download_file(media_link, file_name=new_name, progress=progress_message, progress_args=("Download Started..... 😅", sts, c_time))

    filesize = humanbytes(os.path.getsize(downloaded))

    # Get video duration
    try:
        video_clip = VideoFileClip(downloaded)
        duration = int(video_clip.duration)
    except Exception as e:
        await sts.edit(f"Error reading video file: {e}")
        if downloaded:
            os.remove(downloaded)
        return

    # Convert the video to MP3
    await sts.edit("Converting to MP3...")
    try:
        audio_path = f'{DOWNLOAD_LOCATION}/{new_name}'
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()
    except Exception as e:
        return await sts.edit(f"Error: {e}")

    # Remove the downloaded video
    if downloaded:
        os.remove(downloaded)

    cap = f"🎵 {new_name} \n💽 Size: {filesize} \n🕒 Duration: {duration} seconds"

    # Upload the converted MP3
    await sts.edit("Uploading...")
    c_time = time.time()
    try:
        await bot.send_audio(msg.chat.id, audio=audio_path, caption=cap, duration=duration, progress=progress_message, progress_args=("Upload Started..... 😅", sts, c_time))
    except Exception as e:
        return await sts.edit(f"Error: {e}")
    await sts.delete()
