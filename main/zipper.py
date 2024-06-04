import os
import zipfile
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes

# Initialize Pyrogram client
app = Client("zip_bot")

# Dictionary to store files for zipping
zip_files = {}

# /zip command handler
@Client.on_message(filters.private & filters.command("start") & filters.user(ADMIN))
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

# Handler for adding files to the ZIP list
@app.on_message(filters.private & (filters.document | filters.video | filters.audio) & filters.user(ADMIN))
async def add_file_to_zip(bot, msg: Message):
    chat_id = msg.chat.id
    if chat_id in zip_files:
        zip_files[chat_id].append(msg)
        await msg.reply_text(f"✅ File added to ZIP list. Total files: {len(zip_files[chat_id])}")

# Callback query handler for confirming ZIP files
@app.on_callback_query(filters.regex("zip_confirm") & filters.user(ADMIN))
async def confirm_zip_files(bot, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    if chat_id in zip_files and zip_files[chat_id]:
        await bot.send_message(chat_id, "Please provide a name for the ZIP file (without extension).")

# Callback query handler for canceling ZIP files
@app.on_callback_query(filters.regex("zip_cancel") & filters.user(ADMIN))
async def cancel_zip_files(bot, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    if chat_id in zip_files:
        del zip_files[chat_id]

# Handler for getting ZIP name and creating the ZIP file
@app.on_message(filters.private & filters.text & filters.user(ADMIN))
async def get_zip_name(bot, msg: Message):
    chat_id = msg.chat.id
    if chat_id in zip_files and zip_files[chat_id]:
        zip_name = msg.text
        await create_zip(bot, msg, zip_name)

# Function to create ZIP file
async def create_zip(bot: Client, msg: Message, zip_name: str):
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
