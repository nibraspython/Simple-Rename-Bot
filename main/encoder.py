import time, os
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

@Client.on_message(filters.private & filters.command("convert") & filters.user(ADMIN))
async def convert_video(bot, msg):
    await msg.reply_text("🎥 Please send the video you want to convert to a specific resolution.")

@Client.on_message(filters.private & filters.video & filters.user(ADMIN))
async def receive_video(bot, msg):
    video = msg.video
    video_name = video.file_name
    buttons = [
        [("720p", "720p"), ("480p", "480p")]
    ]
    await msg.reply_text(f"🎞 Video received: **{video_name}**\nSelect the resolution you want to convert to:", 
                         reply_markup=InlineKeyboardMarkup(buttons))

@Client.on_callback_query(filters.regex("720p|480p"))
async def convert_resolution(bot, query):
    resolution = query.data
    msg = query.message.reply_to_message
    reply = query.message
    sts = await reply.reply_text(f"📥 Downloading video... Please wait.")
    c_time = time.time()
    downloaded = await msg.download(progress=progress_message, progress_args=("Download Started..... Thanks To All Who Supported ❤", sts, c_time))
    
    # Get video duration and other info
    video_clip = VideoFileClip(downloaded)
    duration = int(video_clip.duration)
    width, height = video_clip.size
    video_clip.close()

    await sts.edit("✅ Download completed.\n⚙️ Converting to {resolution}... Please wait.")

    # Convert video to the selected resolution
    output_file = f"{DOWNLOAD_LOCATION}/{os.path.splitext(os.path.basename(downloaded))[0]}_{resolution}.mp4"
    if resolution == "720p":
        new_height = 720
    else:  # 480p
        new_height = 480
    new_width = int(width * new_height / height)
    video_clip = VideoFileClip(downloaded)
    video_clip_resized = video_clip.resize((new_width, new_height))
    video_clip_resized.write_videofile(output_file)
    video_clip.close()
    video_clip_resized.close()

    filesize = humanbytes(os.path.getsize(output_file))

    cap = f"🎥 **Converted Video**\n📁 **File Name**: `{os.path.basename(output_file)}`\n💽 **Size**: {filesize}\n🕒 **Duration**: {duration} seconds\n📏 **Resolution**: {resolution}"

    await sts.edit("🚀 Uploading converted video... Please wait.")
    c_time = time.time()
    try:
        await bot.send_video(msg.chat.id, video=output_file, caption=cap, progress=progress_message, progress_args=("Upload Started..... Thanks To All Who Supported ❤", sts, c_time))
    except Exception as e:
        return await sts.edit(f"Error: {e}")

    try:
        os.remove(downloaded)
        os.remove(output_file)
    except:
        pass
    await sts.delete()
