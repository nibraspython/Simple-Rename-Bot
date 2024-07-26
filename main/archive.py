import time
import os
import zipfile
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes

class ZipManager:
    def __init__(self):
        self.chat_data = {}

    def start_zip_process(self, chat_id):
        self.chat_data[chat_id] = {"files": [], "waiting_for_name": False, "active": True}

    def add_file(self, chat_id, file):
        if chat_id not in self.chat_data:
            self.start_zip_process(chat_id)
        self.chat_data[chat_id]["files"].append(file)

    def get_files(self, chat_id):
        return self.chat_data.get(chat_id, {}).get("files", [])

    def clear_files(self, chat_id):
        if chat_id in self.chat_data:
            self.chat_data[chat_id]["files"] = []

    def set_waiting_for_name(self, chat_id, state):
        if chat_id not in self.chat_data:
            self.start_zip_process(chat_id)
        self.chat_data[chat_id]["waiting_for_name"] = state

    def is_waiting_for_name(self, chat_id):
        return self.chat_data.get(chat_id, {}).get("waiting_for_name", False)
    
    def is_active(self, chat_id):
        return self.chat_data.get(chat_id, {}).get("active", False)

    def deactivate(self, chat_id):
        if chat_id in self.chat_data:
            self.chat_data[chat_id]["active"] = False

zip_manager = ZipManager()

@Client.on_message(filters.private & filters.command("archive") & filters.user(ADMIN))
async def start_zip_process(bot, msg):
    chat_id = msg.chat.id
    zip_manager.start_zip_process(chat_id)
    await msg.reply_text("📦 Send your files to add to the zip file.\n\nUse /done when finished or /cancel to abort.")

@Client.on_message(filters.private & filters.user(ADMIN) & ~filters.command(["archive", "done", "cancel"]))
async def add_file_to_zip(bot, msg):
    chat_id = msg.chat.id
    if not zip_manager.is_active(chat_id):
        return  # Ignore messages if zipping process is not active
    
    media = msg.document or msg.audio or msg.video
    if not media:
        return await msg.reply_text("Please send a valid file.")
    
    zip_manager.add_file(chat_id, media)
    files = zip_manager.get_files(chat_id)
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
        zip_manager.clear_files(chat_id)
        zip_manager.deactivate(chat_id)
        await query.message.edit_text("❌ Zipping process canceled.")
        return
    
    if query.message.text != "📛 Send your custom name without extension for the zip file.":
        await query.message.edit_text("📛 Send your custom name without extension for the zip file.")
    zip_manager.set_waiting_for_name(chat_id, True)

@Client.on_message(filters.private & filters.user(ADMIN))
async def handle_custom_name(bot, msg):
    chat_id = msg.chat.id
    if not zip_manager.is_active(chat_id):
        return  # Ignore messages if zipping process is not active
    
    if zip_manager.is_waiting_for_name(chat_id):
        custom_name = msg.text.strip()
        if not custom_name:
            return await msg.reply_text("Please provide a valid name for the zip file.")
        
        files = zip_manager.get_files(chat_id)
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
        
        zip_manager.clear_files(chat_id)
        zip_manager.set_waiting_for_name(chat_id, False)
        zip_manager.deactivate(chat_id)
        await sts.delete()
