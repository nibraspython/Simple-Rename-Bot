import time, os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from yt_dlp import YoutubeDL
import requests
from requests.exceptions import ChunkedEncodingError, ConnectionError, Timeout

# Retry logic for direct file downloads
def download_with_retry(url, download_path, max_retries=5, chunk_size=8192):
    attempt = 0
    while attempt < max_retries:
        try:
            with requests.get(url, stream=True, timeout=10) as r:
                r.raise_for_status()  # Check if the request is successful
                total_size = int(r.headers.get('content-length', 0))
                with open(download_path, 'wb') as f:
                    downloaded_size = 0
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:  # filter out keep-alive chunks
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            print(f"Downloading: {downloaded_size}/{total_size} bytes")
            return download_path
        except (ChunkedEncodingError, ConnectionError, Timeout) as e:
            attempt += 1
            print(f"Download failed (Attempt {attempt}/{max_retries}): {e}")
            if attempt >= max_retries:
                raise Exception(f"Download failed after {max_retries} attempts.")
            time.sleep(2)  # Add delay before retrying
    return None

# Dailymotion Download Function using yt-dlp
def download_dailymotion(url):
    ydl_opts = {
        'format': 'best',  # download the best quality
        'outtmpl': f'{DOWNLOAD_LOCATION}/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        video_title = info.get('title')
        duration = info.get('duration', 0)
        file_size = info.get('filesize', 0)
        resolution = info.get('height')
        thumbnail_url = info.get('thumbnail')
        return file_path, video_title, duration, file_size, resolution, thumbnail_url

# Function to handle download confirmations via inline keyboard buttons
async def handle_confirmation(client, callback_query):
    callback_data = callback_query.data
    msg = callback_query.message
    url = callback_query.message.reply_to_message.text

    if callback_data == "confirm":
        # Proceed with the download
        await msg.edit_text("📥 Downloading...")
        try:
            file_name = url.split('/')[-1] or "unknown_file"
            download_path = os.path.join(DOWNLOAD_LOCATION, file_name)

            # Download the file using retry logic
            downloaded_path = download_with_retry(url, download_path)

            await msg.edit_text(f"🚀 Uploading: {file_name} 📤")
            await client.send_document(
                chat_id=msg.chat.id,
                document=downloaded_path,
                caption=f"📄 {file_name}",
                progress=progress_message,
                progress_args=(f"🚀 Uploading {file_name}...", msg, time.time())
            )

            # Clean up the file after upload
            os.remove(downloaded_path)

            await msg.edit_text(f"✅ Successfully uploaded: {file_name}")
        except Exception as e:
            await msg.edit_text(f"❌ Failed to download. Error: {str(e)}")
    elif callback_data == "cancel":
        # Cancel the download
        await msg.edit_text("❌ Download cancelled.")

@Client.on_message(filters.private & filters.command("dailydl") & filters.user(ADMIN))
async def dailymotion_download(bot, msg):
    reply = msg.reply_to_message
    if not reply or not reply.text:
        return await msg.reply_text("Please reply to a message containing one or more URLs.")
    
    urls = reply.text.split()  # Split message to get multiple URLs
    if not urls:
        return await msg.reply_text("Please provide valid URLs.")

    for url in urls:
        try:
            sts = await msg.reply_text(f"🔄 Processing request for {url}...")

            # Check if the URL is a direct file link or a Dailymotion link
            if "dailymotion.com" in url:
                downloaded, video_title, duration, file_size, resolution, thumbnail_url = download_dailymotion(url)
                file_size_human = humanbytes(file_size)
                
                # Notify about download start
                await sts.edit(f"📥 Downloading: {video_title}\nResolution: {resolution}p\n💽 Size: {file_size_human}")
                # Upload to Telegram after download
                await bot.send_video(
                    chat_id=msg.chat.id,
                    video=downloaded,
                    caption=f"🎬 {video_title}\nResolution: {resolution}p\nDuration: {duration // 60} mins {duration % 60} secs",
                    progress=progress_message,
                    progress_args=(f"🚀 Uploading {video_title}...", sts, time.time()),
                )

                # Remove downloaded files
                os.remove(downloaded)
            else:
                # For direct download links
                file_name = url.split('/')[-1] or "unknown_file"
                download_path = os.path.join(DOWNLOAD_LOCATION, file_name)

                # Prepare the inline keyboard for confirmation
                confirm_keyboard = InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
                        InlineKeyboardButton("❌ Cancel", callback_data="cancel")
                    ]]
                )

                # Show file name and ask for confirmation
                await sts.edit(f"🔄 Processing: {file_name}\n💽 Size: (Fetching...)", reply_markup=confirm_keyboard)

        except Exception as e:
            await msg.reply_text(f"❌ Failed to process {url}. Error: {str(e)}")

    await msg.reply_text("🎉 All URLs processed successfully!")

@Client.on_callback_query()
async def on_callback_query(client, callback_query):
    await handle_confirmation(client, callback_query)
