import time
import os
import zipfile
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes

zip_files = {}

@Client.on_message(filters.private & filters.command("zip") & filters.user(ADMIN))
async def zip_files_handler(bot, msg):
    chat_id = msg.chat.id
    zip_files[chat_id] = []

    confirm_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm", callback_data="zip_confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="zip_cancel")]
    ])
    
    await msg.reply_text(
        "📁 Send all the files you want to ZIP.\nClick the Confirm button when you're done.",
        reply_markup=confirm_keyboard
    )

@Client.on_message(filters.private & filters.document & filters.user(ADMIN))
async def add_file_to_zip(bot, msg):
    chat_id = msg.chat.id
    if chat_id in zip_files:
        zip_files[chat_id].append(msg)
        await msg.reply_text(f"✅ File added to ZIP list. Total files: {len(zip_files[chat_id])}")

@Client.on_callback_query(filters.regex("zip_confirm") & filters.user(ADMIN))
async def confirm_zip_files(bot, callback_query):
    chat_id = callback_query.message.chat.id
    if chat_id in zip_files and zip_files[chat_id]:
        await bot.send_message(chat_id, "Please provide a name for the ZIP file (without extension).")
    else:
        await bot.send_message(chat_id, "No files were added to the ZIP list.")

@Client.on_callback_query(filters.regex("zip_cancel") & filters.user(ADMIN))
async def cancel_zip_files(bot, callback_query):
    chat_id = callback_query.message.chat.id
    if chat_id in zip_files:
        del zip_files[chat_id]
    await bot.send_message(chat_id, "❌ ZIP creation canceled.")

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def get_zip_name(bot, msg):
    chat_id = msg.chat.id
    if chat_id in zip_files and zip_files[chat_id]:
        zip_name = msg.text
        await create_zip(bot, msg, zip_name)

async def create_zip(bot, msg, zip_name):
    chat_id = msg.chat.id
    zip_path = os.path.join(DOWNLOAD_LOCATION, f"{zip_name}.zip")
    sts = await msg.reply_text("🔄 Downloading files for ZIP... 📥")

    try:
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for i, file_msg in enumerate(zip_files[chat_id]):
                c_time = time.time()
                downloaded = await file_msg.download(progress=progress_message, progress_args=(f"Downloading file {i+1}/{len(zip_files[chat_id])}...", sts, c_time))
                zipf.write(downloaded, os.path.basename(downloaded))
                os.remove(downloaded)
        
        filesize = humanbytes(os.path.getsize(zip_path))
        cap = CAPTION.format(file_name=f"{zip_name}.zip", file_size=filesize) if CAPTION else f"{zip_name}.zip\n\n💽 size: {filesize}"
        
        await sts.edit("🚀 Uploading ZIP file... 📤")
        c_time = time.time()
        await bot.send_document(chat_id, document=zip_path, caption=cap, progress=progress_message, progress_args=("Uploading ZIP file...", sts, c_time))
        os.remove(zip_path)
    except Exception as e:
        await sts.edit(f"Error: {e}")
    finally:
        del zip_files[chat_id]
        await sts.delete()
