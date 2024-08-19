import time, os
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import ADMIN
from main.utils import progress_message
from main.archive_creator import handle_archive_creation  # Importing the function from another file

user_data = {}

@Client.on_message(filters.private & filters.command("tools") & filters.user(ADMIN))
async def tools_menu(bot, msg):
    # Show the initial tools menu
    keyboard = [
        [InlineKeyboardButton("Create Archive 📦", callback_data="create_archive")],
        [InlineKeyboardButton("Audio Extractor 🎧", callback_data="audio_extractor"),
         InlineKeyboardButton("Video Merger 🎥", callback_data="video_merger")],
        [InlineKeyboardButton("Video Trimmer ✂️", callback_data="video_trimmer")]
    ]
    await msg.reply_text("🎛️ **Tools Menu**\n\nPlease send your video or document:", reply_markup=InlineKeyboardMarkup(keyboard))

@Client.on_message(filters.private & (filters.document | filters.video) & filters.user(ADMIN))
async def handle_media(bot, msg):
    user_data[msg.from_user.id] = {
        'media': msg,
        'action': None,
        'files': []
    }
    keyboard = [
        [InlineKeyboardButton("Create Archive 📦", callback_data="create_archive")],
        [InlineKeyboardButton("Audio Extractor 🎧", callback_data="audio_extractor"),
         InlineKeyboardButton("Video Merger 🎥", callback_data="video_merger")],
        [InlineKeyboardButton("Video Trimmer ✂️", callback_data="video_trimmer")]
    ]
    await msg.reply_text("🛠️ **Select the tool you'd like to use:**", reply_markup=InlineKeyboardMarkup(keyboard))

@Client.on_callback_query(filters.regex(r'create_archive|audio_extractor|video_merger|video_trimmer'))
async def tools_callback(bot, callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    if user_id not in user_data or 'media' not in user_data[user_id]:
        return await callback_query.answer("Please send a video or document first.")
    
    user_data[user_id]['action'] = data
    
    if data == 'create_archive':
        await callback_query.message.edit_text(
            "📁 **Send all files you want to include in the archive.**\n\n🗂️ Files added: 0",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Done ✅", callback_data="archive_done"), InlineKeyboardButton("Cancel ❌", callback_data="archive_cancel")]])
        )

@Client.on_message(filters.private & (filters.document | filters.video) & filters.user(ADMIN))
async def add_file_to_archive(bot, msg):
    user_id = msg.from_user.id
    
    if user_id in user_data and user_data[user_id]['action'] == 'create_archive':
        user_data[user_id]['files'].append(msg)
        file_list = "\n".join([f"{i+1}. {file.document.file_name}" for i, file in enumerate(user_data[user_id]['files'])])
        await msg.reply_text(
            f"📁 **Files added:** {len(user_data[user_id]['files'])}\n\n{file_list}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Done ✅", callback_data="archive_done"), InlineKeyboardButton("Cancel ❌", callback_data="archive_cancel")]])
        )

@Client.on_callback_query(filters.regex('archive_done'))
async def archive_done(bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in user_data:
        await callback_query.message.edit_text("🎨 **Send your custom name for the ZIP file:**")
        user_data[user_id]['awaiting_name'] = True

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def get_custom_zip_name(bot, msg):
    user_id = msg.from_user.id
    
    if user_id in user_data and user_data[user_id].get('awaiting_name'):
        custom_name = msg.text
        await msg.reply_text(f"📦 **Creating archive `{custom_name}.zip`**...\n\n⬇️ Downloading files... Please wait.")
        
        await handle_archive_creation(bot, msg, user_data, custom_name)
        del user_data[user_id]  # Clear user data after completion
