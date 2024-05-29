import time, os
from pyrogram import Client, filters
from pyrogram.types import Message  # Add this import
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

# Only handle messages with the "/convert" command and from the authorized user
@Client.on_message(filters.private & filters.command("convert") & filters.user(ADMIN))
async def convert_to_mp3(bot, msg):
    await msg.reply_text("Please send a video or provide a direct link to convert to MP3. 😊")

# Handle messages that are either videos, documents, or text links
@Client.on_message(filters.private & (filters.video | filters.document | filters.text) & filters.user(ADMIN))
async def handle_conversion(bot, msg):
    # Check if it's a Message object or a raw text link
    if isinstance(msg, Message):  # Use Message class from pyrogram.types
        media = msg.video or msg.document
    else:
        media = None

    # If there's no media and it's not a direct link, reply with instructions
    if not media and not msg.text.startswith("http"):
        return await msg.reply_text("Please reply to a video message or provide a direct link to convert to MP3.")

    # If it's a media message, check if it's a video or a non-MP4 document
    if media:
        if not media.video and media.document.mime_type != 'video/mp4':
            return await msg.reply_text("Please reply to a video message or provide a direct link to convert to MP3.")
    # If it's a text link, check if it ends with .mp4
    else:
        if not msg.text.endswith(".mp4"):
            return await msg.reply_text("Please provide a valid direct link to an MP4 video.")
        media = msg.text

    new_name = "converted_audio.mp3"
    sts = await msg.reply_text("Trying to Download! 📥")

    c_time = time.time()

    # Download the media if it's a message
    if isinstance(media, Message):
        downloaded = await bot.download_media(media, file_name=new_name, progress=progress_message, progress_args=("Download Started..... 😅", sts, c_time))
    # Otherwise, download the file directly
    else:
        downloaded = await bot.download_file(media, file_name=new_name, progress=progress_message, progress_args=("Download Started..... 😅", sts, c_time))

    filesize = humanbytes(os.path.getsize(downloaded))

    # Get video duration
    video_clip = VideoFileClip(downloaded)
    duration = int(video_clip.duration)
    video_clip.close()

    # Convert the video to MP3
    await sts.edit("Converting to MP3...")
    try:
        audio_path = f'{DOWNLOAD_LOCATION}/{new_name}'
        video_clip = VideoFileClip(downloaded)
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
