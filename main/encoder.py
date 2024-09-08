import time, os
import ffmpeg
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message
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
    try:
        probe = ffmpeg.probe(downloaded)
        duration = float(probe['streams'][0]['duration'])
        duration_str = f"{int(duration // 60)}m {int(duration % 60)}s"
    except Exception as e:
        duration_str = "Unknown duration"
        print(f"Error getting video duration: {e}")

    # Determine the output file name and resolution parameters
    encoded_file = os.path.join(DOWNLOAD_LOCATION, f"encoded_{resolution}_{os.path.basename(downloaded)}")
    resolution_params = {
        "720p": "1280x720",
        "480p": "854x480"
    }.get(resolution, "1280x720")  # Default to 720p if resolution is not found

    # Use ffmpeg to encode the video
    await sts.edit(f"🎞️ Encoding `{video.file_name}` to {resolution}.....")
    try:
        ffmpeg.input(downloaded).output(encoded_file, vf=f"scale={resolution_params}", vcodec='libx264', preset='fast').run(overwrite_output=True)
    except ffmpeg.Error as e:
        await sts.edit(f"❌ Encoding error: {e}")
        return

    await sts.edit(f"✅ Encoding completed: `{video.file_name}` to {resolution}")

    # Start uploading the encoded video with duration
    await sts.edit(f"🚀 Uploading encoded video..... 📤")
    c_time = time.time()
    await bot.send_video(callback_query.message.chat.id, video=encoded_file, caption=f"Encoded to {resolution}\n🕒 Duration: {duration_str}", duration=duration, progress=progress_message, progress_args=(f"Uploading `{video.file_name}`", sts, c_time))

    # Clean up
    try:
        os.remove(downloaded)
        os.remove(encoded_file)
    except Exception as e:
        print(f"Cleanup error: {e}")

    await sts.delete()
