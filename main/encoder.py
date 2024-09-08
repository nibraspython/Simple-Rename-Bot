import os
import time
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import subprocess

video_message_store = {}

@Client.on_message(filters.private & filters.command("convert") & filters.user(ADMIN))
async def convert_video(bot, msg):
    await msg.reply_text("🎥 Please send the video you want to convert to a specific resolution.")

@Client.on_message(filters.private & filters.video & filters.user(ADMIN))
async def receive_video(bot, msg):
    video = msg.video
    video_name = video.file_name
    buttons = InlineKeyboardMarkup(
        [[InlineKeyboardButton("720p", callback_data=f"720p_{msg.id}"),
          InlineKeyboardButton("480p", callback_data=f"480p_{msg.id}")]]
    )
    video_message_store[msg.id] = msg
    await msg.reply_text(f"🎞 Video received: **{video_name}**\nSelect the resolution you want to convert to:", 
                         reply_markup=buttons)

@Client.on_callback_query(filters.regex(r"^(720p|480p)_(\d+)$"))
async def convert_resolution(bot, query):
    resolution, msg_id = query.data.split("_")
    msg_id = int(msg_id)
    
    msg = video_message_store.get(msg_id)
    if not msg or not msg.video:
        return await query.message.edit_text("⚠️ Error: The video message could not be found. Please try again.")

    sts = await query.message.reply_text(f"📥 Downloading video... Please wait.")
    c_time = time.time()
    try:
        downloaded = await msg.download(DOWNLOAD_LOCATION, progress=progress_message, progress_args=("Downloading...", sts, c_time))
    except Exception as e:
        return await sts.edit(f"⚠️ Error: Download failed. {str(e)}")
    
    if not downloaded:
        return await sts.edit("⚠️ Error: Download failed. Please try again.")
    
    await sts.edit(f"✅ Download completed.\n⚙️ Converting to {resolution}... Please wait.")
    
    # Extract file name without extension
    base_name = os.path.splitext(os.path.basename(downloaded))[0]
    output_file = os.path.join(DOWNLOAD_LOCATION, f"{base_name}_{resolution}.mp4")
    
    ffmpeg_cmd = f"ffmpeg -i '{downloaded}' -vf 'scale=-1:{resolution}' '{output_file}'"
    
    result = subprocess.run(ffmpeg_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        return await sts.edit(f"⚠️ ffmpeg Error: {result.stderr}")
    
    filesize = humanbytes(os.path.getsize(output_file))
    
    # Get video duration
    ffprobe_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 '{output_file}'"
    duration = int(float(subprocess.check_output(ffprobe_cmd, shell=True).decode().strip()))

    cap = f"🎥 **Converted Video**\n📁 **File Name**: `{os.path.basename(output_file)}`\n💽 **Size**: {filesize}\n🕒 **Duration**: {duration} seconds\n📏 **Resolution**: {resolution}"

    await sts.edit("🚀 Uploading converted video... Please wait.")
    c_time = time.time()
    try:
        await bot.send_video(msg.chat.id, video=output_file, caption=cap, progress=progress_message, progress_args=("Uploading...", sts, c_time))
    except Exception as e:
        return await sts.edit(f"Error: {e}")

    try:
        os.remove(downloaded)
        os.remove(output_file)
    except:
        pass

    await sts.delete()
    video_message_store.pop(msg_id, None)
