import os
import time
import zipfile
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import ADMIN, DOWNLOAD_LOCATION
from main.utils import progress_message, humanbytes

user_data = {}

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
            file_type = 'document'
        elif msg.video:
            file_name = msg.video.file_name
            file_type = 'video'
        else:
            return  # Ignore other media types

        # Append the file to the user's data
        user_data[user_id]['files'].append({
            'message': msg,
            'file_name': file_name,
            'file_type': file_type
        })

        # Generate the file list text
        file_list = "\n".join([f"{i+1}. {file['file_name']}" for i, file in enumerate(user_data[user_id]['files'])])

        # Send updated file count and list as a new message
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

async def handle_archive_creation(bot: Client, msg, user_data, custom_name):
    user_id = msg.from_user.id

    if user_id not in user_data:
        await msg.reply_text("No files found to create an archive.")
        return

    # Create the directory for the downloaded files if it doesn't exist
    download_dir = os.path.join(DOWNLOAD_LOCATION, f"{custom_name}_temp")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    media_files = []
    for file_info in user_data[user_id]['files']:
        media = file_info['message']
        file_name = file_info['file_name']
        file_path = os.path.join(download_dir, file_name)

        # Download each file
        sts = await msg.reply_text(f"🔄 Downloading {file_name}.....📥")
        c_time = time.time()
        downloaded = await media.download(file_name=file_path, progress=progress_message, progress_args=(f"Download Started: {file_name}..... Thanks To All Who Supported ❤", sts, c_time))
        media_files.append(downloaded)

    # Create a ZIP file
    zip_file_path = os.path.join(DOWNLOAD_LOCATION, f"{custom_name}.zip")
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for file_path in media_files:
            zipf.write(file_path, os.path.basename(file_path))

    # Clean up downloaded files
    for file_path in media_files:
        os.remove(file_path)
    os.rmdir(download_dir)

    # Upload the ZIP file
    filesize = humanbytes(os.path.getsize(zip_file_path))
    await sts.edit("🚀 Uploading started..... 📤Thanks To All Who Supported ❤")
    c_time = time.time()
    try:
        await bot.send_document(msg.chat.id, document=zip_file_path, caption=f"{custom_name}.zip\n\n💽 size: {filesize}", progress=progress_message, progress_args=(f"Upload Started: {custom_name}.zip..... Thanks To All Who Supported ❤", sts, c_time))
    except Exception as e:
        await msg.reply_text(f"Error: {e}")
    finally:
        os.remove(zip_file_path)  # Remove the ZIP file after uploading
