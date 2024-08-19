import os
import time
import zipfile
from pyrogram import Client
from config import DOWNLOAD_LOCATION
from main.utils import progress_message, humanbytes

async def handle_archive_creation(bot: Client, msg, user_data, custom_name):
    user_id = msg.from_user.id

    if user_id not in user_data:
        await msg.reply_text("No files found to create an archive.")
        return

    # Create the directory for the downloaded files if it doesn't exist
    download_dir = os.path.join(DOWNLOAD_LOCATION, f"{custom_name}_temp")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    media_files = []
    for file_info in user_data[user_id]['files']:
        media = file_info['message']
        file_name = file_info['file_name']
        file_path = os.path.join(download_dir, file_name)

        # Download each file
        sts = await msg.reply_text(f"🔄 Downloading {file_name}.....📥")
        c_time = time.time()
        downloaded = await media.download(file_name=file_path, progress=progress_message, progress_args=(f"Download Started: {file_name}..... Thanks To All Who Supported ❤", sts, c_time))
        media_files.append(downloaded)

    # Create a ZIP file
    zip_file_path = os.path.join(DOWNLOAD_LOCATION, f"{custom_name}.zip")
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for file_path in media_files:
            zipf.write(file_path, os.path.basename(file_path))

    # Clean up downloaded files
    for file_path in media_files:
        os.remove(file_path)
    os.rmdir(download_dir)

    # Upload the ZIP file
    filesize = humanbytes(os.path.getsize(zip_file_path))
    await sts.edit("🚀 Uploading started..... 📤Thanks To All Who Supported ❤")
    c_time = time.time()
    try:
        await bot.send_document(msg.chat.id, document=zip_file_path, caption=f"{custom_name}.zip\n\n💽 size: {filesize}", progress=progress_message, progress_args=(f"Upload Started: {custom_name}.zip..... Thanks To All Who Supported ❤", sts, c_time))
    except Exception as e:
        await msg.reply_text(f"Error: {e}")
    finally:
        os.remove(zip_file_path)  # Remove the ZIP file after uploading
