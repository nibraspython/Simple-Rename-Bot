import time
import os
from pyrogram import Client, filters
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.private & filters.command("convert"))
async def convert_to_mp3(bot, msg):
    await msg.reply_text("🎬 Please send the video file or provide a direct link to convert to MP3 🎶")

@Client.on_message(filters.private & ~filters.command(["convert"]) & ~filters.command(["cancel"]) & ~filters.command(["confirm"]))
async def handle_conversion(bot, msg):
    reply = msg.reply_to_message
    if not reply:
        return await msg.reply_text("Please reply to a message with a video file or provide a direct link to convert to MP3.")
    
    # Check if the reply contains a media file or a link
    media = reply.document or reply.video
    if not media and not reply.text:
        return await msg.reply_text("Please reply to a message with a video file or provide a direct link to convert to MP3.")

    # Display confirmation message with inline keyboard
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Confirm ✅", callback_data="confirm"),
                InlineKeyboardButton("Cancel ❌", callback_data="cancel")
            ]
        ]
    )
    await msg.reply_text("🔄 Convert to mp3", reply_markup=keyboard)

@Client.on_callback_query()
async def handle_callback(bot, query):
    if query.data == "confirm":
        await query.answer("Conversion started! 🔄")

        # Download the video file
        sts = await query.message.reply_text("📥 Downloading the video...")
        video = await query.message.reply_to_message.download()

        # Convert video to mp3
        audio_file = f"{video}.mp3"
        video_clip = VideoFileClip(video)
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(audio_file)
        audio_clip.close()
        video_clip.close()
        os.remove(video)

        # Get duration of the audio
        duration = int(audio_clip.duration)
        await sts.edit("🔄 Converting video to MP3...")

        # Upload the audio file
        filesize = os.path.getsize(audio_file)
        await sts.edit("📤 Uploading MP3 file...")
        c_time = time.time()
        try:
            await bot.send_audio(query.message.chat.id, audio_file, caption=f"🎵 {os.path.basename(audio_file)}\n\n🕒 Duration: {duration} seconds", progress=progress_message, progress_args=("Upload in progress...", sts, c_time))
        except Exception as e:
            await sts.edit(f"Error: {e}")
        os.remove(audio_file)
        await sts.delete()

    elif query.data == "cancel":
        await query.message.reply_text("Conversion canceled! ❌")
        await query.answer()

