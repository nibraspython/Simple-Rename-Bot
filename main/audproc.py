import time, os
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from pydub import AudioSegment  # To trim audio
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import timedelta

# Store user input (temporary storage)
user_inputs = {}

# Helper function to convert HH:MM:SS to seconds
def hhmmss_to_seconds(time_str):
    h, m, s = map(int, time_str.split(':'))
    return timedelta(hours=h, minutes=m, seconds=s).total_seconds()

@Client.on_message(filters.private & filters.command("audio") & filters.user(ADMIN))
async def audio_trim_start(bot, msg):
    reply = msg.reply_to_message
    if not reply or not (reply.audio or reply.document):
        return await msg.reply_text("Please Reply To An Audio File (.mp3 or .mka)")
    
    audio = reply.audio or reply.document
    if not (audio.mime_type.startswith("audio/mpeg") or audio.mime_type.startswith("audio/x-matroska")):
        return await msg.reply_text("Only .mp3 and .mka audio formats are supported.")
    
    # Start session for /audio command
    user_inputs[msg.chat.id] = {"audio": audio}
    
    await msg.reply_text(
        "🔄 Send me the durations to remove from the audio file in this format: `HH:MM:SS - HH:MM:SS` (e.g., `00:01:30 - 00:02:00` to remove from 1m30s to 2m0s).",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="cancel_trim")]
        ])
    )

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def receive_durations(bot, msg):
    # Only process if user is in a valid /audio session
    if msg.chat.id not in user_inputs or "audio" not in user_inputs[msg.chat.id]:
        return  # Ignore unrelated messages

    try:
        duration_ranges = msg.text.split("-")
        start_time_str, end_time_str = duration_ranges[0].strip(), duration_ranges[1].strip()
        start_time = hhmmss_to_seconds(start_time_str)
        end_time = hhmmss_to_seconds(end_time_str)
        user_inputs[msg.chat.id]["durations"] = (start_time, end_time)

        await msg.reply_text(
            f"Durations received: `{start_time_str} - {end_time_str}`\nConfirm trimming?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Confirm", callback_data="confirm_trim"),
                 InlineKeyboardButton("Cancel", callback_data="cancel_trim")]
            ])
        )
    except Exception as e:
        await msg.reply_text("Invalid input. Please send durations in `HH:MM:SS - HH:MM:SS` format (e.g., `00:01:30 - 00:02:00`).")

@Client.on_callback_query(filters.regex("confirm_trim"))
async def confirm_trim(bot, query):
    data = user_inputs.get(query.message.chat.id, {})
    if not data:
        return await query.message.edit_text("Session expired. Please try again.")

    audio = data["audio"]
    start_time, end_time = data["durations"]
    user_inputs.pop(query.message.chat.id)  # Clear after use

    # Start downloading
    sts = await query.message.edit_text("🔄 Downloading audio...📥")
    c_time = time.time()
    downloaded = await bot.download_media(audio, progress=progress_message, progress_args=("Downloading...❤", sts, c_time))

    await sts.edit_text("📥 Download complete. Now trimming...🔧")

    # Trimming audio
    trimmed_audio = "trimmed_audio.mp3"
    audio_segment = AudioSegment.from_file(downloaded)
    trimmed_segment = audio_segment[:int(start_time * 1000)] + audio_segment[int(end_time * 1000):]
    trimmed_segment.export(trimmed_audio, format="mp3")  # Export trimmed audio

    # Upload trimmed audio
    await sts.edit_text("🚀 Uploading trimmed audio...📤")
    c_time = time.time()
    try:
        await bot.send_audio(query.message.chat.id, audio=trimmed_audio, caption="🎶 Trimmed Audio Uploaded!", progress=progress_message, progress_args=("Uploading...❤", sts, c_time))
    except Exception as e:
        return await sts.edit_text(f"Error: {e}")

    # Clean up
    os.remove(downloaded)
    os.remove(trimmed_audio)
    await sts.delete()

@Client.on_callback_query(filters.regex("cancel_trim"))
async def cancel_trim(bot, query):
    user_inputs.pop(query.message.chat.id, None)
    await query.message.edit_text("🚫 Trimming operation cancelled.")
