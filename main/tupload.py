import os
import time
from pyrogram import Client, filters
from config import ADMIN, DOWNLOAD_LOCATION, CAPTION
from main.utils import progress_message, humanbytes

@Client.on_message(filters.private & filters.command("upload") & filters.user(ADMIN))
async def upload_file(bot, msg):
    await msg.reply_text("📁 Send the path of the file you want to upload to Telegram as DC4.")

@Client.on_message(filters.private & filters.command & filters.user(ADMIN))
async def handle_upload(bot, msg):
    try:
        file_path = msg.text.strip()
        if not os.path.exists(file_path):
            await msg.reply_text("❌ The specified file path does not exist.")
            return

        sts = await msg.reply_text("🚀 File uploading started..... 📤")

        # Get file name and size
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # Upload the file to Telegram specifying DC4
        await bot.send_document(
            chat_id=msg.chat.id,
            document=file_path,
            progress=progress_message,
            progress_args=("Upload Started..... Thanks To All Who Supported ❤", sts),
            caption=CAPTION.format(file_name=file_name, file_size=humanbytes(file_size)),
            dc="4"  # Specify DC4 for the file upload
        )

        os.remove(file_path)  # Remove the local file after upload
        await sts.delete()   # Delete the progress message

    except Exception as e:
        await sts.edit(f"❌ Error: {e}")

