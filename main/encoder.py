import time, os
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip
import moviepy.video.fx.all as vfx
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.private & filters.command("encode") & filters.user(ADMIN))
async def encode_video(bot, msg):
    await msg.reply_text("📥 Please send your video to encode to a specific resolution.")

@Client.on_message(filters.private & filters.user(ADMIN) & filters.video)
async def receive_video(bot, video_msg):
    video = video_msg.video
    filename = video.file_name

    # Inline keyboard for resolution selection
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("720p", callback_data=f"encode_720p|{video_msg.id}")],
        [InlineKeyboardButton("480p", callback_data=f"encode_480p|{video_msg.id}")]
    ])
    
    await video_msg.reply_text(
        f"🎥 Video received: `{filename}`\n\nSelect the resolution you want to encode to:",
        reply_markup=keyboard
    )
    
@Client.on_callback_query(filters.regex(r"^encode_"))
async def start_encoding(bot, callback_query):
    resolution, message_id = callback_query.data.split("|")
    resolution = resolution.split("_")[1]

    video_msg = await bot.get_messages(callback_query.message.chat.id, int(message_id))
    video = video_msg.video

    # Start downloading the video
    sts = await callback_query.message.edit_text(f"🔄 Downloading `{video.file_name}`.....📥")
    c_time = time.time()
    downloaded = await video_msg.download(progress=progress_message, progress_args=(f"Downloading `{video.file_name}`", sts, c_time))

    # Notify download completion
    await sts.edit(f"✅ Download completed: `{video.file_name}`")

    # Get video duration before encoding
    video_clip = VideoFileClip(downloaded)
    duration = int(video_clip.duration)

    # Encode the video to the selected resolution
    await sts.edit(f"🎞️ Encoding `{video.file_name}` to {resolution}.....")
    if resolution == "720p":
        video_clip = video_clip.resize(height=720)
    elif resolution == "480p":
        video_clip = video_clip.resize(height=480)

    encoded_file = os.path.join(DOWNLOAD_LOCATION, f"encoded_{resolution}_{video.file_name}")
    video_clip.write_videofile(encoded_file, logger=None)  # Disable progress bar
    video_clip.close()

    await sts.edit(f"✅ Encoding completed: `{video.file_name}` to {resolution}")

    # Start uploading the encoded video with duration
    await sts.edit("🚀 Uploading encoded video..... 📤")
    c_time = time.time()
    await bot.send_video(callback_query.message.chat.id, video=encoded_file, caption=f"Encoded to {resolution}\n🕒 Duration: {duration} seconds", duration=duration, progress=progress_message, progress_args=(f"Uploading `{video.file_name}`", sts, c_time))

    # Clean up
    try:
        os.remove(downloaded)
        os.remove(encoded_file)
    except:
        pass

    await sts.delete()
