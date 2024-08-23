import time, os, zipfile
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes

# Dictionary to keep track of user sessions for creating a zip
zip_sessions = {}

@Client.on_message(filters.private & filters.command("zip") & filters.user(ADMIN))
async def start_zip(bot, msg):
    chat_id = msg.chat.id
    zip_sessions[chat_id] = []
    await msg.reply_text(
        "📂 Send all the files you want to add to the zip. Click 'Done' when finished.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Done", callback_data="done_zip")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_zip")]
        ])
    )

@Client.on_message(filters.private & filters.document & filters.user(ADMIN))
async def add_file_to_zip(bot, msg):
    chat_id = msg.chat.id
    if chat_id in zip_sessions:
        zip_sessions[chat_id].append(msg)
        file_count = len(zip_sessions[chat_id])
        file_list = "\n".join([f.document.file_name for f in zip_sessions[chat_id]])
        await msg.reply_text(
            f"📄 Files to be added: {file_count}\n{file_list}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Done", callback_data="done_zip")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_zip")]
            ])
        )

@Client.on_callback_query(filters.regex("done_zip"))
async def ask_for_zip_name(bot, query):
    chat_id = query.message.chat.id
    await query.message.reply_text("📝 Send your custom name for the zip file.")

@Client.on_callback_query(filters.regex("cancel_zip"))
async def cancel_zip_creation(bot, query):
    chat_id = query.message.chat.id
    if chat_id in zip_sessions:
        del zip_sessions[chat_id]
    await query.message.reply_text("❌ Zip creation cancelled.")

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def create_zip_file(bot, msg):
    chat_id = msg.chat.id
    if chat_id not in zip_sessions or not zip_sessions[chat_id]:
        return

    zip_name = f"{msg.text}.zip"
    zip_path = os.path.join(DOWNLOAD_LOCATION, zip_name)
    sts = await msg.reply_text("🔄 Downloading files... 📥")

    # Download all files
    file_paths = []
    for file_msg in zip_sessions[chat_id]:
        c_time = time.time()
        file_name = file_msg.document.file_name
        downloaded = await file_msg.download(file_name=file_name, progress=progress_message, progress_args=("Download Started..... Thanks To All Who Supported ❤", sts, c_time))
        file_paths.append(downloaded)

    await sts.edit("📦 Creating zip file...")

    # Create the zip file
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in file_paths:
            zipf.write(file, os.path.basename(file))

    await sts.edit("🚀 Uploading zip file... 📤")
    
    c_time = time.time()
    try:
        await bot.send_document(
            chat_id,
            zip_path,
            caption=f"Here is your zip file: {zip_name}",
            progress=progress_message,
            progress_args=("Upload Started..... Thanks To All Who Supported ❤", sts, c_time)
        )
    except Exception as e:
        return await sts.edit(f"Error: {e}")

    # Cleanup
    os.remove(zip_path)
    for file in file_paths:
        os.remove(file)

    del zip_sessions[chat_id]
    await sts.delete()
