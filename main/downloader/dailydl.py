import time, os
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from yt_dlp import YoutubeDL
import requests
from moviepy.editor import VideoFileClip
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Dailymotion Download Function with Resolution and Thumbnail URL
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
        resolution = info.get('height')  # Get video resolution height
        thumbnail_url = info.get('thumbnail')  # Get the thumbnail URL from the info
        return file_path, video_title, duration, file_size, resolution, thumbnail_url

# Function to generate thumbnail from the video if no thumbnail is available
def generate_thumbnail(video_path):
    thumbnail_path = f"{video_path}_thumbnail.jpg"
    try:
        video_clip = VideoFileClip(video_path)
        video_clip.save_frame(thumbnail_path, t=video_clip.duration / 2)  # Capture thumbnail at the middle of the video
        video_clip.close()
        return thumbnail_path
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None

# Function to download the thumbnail if available
def download_thumbnail(thumbnail_url, title):
    if not thumbnail_url:
        return None
    thumbnail_path = f"{DOWNLOAD_LOCATION}/{title}_thumbnail.jpg"
    response = requests.get(thumbnail_url)
    if response.status_code == 200:
        with open(thumbnail_path, 'wb') as f:
            f.write(response.content)
        return thumbnail_path
    return None

# Direct URL handling
@Client.on_message(filters.private & filters.command("dailydl") & filters.user(ADMIN))
async def handle_download(bot, msg):
    reply = msg.reply_to_message
    if not reply or not reply.text:
        return await msg.reply_text("Please reply to a message containing a Dailymotion or Direct Download URL.")
    
    urls = reply.text.split()
    if not urls:
        return await msg.reply_text("Please provide valid URLs.")
    
    # Iterate over each URL
    for url in urls:
        sts = await msg.reply_text(f"🔄 Processing your request for {url}...")
        
        # Show buttons for Dailymotion or Direct URL
        buttons = [
            [InlineKeyboardButton("Dailymotion", callback_data=f"dmotion_{url}")],
            [InlineKeyboardButton("Direct URL", callback_data=f"direct_{url}")]
        ]
        await sts.edit("Choose an option:", reply_markup=InlineKeyboardMarkup(buttons))

# Callback query handler
@Client.on_callback_query(filters.regex(r"(direct|dmotion)"))
async def callback_handler(bot, query):
    url = query.data.split("_")[1]
    
    if query.data.startswith("direct"):
        # Handle direct download URL
        file_name, file_size = get_file_info(url)
        human_size = humanbytes(file_size)
        
        buttons = [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{url}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ]
        await query.message.edit(f"File: {file_name}\n💽 Size: {human_size}", reply_markup=InlineKeyboardMarkup(buttons))
    
    elif query.data.startswith("dmotion"):
        # Handle Dailymotion download
        await query.message.edit(f"📥 Downloading Dailymotion video from {url}...")
        try:
            c_time = time.time()
            downloaded, video_title, duration, file_size, resolution, thumbnail_url = download_dailymotion(url)
            human_size = humanbytes(file_size)
            
            await query.message.edit(f"📥 Downloading: {video_title}\nResolution: {resolution}p\n💽 Size: {human_size}")

            # Generate or download thumbnail
            thumbnail_path = download_thumbnail(thumbnail_url, video_title)
            if not thumbnail_path:
                thumbnail_path = generate_thumbnail(downloaded)

            # Download complete
            await query.message.edit("✅ Download Completed! 📥")
            
            # Prepare caption
            cap = f"🎬 **{video_title}**\n\n💽 Size: {human_size}\n🕒 Duration: {duration // 60} mins {duration % 60} secs\n📹 Resolution: {resolution}p"
            
            # Start uploading
            await query.message.edit(f"🚀 Uploading: {video_title} 📤")
            c_time = time.time()
            
            await bot.send_video(
                query.message.chat.id,
                video=downloaded,
                thumb=thumbnail_path if thumbnail_path else None,
                caption=cap,
                duration=duration,
                progress=progress_message,
                progress_args=(f"🚀 Uploading {video_title}... 📤", query.message, c_time),
            )
            
            # Clean up
            os.remove(downloaded)
            if thumbnail_path:
                os.remove(thumbnail_path)

            await query.message.edit(f"✅ Successfully uploaded: {video_title}")

        except Exception as e:
            await query.message.edit(f"❌ Failed to process {url}. Error: {str(e)}")

# Handle Confirm or Cancel for Direct URL
@Client.on_callback_query(filters.regex(r"(confirm|cancel)"))
async def confirm_cancel_handler(bot, query):
    if query.data.startswith("confirm"):
        url = query.data.split("_")[1]
        file_name, file_size = get_file_info(url)
        
        # Start downloading
        sts = await query.message.edit(f"📥 Downloading {file_name}...")
        c_time = time.time()
        downloaded_file = download_file(url, file_name)
        
        # Download completed message
        await sts.edit("✅ Download Completed!")
        
        # Start Uploading
        await sts.edit(f"🚀 Uploading {file_name}...")
        await bot.send_document(
            query.message.chat.id,
            document=downloaded_file,
            caption=f"📁 **{file_name}**",
            progress=progress_message,
            progress_args=(f"🚀 Uploading {file_name}...", sts, c_time),
        )
        
        # Clean up
        os.remove(downloaded_file)
        await sts.edit(f"✅ Successfully uploaded: {file_name}")
        
    elif query.data == "cancel":
        await query.message.edit("❌ Operation cancelled.")
