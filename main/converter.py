import time, os
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

@Client.on_message(filters.private & filters.command("convert") & filters.user(ADMIN))
async def convert_to_mp3(bot, msg):
    await msg.reply_text("Please send a video or provide a direct link to convert to MP3. 😊")

@Client.on_message(filters.private & (filters.video | filters.document) & filters.user(ADMIN))
async def handle_conversion(bot, msg):
    media = msg

    if not media.video and not (media.document and media.document.mime_type == 'video/mp4'):
        return await msg.reply_text("Please reply to a video message or provide a direct link to convert to MP3.")

    if media.video:
        og_media = media.video
    elif media.document.mime_type == 'video/mp4':
        og_media = media.document
    else:
        return await msg.reply_text("Please reply to a video message or provide a direct link to convert to MP3.")

    new_name = "converted_audio.mp3"
    sts = await msg.reply_text("Trying to Download! 📥")
    
    c_time = time.time()
    
    downloaded = await og_media.download()

    filesize = humanbytes(og_media.file_size)

    # Get video duration
    video_clip = VideoFileClip(downloaded)
    duration = int(video_clip.duration)
    video_clip.close()

    await sts.edit("Converting to MP3...")
    try:
        audio_path = f'{DOWNLOAD_LOCATION}/{new_name}'
        video_clip = VideoFileClip(downloaded)
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()
    except Exception as e:
        return await sts.edit(f"Error: {e}")

    if downloaded:
        os.remove(downloaded)

    cap = f"🎵 {new_name} \n💽 Size: {filesize} \n🕒 Duration: {duration} seconds"

    await sts.edit("Uploading...")
    c_time = time.time()
    try:
        await bot.send_audio(msg.chat.id, audio=audio_path, caption=cap, duration=duration, progress=progress_message, progress_args=("Upload Started..... 😅", sts, c_time))
    except Exception as e:
        return await sts.edit(f"Error: {e}")
    await sts.delete()
