import time, os, hashlib
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from yt_dlp import YoutubeDL
import requests
from moviepy.editor import VideoFileClip
from urllib.parse import urlparse
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Function to get file name from the URL or response headers
def get_file_name(url, response):
    if 'Content-Disposition' in response.headers:
        cd = response.headers['Content-Disposition']
        fname = cd.split('filename=')[-1].strip('\"')
        if fname:
            return fname
    path = urlparse(url).path
    fname = os.path.basename(path)
    if fname:
        return fname
    return "unknown_file"

# Function to download direct link
def download_direct_link(url):
    response = requests.head(url, allow_redirects=True)
    if response.status_code == 200:
        file_name = get_file_name(url, response)
        file_size = int(response.headers.get('content-length', 0))
        file_size_human = humanbytes(file_size)
        return file_name, file_size, file_size_human
    return None, None, None

# Generate a unique hash for each file to use as callback data
def generate_unique_id(url):
    return hashlib.md5(url.encode()).hexdigest()

@Client.on_message(filters.private & filters.command("dailydl") & filters.user(ADMIN))
async def dailymotion_download(bot, msg):
    reply = msg.reply_to_message
    if not reply or not reply.text:
        return await msg.reply_text("Please reply to a message containing one or more URLs.")

    urls = reply.text.split()  # Split the message to extract multiple URLs
    if not urls:
        return await msg.reply_text("Please provide valid URLs.")

    for url in urls:
        try:
            sts = await msg.reply_text(f"🔄 Processing your request for {url}...")

            if "dailymotion.com" not in url:
                file_name, file_size, file_size_human = download_direct_link(url)
                if not file_name:
                    return await sts.edit(f"❌ Failed to get file info for {url}.")
                
                unique_id = generate_unique_id(url)  # Generate a short unique identifier

                confirm_buttons = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{unique_id}")],
                    [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{unique_id}")]
                ])

                await sts.edit(
                    f"📄 **File Name:** {file_name}\n💽 **Size:** {file_size_human}\n\nDo you want to proceed?",
                    reply_markup=confirm_buttons
                )

                @Client.on_callback_query(filters.regex(f"confirm_{unique_id}"))
                async def on_confirm(client, callback_query):
                    await callback_query.answer()
                    await callback_query.message.delete()

                    # Start downloading
                    c_time = time.time()
                    await sts.edit(f"📥 Downloading: {file_name}...\n💽 Size: {file_size_human}")
                    download_path = f"{DOWNLOAD_LOCATION}/{file_name}"
                    
                    with requests.get(url, stream=True) as r:
                        r.raise_for_status()
                        with open(download_path, 'wb') as f:
                            total_length = int(r.headers.get('content-length', 0))
                            dl = 0
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    dl += len(chunk)
                                    done = int(50 * dl / total_length)
                                    # Update progress
                                    await progress_message(f"📥 Downloading {file_name}...", sts, c_time, dl, total_length)

                    await sts.edit("✅ Download Completed! 📥")

                    await sts.edit(f"🚀 Uploading: {file_name} 📤")
                    c_time = time.time()

                    await bot.send_document(
                        msg.chat.id,
                        document=download_path,
                        caption=f"📄 **{file_name}**",
                        progress=progress_message,
                        progress_args=(f"🚀 Uploading {file_name}... 📤", sts, c_time),
                    )

                    os.remove(download_path)

                    await sts.edit(f"✅ Successfully uploaded: {file_name}")

                @Client.on_callback_query(filters.regex(f"cancel_{unique_id}"))
                async def on_cancel(client, callback_query):
                    await callback_query.answer()
                    await callback_query.message.delete()
                    await sts.edit("❌ Download cancelled.")
            
            else:
                downloaded, video_title, duration, file_size, resolution, thumbnail_url = download_dailymotion(url)
                human_size = humanbytes(file_size)

                await sts.edit(f"📥 Downloading: {video_title}\nResolution: {resolution}p\n💽 Size: {human_size}")

                thumbnail_path = download_thumbnail(thumbnail_url, video_title)
                if not thumbnail_path:
                    thumbnail_path = generate_thumbnail(downloaded)

                await sts.edit("✅ Download Completed! 📥")
                
                cap = f"🎬 **{video_title}**\n💽 Size: {human_size}\n🕒 Duration: {duration // 60} mins {duration % 60} secs\n📹 Resolution: {resolution}p"

                await sts.edit(f"🚀 Uploading: {video_title} 📤")
                c_time = time.time()

                await bot.send_video(
                    msg.chat.id,
                    video=downloaded,
                    thumb=thumbnail_path if thumbnail_path else None,
                    caption=cap,
                    duration=duration,
                    progress=progress_message,
                    progress_args=(f"🚀 Uploading {video_title}... 📤", sts, c_time),
                )

                os.remove(downloaded)
                if thumbnail_path:
                    os.remove(thumbnail_path)

                await sts.edit(f"✅ Successfully uploaded: {video_title}")

        except Exception as e:
            await msg.reply_text(f"❌ Failed to process {url}. Error: {str(e)}")

    await msg.reply_text("🎉 All URLs processed successfully!")
