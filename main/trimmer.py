import time
import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

# Temporary storage for media and trimming durations
trim_data = {}

@Client.on_message(filters.private & filters.command("trim") & filters.user(ADMIN))
async def start_trim_process(bot, msg):
    chat_id = msg.chat.id
    trim_data[chat_id] = {}
    await msg.reply_text("🔄 **Please send the video or document you want to trim.**")

@Client.on_message(filters.private & filters.media & filters.user(ADMIN))
async def receive_media(bot, msg):
    chat_id = msg.chat.id
    if chat_id in trim_data and 'media' not in trim_data[chat_id]:
        media = msg.video or msg.document
        if media:
            trim_data[chat_id]['media'] = media
            await msg.reply_text("🕒 **Media received. Please send the trimming durations in the format:** `HH:MM:SS HH:MM:SS` (start_time end_time)")

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def receive_durations(bot, msg):
    chat_id = msg.chat.id
    if chat_id in trim_data and 'media' in trim_data[chat_id] and 'start_time' not in trim_data[chat_id]:
        durations = msg.text.strip().split()
        if len(durations) == 2:
            start_time_str, end_time_str = durations
            try:
                # Convert time strings to seconds
                start_time = sum(int(x) * 60 ** i for i, x in enumerate(reversed(start_time_str.split(":"))))
                end_time = sum(int(x) * 60 ** i for i, x in enumerate(reversed(end_time_str.split(":"))))
                
                trim_data[chat_id]['start_time'] = start_time
                trim_data[chat_id]['end_time'] = end_time

                await msg.reply_text(
                    f"🕒 **Trimming durations received:**\nStart: `{start_time_str}`\nEnd: `{end_time_str}`",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Confirm ✔️", callback_data="trim_confirm")],
                        [InlineKeyboardButton("Cancel 🚫", callback_data="trim_cancel")]
                    ])
                )
            except ValueError:
                await msg.reply_text("❌ **Invalid time format. Please use:** `HH:MM:SS HH:MM:SS`")
        else:
            await msg.reply_text("❌ **Please provide both start and end times in the format:** `HH:MM:SS HH:MM:SS`")

@Client.on_callback_query(filters.regex("trim_confirm") & filters.user(ADMIN))
async def trim_confirm_callback(bot, query):
    chat_id = query.message.chat.id
    if chat_id in trim_data and 'media' in trim_data[chat_id]:
        media = trim_data[chat_id]['media']
        start_time = trim_data[chat_id]['start_time']
        end_time = trim_data[chat_id]['end_time']

        sts = await query.message.reply_text("🔄 **Downloading...** 📥")
        c_time = time.time()
        downloaded = await bot.download_media(
            media,
            progress=progress_message,
            progress_args=("📥 **Download Started...**", sts, c_time)
        )
        
        # Extracting thumbnail from the original video
        thumbnail = f"{os.path.splitext(downloaded)[0]}_thumbnail.jpg"
        await bot.download_media(media.thumbs[0].file_id, file_name=thumbnail) if media.thumbs else None

        # Get the original frame rate using ffprobe
        frame_rate_probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'default=noprint_wrappers=1:nokey=1', downloaded],
            capture_output=True, text=True
        )
        original_fps = frame_rate_probe.stdout.strip()
        if '/' in original_fps:
            num, denom = map(int, original_fps.split('/'))
            frame_rate = num / denom
        else:
            frame_rate = float(original_fps)

        output_video = f"{os.path.splitext(downloaded)[0]}_trimmed.mp4"

        try:
            # Improved trimming command with frame rate preservation
            command = [
                'ffmpeg', '-ss', str(start_time), '-i', downloaded,
                '-to', str(end_time), '-r', str(int(round(frame_rate))),  # Set original frame rate
                '-c:v', 'libx264', '-c:a', 'aac',  # Re-encode with H.264 and AAC
                '-strict', 'experimental',
                output_video
            ]
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            return await sts.edit(f"❌ **Error during trimming:** `{e}`")

        video_clip = VideoFileClip(output_video)
        duration = int(video_clip.duration)
        video_clip.close()

        filesize = humanbytes(os.path.getsize(output_video))
        cap = f"🎬 **Trimmed Video**\n\n💽 **Size:** `{filesize}`\n🕒 **Duration:** `{duration} seconds`"

        await sts.edit("🚀 **Uploading started...📤**")
        c_time = time.time()
        try:
            await bot.send_video(
                chat_id, video=output_video, caption=cap,
                duration=duration, thumb=thumbnail if os.path.exists(thumbnail) else None, progress=progress_message,
                progress_args=(f"🚀 **Upload Started...📤**\n**Thanks To K-MAC For His Trimming Code❤ 🧑‍💻**", sts, c_time)
            )
        except Exception as e:
            return await sts.edit(f"❌ **Error:** `{e}`")

        # Cleanup
        try:
            os.remove(downloaded)
            os.remove(output_video)
            if os.path.exists(thumbnail):
                os.remove(thumbnail)
        except:
            pass

        await sts.delete()
        del trim_data[chat_id]

@Client.on_callback_query(filters.regex("trim_cancel") & filters.user(ADMIN))
async def trim_cancel_callback(bot, query):
    chat_id = query.message.chat.id
    if chat_id in trim_data:
        del trim_data[chat_id]
    await query.message.reply_text("❌ **Trimming canceled.**")
    await query.message.delete()
