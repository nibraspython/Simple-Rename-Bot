import time
import os
import zipfile
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes

# Global variable to manage blocking state
command_block_state = {"zip_mode": False}

# Global variable to store files and user data
user_files = {}

@Client.on_message(filters.private & filters.command("block") & filters.user(ADMIN))
async def block_other_commands(bot, msg):
    command_block_state["zip_mode"] = True
    await msg.reply_text("🔒 **All commands are now blocked except /zip.**")

@Client.on_message(filters.private & filters.command("unblock") & filters.user(ADMIN))
async def unblock_other_commands(bot, msg):
    command_block_state["zip_mode"] = False
    await msg.reply_text("🔓 **/zip is now blocked, and other commands are unblocked.**")

@Client.on_message(filters.private & filters.command("zip") & filters.user(ADMIN))
async def start_archive(bot, msg):
    if not command_block_state["zip_mode"]:
        await msg.reply_text("⚠️ **/zip command is currently blocked. Please use /unblock to enable it.**")
        return

    chat_id = msg.chat.id

    # Initialize the user's session
    user_files[chat_id] = {"files": [], "is_collecting": False, "awaiting_zip_name": True}

    await msg.reply_text("🔤 **Please send the name you want for the ZIP file.**")

@Client.on_message(filters.private & filters.user(ADMIN) & filters.text)
async def receive_zip_name(bot, msg):
    chat_id = msg.chat.id

    if not command_block_state["zip_mode"]:
        return

    if chat_id in user_files and user_files[chat_id]["awaiting_zip_name"]:
        # Store the ZIP name and start file collection
        zip_name = msg.text + ".zip"
        user_files[chat_id]["zip_name"] = zip_name
        user_files[chat_id]["is_collecting"] = True
        user_files[chat_id]["awaiting_zip_name"] = False

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Done", callback_data="done_collecting"),
             InlineKeyboardButton("❌ Cancel", callback_data="cancel_collecting")]
        ])

        await msg.reply_text(
            "📥 **ZIP name set! Now, send the files you want to include in the ZIP.**\n"
            "When you're done, click the **Done** button.",
            reply_markup=keyboard
        )
    elif chat_id in user_files and user_files[chat_id]["is_collecting"]:
        # If the user is in the file collection phase, ignore text messages that aren't the command
        await msg.reply_text("⚠️ Please send files, or click **Done** when you're finished.")

@Client.on_message(filters.private & filters.user(ADMIN) & (filters.document | filters.video | filters.audio))
async def collect_files(bot, msg):
    chat_id = msg.chat.id
    
    if not command_block_state["zip_mode"]:
        return

    if chat_id in user_files and user_files[chat_id]["is_collecting"]:
        # Collect files
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
    if not command_block_state["zip_mode"]:
        return

    chat_id = query.message.chat.id
    files = user_files.get(chat_id, {}).get("files", [])
    zip_name = user_files.get(chat_id, {}).get("zip_name", "output.zip")
    
    if not files:
        await query.message.edit_text("⚠️ No files were sent to create a ZIP.")
        return
    
    # Fetching file names safely by checking if the media exists
    file_names = []
    for f in files:
        if f.document:
            file_names.append(f.document.file_name)
        elif f.video:
            file_names.append(f.video.file_name)
        elif f.audio:
            file_names.append(f.audio.file_name)
    
    file_list_text = "\n".join([f"`{name}`" for name in file_names])
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm", callback_data="confirm_zip"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel_collecting")]
    ])
    
    await query.message.edit_text(
        "📦 **The following files will be added to the ZIP:**\n\n" +
        file_list_text +
        f"\n\n**ZIP Name:** `{zip_name}`\n\nClick **Confirm** to proceed or **Cancel** to stop.",
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("confirm_zip"))
async def confirm_zip(bot, query: CallbackQuery):
    if not command_block_state["zip_mode"]:
        return
    
    chat_id = query.message.chat.id
    zip_name = user_files.get(chat_id, {}).get("zip_name", "output.zip")
    
    await query.message.edit_text("📥 **Downloading your files...**")
    
    zip_path = os.path.join(DOWNLOAD_LOCATION, zip_name)
    with zipfile.ZipFile(zip_path, 'w') as archive:
        for media_msg in user_files[chat_id]["files"]:
            c_time = time.time()
            file_path = await media_msg.download(progress=progress_message, progress_args=("Downloading...", query.message, c_time))
            archive.write(file_path, os.path.basename(file_path))
            os.remove(file_path)
    
    await query.message.edit_text("✅ **Files downloaded. Creating your ZIP...**")
    
    c_time = time.time()
    await bot.send_document(
        chat_id,
        document=zip_path,
        caption=f"Here is your ZIP file: `{zip_name}`",
        progress=progress_message,
        progress_args=("Uploading ZIP...", query.message, c_time)
    )
    
    os.remove(zip_path)
    del user_files[chat_id]

@Client.on_callback_query(filters.regex("cancel_collecting"))
async def cancel_collecting(bot, query: CallbackQuery):
    if not command_block_state["zip_mode"]:
        return
    
    chat_id = query.message.chat.id
    del user_files[chat_id]
    await query.message.edit_text("❌ **File collection cancelled.**")
