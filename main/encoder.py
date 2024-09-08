import time, os
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip
from moviepy.video.fx import resize
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

@Client.on_message(filters.private & filters.command("encode") & filters.user(ADMIN))
async def encode_file(bot, msg):
    await msg.reply_text("📥 Send your video to encode to a specific resolution.")

@Client.on_message(filters.private & filters.reply & filters.user(ADMIN))
async def receive_video(bot, msg):
    if msg.reply_to_message and msg.reply_to_message.text == "📥 Send your video to encode to a specific resolution.":
        media = msg.document or msg.video
        if not media:
            return await msg.reply_text("❌ Please send a video file.")

        try:
            og_media = media
            file_name = og_media.file_name or "video.mp4"

            # Reply with resolution selection options
            keyboard = [
                [InlineKeyboardButton("720p", callback_data="720p")],
                [InlineKeyboardButton("480p", callback_data="480p")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await msg.reply_text("🎥 Video received! Choose the resolution to encode:", reply_markup=reply_markup)
        except Exception as e:
            await msg.reply_text(f"🚨 An error occurred: {e}")

@Client.on_callback_query()
async def handle_resolution_selection(bot, query):
    resolution = query.data
    msg = query.message

    if resolution not in ["720p", "480p"]:
        return await query.answer("Invalid resolution selected.", show_alert=True)
    
    try:
        # Notify user that encoding has started
        await query.message.edit("🔄 Downloading video... 📥")

        c_time = time.time()
        downloaded_file = await bot.download_media(msg.reply_to_message, file_name=f"downloaded_video.mp4", progress=progress_message, progress_args=("Download in progress... 📥", query.message, c_time))
        
        # Notify user that download is complete
        await query.message.edit("✅ Download completed! Encoding video to selected resolution...")
        
        # Encode video
        new_file_name = f"encoded_video_{resolution}.mp4"
        video_clip = VideoFileClip(downloaded_file)
        if resolution == "720p":
            new_size = (1280, 720)
        elif resolution == "480p":
            new_size = (854, 480)
        
        resized_clip = resize(video_clip, newsize=new_size)
        resized_clip.write_videofile(new_file_name, codec='libx264')
        video_clip.close()
        
        # Notify user that encoding is complete
        await query.message.edit("🔄 Encoding video to selected resolution... 🕒")
        
        # Prepare for upload
        await query.message.edit("🚀 Uploading started... 📤 Thanks To All Who Supported ❤")
        c_time = time.time()
        try:
            await bot.send_video(msg.chat.id, video=new_file_name, caption=f"📹 Encoded video in {resolution} resolution.", progress=progress_message, progress_args=("Upload Started... 📤 Thanks To All Who Supported ❤", query.message, c_time))
        except Exception as e:
            return await query.message.edit(f"🚨 Error: {e}")
        
        # Clean up files
        try:
            os.remove(downloaded_file)
            os.remove(new_file_name)
        except:
            pass

        await query.message.delete()
    except Exception as e:
        await query.message.edit(f"🚨 An error occurred: {e}")
