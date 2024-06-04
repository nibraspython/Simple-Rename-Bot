import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

# Initialize Pyrogram client
app = Client("video_to_mp3_bot")

# /convert command handler
@Client.on_message(filters.private & filters.command("convert") & filters.user(ADMIN))
async def convert_to_mp3(bot, msg):
    chat_id = msg.chat.id
    await msg.reply_text("🔄 Please send the video file you want to convert to MP3.")

# Handler for receiving the video file
@app.on_message(filters.private & filters.video & filters.user(ADMIN))
async def receive_video(bot, msg: Message):
    chat_id = msg.chat.id
    video = msg.video
    if video:
        try:
            await msg.reply_text("📥 Video received. Converting to MP3...")
            sts = await msg.reply_text("🔄 Converting...")
            c_time = time.time()
            downloaded = await bot.download_media(
                video,
                progress=progress_message,
                progress_args=("📥 Downloading...", sts, c_time)
            )
            mp3_path = os.path.join(DOWNLOAD_LOCATION, f"{video.file_id}.mp3")

            try:
                video_clip = VideoFileClip(downloaded)
                audio_clip = video_clip.audio
                audio_clip.write_audiofile(mp3_path)
                audio_clip.close()
                video_clip.close()
            except Exception as e:
                await sts.edit(f"❌ Error during conversion: {e}")
                return

            filesize = humanbytes(os.path.getsize(mp3_path))
            await sts.edit("🚀 Uploading MP3 file... 📤")
            c_time = time.time()
            try:
                await bot.send_audio(
                    chat_id,
                    audio=mp3_path,
                    caption=f"🎵 Converted MP3nn💽 Size: {filesize}",
                    progress=progress_message,
                    progress_args=("🚀 Uploading MP3 file...", sts, c_time)
                )
            except Exception as e:
                await sts.edit(f"❌ Error during upload: {e}")
                return

            os.remove(downloaded)
            os.remove(mp3_path)
            await sts.delete()
            await msg.reply_text("✅ MP3 file converted and uploaded successfully!")
        except Exception as e:
            print(f"❌ Error: {e}")
