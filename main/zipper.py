import time
import os
import zipfile
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes

# Temporary storage for files to zip
files_to_zip = {}

@Client.on_message(filters.private & filters.command("zip") & filters.user(ADMIN))
async def zip_files(bot, msg):
    chat_id = msg.chat.id
    files_to_zip[chat_id] = []

    buttons = [
        [InlineKeyboardButton("Done ✔️", callback_data="zip_done")],
        [InlineKeyboardButton("Cancel 🚫", callback_data="zip_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await msg.reply_text("📤 **Send all the files to be zipped. Click 'Done ✔️' when finished or 'Cancel 🚫' to abort.**", reply_markup=reply_markup)

@Client.on_message(filters.private & filters.media & filters.user(ADMIN))
async def receive_files(bot, msg):
    chat_id = msg.chat.id
    if chat_id in files_to_zip:
        media = msg.document or msg.audio or msg.video
        if media:
            files_to_zip[chat_id].append(media)
            await msg.reply_text(f"📥 **File received: {media.file_name}**\n📁 **Total files: {len(files_to_zip[chat_id])}**")

@Client.on_callback_query(filters.regex("zip_done") & filters.user(ADMIN))
async def zip_done_callback(bot, query):
    chat_id = query.message.chat.id
    if chat_id in files_to_zip and files_to_zip[chat_id]:
        file_list = "\n".join([f"{i+1}. {file.file_name}" for i, file in enumerate(files_to_zip[chat_id])])
        await query.message.reply_text(
            f"📂 **Files to be zipped:**\n\n{file_list}\n\n📁 **Total files: {len(files_to_zip[chat_id])}**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Confirm ✔️", callback_data="zip_confirm")],
                [InlineKeyboardButton("Cancel 🚫", callback_data="zip_cancel")]
            ])
        )
    else:
        await query.message.reply_text("⚠️ **No files received to zip.**")
    await query.message.delete()

@Client.on_callback_query(filters.regex("zip_confirm") & filters.user(ADMIN))
async def zip_confirm_callback(bot, query):
    await query.message.reply_text("💡 **Send the name for the ZIP file (without extension):**")
    await query.message.delete()

@Client.on_callback_query(filters.regex("zip_cancel") & filters.user(ADMIN))
async def zip_cancel_callback(bot, query):
    chat_id = query.message.chat.id
    if chat_id in files_to_zip:
        del files_to_zip[chat_id]
    await query.message.reply_text("❌ **ZIP creation canceled.**")
    await query.message.delete()

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def get_zip_filename(bot, msg):
    chat_id = msg.chat.id
    if chat_id in files_to_zip and files_to_zip[chat_id]:
        zip_filename = msg.text.strip() + ".zip"
        zip_filepath = os.path.join(DOWNLOAD_LOCATION, zip_filename)
        sts = await msg.reply_text("🔄 **Downloading files...**")

        downloaded_files = []
        for media in files_to_zip[chat_id]:
            c_time = time.time()
            downloaded_file = await bot.download_media(
                media,
                progress=progress_message,
                progress_args=(f"⬇️ **Downloading {media.file_name}...**", sts, c_time)
            )
            downloaded_files.append(downloaded_file)

        sts = await sts.edit("🔄 **Creating ZIP file...**")

        # Create ZIP file
        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for file in downloaded_files:
                zipf.write(file, os.path.basename(file))

        filesize = humanbytes(os.path.getsize(zip_filepath))
        await sts.edit(f"📦 **ZIP file created: {zip_filename}**\n📏 **Size: {filesize}**")

        c_time = time.time()
        await bot.send_document(
            msg.chat.id,
            document=zip_filepath,
            caption=f"📦 **{zip_filename}**\n📏 **Size: {filesize}**",
            progress=progress_message,
            progress_args=("⬆️ **Uploading ZIP file...**", sts, c_time)
        )

        # Clean up
        for file in downloaded_files:
            os.remove(file)
        os.remove(zip_filepath)
        del files_to_zip[chat_id]
        await sts.delete()
