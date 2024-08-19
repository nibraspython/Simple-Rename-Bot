from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import ADMIN
from main.archive_creator import handle_archive_creation  # Archive creation logic in another file

user_data = {}

@Client.on_message(filters.private & filters.command("tools") & filters.user(ADMIN))
async def tools_menu(bot, msg):
    # Show the tools menu
    keyboard = [
        [InlineKeyboardButton("Create Archive 📦", callback_data="create_archive")],
        [InlineKeyboardButton("Audio Extractor 🎧", callback_data="audio_extractor"),
         InlineKeyboardButton("Video Merger 🎥", callback_data="video_merger")],
        [InlineKeyboardButton("Video Trimmer ✂️", callback_data="video_trimmer")]
    ]
    await msg.reply_text("🎛️ **Tools Menu**\n\nSelect the tool you'd like to use:", reply_markup=InlineKeyboardMarkup(keyboard))

@Client.on_callback_query(filters.regex('create_archive'))
async def create_archive_callback(bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user_data[user_id] = {'action': 'create_archive', 'files': []}
    await callback_query.message.edit_text(
        "📁 **Send all files you want to include in the archive.**\n\n🗂️ Files added: 0",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Done ✅", callback_data="archive_done"), InlineKeyboardButton("Cancel ❌", callback_data="archive_cancel")]
        ])
    )

@Client.on_message(filters.private & (filters.document | filters.video) & filters.user(ADMIN))
async def add_file_to_archive(bot, msg):
    user_id = msg.from_user.id
    if user_id in user_data and user_data[user_id]['action'] == 'create_archive':
        if msg.document:
            file_name = msg.document.file_name
        elif msg.video:
            file_name = msg.video.file_name
        else:
            return  # Ignore other media types

        user_data[user_id]['files'].append(msg)

        file_list = "\n".join([f"{i+1}. {file.document.file_name or file.video.file_name}" for i, file in enumerate(user_data[user_id]['files'])])

        # Update message after every file sent with new file count and list
        await msg.reply_text(
            f"📁 **Files added:** {len(user_data[user_id]['files'])}\n\n{file_list}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Done ✅", callback_data="archive_done"), InlineKeyboardButton("Cancel ❌", callback_data="archive_cancel")]
            ])
        )

@Client.on_callback_query(filters.regex('archive_done'))
async def archive_done_callback(bot, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id in user_data:
        await callback_query.message.edit_text("🎨 **Send your custom name for the ZIP file:**")
        user_data[user_id]['awaiting_name'] = True

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def get_custom_zip_name(bot, msg):
    user_id = msg.from_user.id
    if user_id in user_data and user_data[user_id].get('awaiting_name'):
        custom_name = msg.text
        await handle_archive_creation(bot, msg, user_data, custom_name)
        del user_data[user_id]  # Clear user data after completion
