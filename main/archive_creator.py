import time
import os
import zipfile
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes

# Global variable to store files and user data
user_files = {}

@Client.on_message(filters.private & filters.command("archive") & filters.user(ADMIN))
async def start_archive(bot, msg):
    chat_id = msg.chat.id
    user_files[chat_id] = {"files": [], "is_collecting": True}
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Done", callback_data="done_collecting"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel_collecting")]
    ])
    
    await msg.reply_text(
        "📥 **Send all files to add to the ZIP.**\n"
        "When you're done, click the **Done** button.",
        reply_markup=keyboard
    )

@Client.on_message(filters.private & filters.user(ADMIN) & (filters.document | filters.video | filters.audio))
async def collect_files(bot, msg):
    chat_id = msg.chat.id
    if chat_id in user_files and user_files[chat_id]["is_collecting"]:
        user_files[chat_id]["files"].append(msg)
        count = len(user_files[chat_id]["files"])
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Done", callback_data="done_collecting"),
             InlineKeyboardButton("❌ Cancel", callback_data="cancel_collecting")]
        ])
        
        await msg.reply_text(
            f"📥 **File collected!**\n"
            f"Files collected: {count}\n"
            "Continue sending files or click **Done** when you're finished.",
            reply_markup=keyboard
        )

@Client.on_callback_query(filters.regex("done_collecting"))
async def done_collecting(bot, query: CallbackQuery):
    chat_id = query.message.chat.id
    files = user_files.get(chat_id, {}).get("files", [])
    
    if not files:
        await query.message.edit_text("⚠️ No files were sent to create a ZIP.")
        return
    
    file_names = "\n".join([f"`{f.document.file_name}`" for f in files])
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm", callback_data="confirm_zip"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel_collecting")]
    ])
    
    await query.message.edit_text(
        "📦 **The following files will be added to the ZIP:**\n\n" +
        file_names +
        "\n\nClick **Confirm** to proceed or **Cancel** to stop.",
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("confirm_zip"))
async def confirm_zip(bot, query: CallbackQuery):
    chat_id = query.message.chat.id
    
    await query.message.edit_text("🔤 **Send the name you want for the ZIP file.**")

    @Client.on_message(filters.private & filters.user(ADMIN))
    async def get_zip_name(bot, msg):
        if msg.chat.id == chat_id and msg.text:
            zip_name = msg.text + ".zip"
            await msg.reply_text("📥 **Downloading your files...**")
            
            zip_path = os.path.join(DOWNLOAD_LOCATION, zip_name)
            with zipfile.ZipFile(zip_path, 'w') as archive:
                for media_msg in user_files[chat_id]["files"]:
                    c_time = time.time()
                    file_path = await media_msg.download(progress=progress_message, progress_args=("Downloading...", msg, c_time))
                    archive.write(file_path, os.path.basename(file_path))
                    os.remove(file_path)
            
            await msg.reply_text("✅ **Files downloaded. Creating your ZIP...**")
            
            c_time = time.time()
            await bot.send_document(
                chat_id,
                document=zip_path,
                caption=f"Here is your ZIP file: `{zip_name}`",
                progress=progress_message,
                progress_args=("Uploading ZIP...", msg, c_time)
            )
            
            os.remove(zip_path)
            del user_files[chat_id]

@Client.on_callback_query(filters.regex("cancel_collecting"))
async def cancel_collecting(bot, query: CallbackQuery):
    chat_id = query.message.chat.id
    del user_files[chat_id]
    await query.message.edit_text("❌ **File collection cancelled.**")
