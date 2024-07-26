import time
import os
import zipfile
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes

@Client.on_message(filters.private & filters.command("archive") & filters.user(ADMIN))
async def start_zip_process(bot, msg):
    print(f"Received /archive command from {msg.from_user.id}")
    await msg.reply_text("📦 Send your files to add to the zip file.\n\nUse /done when finished or /cancel to abort.")

@Client.on_message(filters.private & filters.user(ADMIN) & ~filters.command(["archive", "done", "cancel"]))
async def add_file_to_zip(bot, msg):
    chat_id = msg.chat.id
    media = msg.document or msg.audio or msg.video
    if not media:
        return await msg.reply_text("Please send a valid file.")
    
    # Retrieve and update chat data
    files = bot.get_chat_data(chat_id).get("files", [])
    files.append(media)
    bot.set_chat_data(chat_id, {"files": files})
    
    # Create a response with the current file list
    file_names = "\n".join([file.file_name for file in files])
    file_count = len(files)
    await msg.reply_text(f"📄 Files added: {file_count}\n{file_names}",
                         reply_markup=InlineKeyboardMarkup([
                             [InlineKeyboardButton("✅ Done", callback_data="done")],
                             [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
                         ]))

@Client.on_callback_query(filters.regex(r"done|cancel"))
async def handle_done_cancel(bot, query):
    chat_id = query.message.chat.id
    if query.data == "cancel":
        bot.set_chat_data(chat_id, {"files": []})
        await query.message.edit_text("❌ Zipping process canceled.")
        return
    
    await query.message.edit_text("📛 Send your custom name without extension for the zip file.")
    bot.set_chat_data(chat_id, {"waiting_for_name": True})

@Client.on_message(filters.private & filters.user(ADMIN))
async def handle_custom_name(bot, msg):
    chat_id = msg.chat.id
    if bot.get_chat_data(chat_id).get("waiting_for_name"):
        custom_name = msg.text.strip()
        if not custom_name:
            return await msg.reply_text("Please provide a valid name for the zip file.")
        
        files = bot.get_chat_data(chat_id).get("files", [])
        if not files:
            return await msg.reply_text("No files to zip.")
        
        zip_path = os.path.join(DOWNLOAD_LOCATION, f"{custom_name}.zip")
        sts = await msg.reply_text("🔄 Downloading files...")
        
        # Download files
        c_time = time.time()
        downloaded_files = []
        for file in files:
            downloaded = await bot.download_media(file, progress=progress_message,
                                                  progress_args=("Downloading...", sts, c_time))
            downloaded_files.append(downloaded)
        
        # Create zip file
        sts = await sts.edit("🔄 Creating zip file...")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in downloaded_files:
                zipf.write(file_path, os.path.basename(file_path))
        
        # Upload zip file
        c_time = time.time()
        await bot.send_document(chat_id, zip_path, caption=f"🎉 Here is your zip file: {custom_name}.zip",
                                progress=progress_message, progress_args=("Uploading...", sts, c_time))
        
        # Cleanup
        for file_path in downloaded_files:
            os.remove(file_path)
        os.remove(zip_path)
        bot.set_chat_data(chat_id, {"files": [], "waiting_for_name": False})
        await sts.delete()
