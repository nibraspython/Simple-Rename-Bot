import os
import time
import requests
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from urllib.parse import urlparse
from moviepy.editor import VideoFileClip
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Function to fetch file info from direct URL
def get_file_info(url):
    response = requests.head(url, allow_redirects=True)
    file_size = int(response.headers.get('content-length', 0))
    file_name = os.path.basename(urlparse(url).path)
    if not file_name:
        file_name = "Unknown_File"
    return file_name, file_size

# Function to download file from direct URL
def download_file(url, file_name):
    file_path = os.path.join(DOWNLOAD_LOCATION, file_name)
    with requests.get(url, stream=True) as r:
        with open(file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return file_path

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
        # Forward to the Dailymotion download script
        await query.message.edit("Running Dailymotion script...")
        # Call your Dailymotion script here as needed
        
# Handle Confirm or Cancel
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

# Utility function to extract filename from URL if no filename is present
def extract_file_name(url):
    parsed_url = urlparse(url)
    file_name = os.path.basename(parsed_url.path)
    if not file_name:
        file_name = "unknown_file"
    return file_name

