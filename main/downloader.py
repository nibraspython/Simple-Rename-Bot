import logging
import asyncio
import aiohttp
import os
import time
from datetime import datetime
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, CAPTION, TG_MAX_FILE_SIZE, CHUNK_SIZE, PROCESS_MAX_TIMEOUT, ADMIN
from main.utils import progress_message, humanbytes
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from PIL import Image
from moviepy.editor import VideoFileClip

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def youtube_url_handler(bot, message):
    await message.reply_text("📥 Please send your YouTube links to download.")

@Client.on_message(filters.private & filters.regex(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/.+') & filters.user(ADMIN))
async def youtube_download(bot, message):
    youtube_dl_url = message.text.strip()
    custom_file_name = os.path.basename(youtube_dl_url)
    description = CAPTION
    start = datetime.now()
    
    await message.reply_text("🔄 Initiating download...", parse_mode=enums.ParseMode.HTML)
    
    tmp_directory_for_each_user = os.path.join(DOWNLOAD_LOCATION, str(message.from_user.id))
    if not os.path.isdir(tmp_directory_for_each_user):
        os.makedirs(tmp_directory_for_each_user)
    download_directory = os.path.join(tmp_directory_for_each_user, custom_file_name)
    
    async with aiohttp.ClientSession() as session:
        c_time = time.time()
        try:
            await download_coroutine(bot, session, youtube_dl_url, download_directory, message.chat.id, message.id, c_time)
        except asyncio.TimeoutError:
            await bot.edit_message_text(chat_id=message.chat.id, message_id=message.id, text="⚠️ The download speed is too slow.", parse_mode=enums.ParseMode.HTML)
            return False

    if os.path.exists(download_directory):
        end_one = datetime.now()
        await message.reply_text("🚀 Uploading started...", parse_mode=enums.ParseMode.HTML)
        
        file_size = TG_MAX_FILE_SIZE + 1
        try:
            file_size = os.stat(download_directory).st_size
        except FileNotFoundError as exc:
            download_directory = os.path.splitext(download_directory)[0] + "." + "mkv"
            file_size = os.stat(download_directory).st_size
        
        if file_size > TG_MAX_FILE_SIZE:
            await message.reply_text("❌ The file size exceeds the Telegram limit.", parse_mode=enums.ParseMode.HTML)
        else:
            start_time = time.time()
            video_clip = VideoFileClip(download_directory)
            duration = int(video_clip.duration)
            video_clip.close()

            if description:
                try:
                    cap = description.format(file_name=custom_file_name, file_size=humanbytes(file_size), duration=duration)
                except Exception as e:
                    return await message.reply_text(f"❌ Your caption Error: unexpected keyword ●> ({e})")
            else:
                cap = f"{custom_file_name}\n\n💽 size: {humanbytes(file_size)}\n🕒 duration: {duration} seconds"

            thumbnail_path = await get_thumbnail(bot, message, download_directory)

            await bot.send_video(
                message.chat.id,
                video=download_directory,
                caption=cap,
                duration=duration,
                thumb=thumbnail_path,
                progress=progress_message,
                progress_args=("Upload Started..... Thanks To All Who Supported ❤", message, start_time)
            )

            end_two = datetime.now()
            try:
                os.remove(download_directory)
                os.remove(thumbnail_path)
            except:
                pass
            
            time_taken_for_download = (end_one - start).seconds
            time_taken_for_upload = (end_two - end_one).seconds
            await message.reply_text(f"✅ Successfully uploaded in {time_taken_for_upload} seconds.\n📥 Download time: {time_taken_for_download} seconds.", parse_mode=enums.ParseMode.HTML)
    else:
        await message.reply_text("❌ Invalid link: Incorrect Link", parse_mode=enums.ParseMode.HTML)

async def download_coroutine(bot, session, url, file_name, chat_id, message_id, start):
    downloaded = 0
    display_message = ""
    async with session.get(url, timeout=PROCESS_MAX_TIMEOUT) as response:
        total_length = int(response.headers["Content-Length"])
        content_type = response.headers["Content-Type"]
        if "text" in content_type and total_length < 500:
            return await response.release()
        await bot.edit_message_text(
            chat_id,
            message_id,
            text=f"""Initiating Download
🔗 **URL:** `{url}`
🗂️ **Size:** {humanbytes(total_length)}"""
        )
        with open(file_name, "wb") as f_handle:
            while True:
                chunk = await response.content.read(CHUNK_SIZE)
                if not chunk:
                    break
                f_handle.write(chunk)
                downloaded += CHUNK_SIZE
                now = time.time()
                diff = now - start
                if round(diff % 5.00) == 0 or downloaded == total_length:
                    percentage = downloaded * 100 / total_length
                    speed = downloaded / diff
                    elapsed_time = round(diff) * 1000
                    time_to_completion = round((total_length - downloaded) / speed) * 1000
                    estimated_total_time = elapsed_time + time_to_completion
                    try:
                        current_message = f"""**Download Status**
🔗 **URL:** `{url}`
🗂️ **Size:** {humanbytes(total_length)}
✅ **Done:** {humanbytes(downloaded)}
⏱️ **ETA:** {TimeFormatter(estimated_total_time)}"""
                        if current_message != display_message:
                            await bot.edit_message_text(chat_id, message_id, text=current_message)
                            display_message = current_message
                    except Exception as e:
                        logger.info(str(e))
                        pass
        return await response.release()

async def get_thumbnail(bot, message, download_directory):
    thumb_image_path = os.path.join(DOWNLOAD_LOCATION, f"{message.from_user.id}.jpg")
    if not os.path.exists(thumb_image_path):
        thumb_image_path = await bot.download_media(message.reply_to_message.video.thumbs[0].file_id)
    return thumb_image_path
