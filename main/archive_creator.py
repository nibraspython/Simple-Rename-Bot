import os
import time
import zipfile
from config import DOWNLOAD_LOCATION
from main.utils import progress_message

async def handle_archive_creation(bot, msg, user_data, custom_name):
    user_id = msg.from_user.id
    files_to_zip = []
    
    download_message = await msg.reply_text(f"📦 **Creating archive `{custom_name}.zip`**...\n\n⬇️ Downloading files... Please wait.")
    
    for media in user_data[user_id]['files']:
        c_time = time.time()
        downloaded = await media.download(
            progress=progress_message, 
            progress_args=("⬇️ Download Started... Thanks To All Who Supported ❤", download_message, c_time)
        )
        files_to_zip.append(downloaded)
    
    await download_message.edit_text("✅ **Download completed.**\n\n📦 **Creating ZIP file...**")
    
    zip_path = create_zip_archive(custom_name, files_to_zip)
    
    upload_message = await download_message.edit_text("🚀 **Uploading ZIP file...**")
    c_time = time.time()
    await bot.send_document(
        chat_id=msg.chat.id,
        document=zip_path,
        caption=f"{custom_name}.zip",
        progress=progress_message,
        progress_args=("📤 Upload Started... Thanks To All Who Supported ❤", upload_message, c_time)
    )
    
    await upload_message.edit_text("✅ **Upload completed!**")
    
    # Cleanup
    for file_path in files_to_zip:
        os.remove(file_path)
    if os.path.exists(zip_path):
        os.remove(zip_path)

def create_zip_archive(zip_name, files):
    zip_path = os.path.join(DOWNLOAD_LOCATION, f"{zip_name}.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))
    return zip_path
