import time
import os
import zipfile
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message

@Client.on_message(filters.private & filters.command("zip") & filters.user(ADMIN))
async def zip_files(bot, msg):
    reply = msg.reply_to_message
    if not reply:
        return await msg.reply_text("📦 Please reply to a file to include it in the zip.")
    
    # Initialize variables
    files_to_zip = []
    count = 0
    file_names = []
    message = await msg.reply_text("🔍 Starting zipping process...")
    
    # Function to update the message with file count
    async def update_message():
        nonlocal count
        count += 1
        await message.edit_text(f"🔍 Zipping {count}/{len(files_to_zip)} files...")
    
    # Function to zip files
    async def zip_and_upload(file_names, zip_name):
        await message.edit_text("📦 Zipping files...")
        zip_path = f"{DOWNLOAD_LOCATION}/{zip_name}.zip"
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for file in files_to_zip:
                zipf.write(file, os.path.basename(file))
        await message.edit_text("📤 Uploading zip file...")
        await bot.send_document(msg.chat.id, zip_path, caption="🎉 Zip file ready!")
        os.remove(zip_path)
        await message.delete()
    
    # Process the files
    media = reply.document or reply.audio or reply.video
    if media:
        file_name = f"{DOWNLOAD_LOCATION}/{media.file_name}"
        await media.download(file_name, progress=progress_message, progress_args=("📥 Downloading file...", message, time.time()))
        files_to_zip.append(file_name)
        file_names.append(media.file_name)
        await update_message()
    
    # Check if more files are being sent
    async for msg in bot.iter_history(msg.chat.id, offset_id=reply.message_id, reverse=True):
        if msg.media:
            file_name = f"{DOWNLOAD_LOCATION}/{msg.media.file_name}"
            await msg.download(file_name, progress=progress_message, progress_args=("📥 Downloading file...", message, time.time()))
            files_to_zip.append(file_name)
            file_names.append(msg.media.file_name)
            await update_message()
    
    # Check if any files found
    if not files_to_zip:
        await message.edit_text("🚫 No files found to zip.")
        return
    
    # Ask for zip file name
    await message.edit_text("✏️ All files sent. Please send the name for the zip file.")
    zip_name_msg = await bot.listen(msg.chat.id)
    zip_name = zip_name_msg.text.strip()
    
    # Zip and upload
    await zip_and_upload(files_to_zip, zip_name)

    # Clean up downloaded files
    for file in files_to_zip:
        os.remove(file)
