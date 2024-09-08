import time
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

# Temporary storage for media and conversion details
convert_data = {}

@Client.on_message(filters.private & filters.command("convert") & filters.user(ADMIN))
async def start_conversion_process(bot, msg):
    chat_id = msg.chat.id
    convert_data[chat_id] = {}
    await msg.reply_text("🔄 **Please send the video or document you want to convert.**")

@Client.on_message(filters.private & filters.media & filters.user(ADMIN))
async def receive_media(bot, msg):
    chat_id = msg.chat.id
    if chat_id in convert_data and 'media' not in convert_data[chat_id]:
        media = msg.video or msg.document
        if media:
            convert_data[chat_id]['media'] = media
            file_name = media.file_name
            await msg.reply_text(f"📂 **Media received:** `{file_name}`\n\n**🔧 Please choose the resolution you want to convert to:**\n\n720p / 480p")

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def receive_resolution(bot, msg):
    chat_id = msg.chat.id
    if chat_id in convert_data and 'media' in convert_data[chat_id] and 'resolution' not in convert_data[chat_id]:
        resolution = msg.text.strip().lower()
        if resolution in ['720p', '480p']:
            convert_data[chat_id]['resolution'] = resolution

            await msg.reply_text(
                f"🆙 **Resolution selected:** `{resolution}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Confirm ✔️", callback_data="convert_confirm")],
                    [InlineKeyboardButton("Cancel 🚫", callback_data="convert_cancel")]
                ])
            )
        else:
            await msg.reply_text("❌ **Invalid resolution. Please select either:** `720p` or `480p`")

@Client.on_callback_query(filters.regex("convert_confirm") & filters.user(ADMIN))
async def convert_confirm_callback(bot, query):
    chat_id = query.message.chat.id
    if chat_id in convert_data and 'media' in convert_data[chat_id]:
        media = convert_data[chat_id]['media']
        resolution = convert_data[chat_id]['resolution']
        file_name = media.file_name

        sts = await query.message.reply_text("🔄 **Downloading...** 📥")
        c_time = time.time()
        downloaded = await bot.download_media(
            media,
            progress=progress_message,
            progress_args=("📥 **Download Started...**", sts, c_time)
        )

        output_video = f"/content/Simple-Rename-Bot/{os.path.splitext(os.path.basename(downloaded))[0]}_{resolution}.mp4"

        try:
            # Determine the resolution parameters
            resolution_map = {'720p': '1280x720', '480p': '854x480'}
            resolution_str = resolution_map[resolution]

            # Use ffmpeg for conversion
            ffmpeg_command = f"ffmpeg -i '{downloaded}' -vf scale={resolution_str} '{output_video}'"
            os.system(ffmpeg_command)
        except Exception as e:
            return await sts.edit(f"❌ **Error during conversion:** `{e}`")

        video_clip = VideoFileClip(output_video)
        duration = int(video_clip.duration)
        video_clip.close()

        filesize = humanbytes(os.path.getsize(output_video))
        cap = (f"🎬 **Converted Video**\n\n💽 **Size:** `{filesize}`\n"
               f"🕒 **Duration:** `{duration} seconds`\n"
               f"🔧 **Resolution:** `{resolution}`")

        await sts.edit(f"🚀 **Uploading started...📤**")
        c_time = time.time()
        try:
            await bot.send_video(
                chat_id, video=output_video, caption=cap,
                duration=duration, progress=progress_message,
                progress_args=(f"🚀 **Upload Started...📤**\n**Thanks For Using The Converter Bot!**\n\n**{os.path.basename(output_video)}**", sts, c_time)
            )
        except Exception as e:
            return await sts.edit(f"❌ **Error:** `{e}`")

        # Cleanup
        try:
            os.remove(downloaded)
            os.remove(output_video)
        except:
            pass

        await sts.delete()
        del convert_data[chat_id]

@Client.on_callback_query(filters.regex("convert_cancel") & filters.user(ADMIN))
async def convert_cancel_callback(bot, query):
    chat_id = query.message.chat.id
    if chat_id in convert_data:
        del convert_data[chat_id]
    await query.message.reply_text("❌ **Conversion canceled.**")
    await query.message.delete()
