from pyrogram import Client, filters
import os
import requests
import time
from moviepy.editor import VideoFileClip
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Dictionary to keep track of users awaiting confirmation after sending a video or link
user_convert_requests = {}

@Client.on_message(filters.private & filters.command("convert"))
async def convert_command(bot, msg):
    await msg.reply_text("Please send the video or direct link to the video you want to convert to MP3.")
    # Starting progress message
    sts = await bot.send_message(msg.chat.id, "🔄 Waiting for your confirmation...")
    c_time = time.time()
    progress_message(0, 100, sts, c_time)  # Change 100 to the total size if known

@Client.on_message(filters.private & (filters.video | filters.text))
async def handle_video_or_link(bot, msg):
    user_id = msg.from_user.id
    if msg.video:
        media = msg.video
        file_name = media.file_name
        user_convert_requests[user_id] = {'type': 'video', 'media': media}
        await msg.reply_text(
            f"**Convert to MP3 🎵**\n\nFile: {file_name}\n\nAre you sure you want to convert this file?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{user_id}"), InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
            ])
        )
    elif msg.text and msg.text.lower().startswith("http"):
        file_name = os.path.basename(msg.text.split("?")[0])  # Get file name from URL
        user_convert_requests[user_id] = {'type': 'link', 'url': msg.text}
        await msg.reply_text(
            f"**Convert to MP3 🎵**\n\nFile: {file_name}\n\nAre you sure you want to convert this file?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{user_id}"), InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{user_id}")]
            ])
        )
    # Starting progress message here
    sts = await bot.send_message(msg.chat.id, "🔄 Waiting for your confirmation...")
    c_time = time.time()
    progress_message(0, 100, sts, c_time)  # Change 100 to the total size if known

@Client.on_callback_query(filters.regex(r"^(confirm|cancel)_(\d+)$"))
async def confirm_or_cancel(bot, query):
    # Your existing code for confirm or cancel
