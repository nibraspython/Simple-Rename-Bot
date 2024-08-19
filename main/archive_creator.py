import os
import zipfile
from pyrogram import Client, CallbackQuery
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message  # Assuming you have a progress_message function

async def handle_archive_creation(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id

    # Request the user to send files for archiving
    await query.message.reply_text(
        "📦 **Please send the files you want to archive.**\n\n"
        "You can send multiple files, and when you're done, use the `/done` command."
    )

    # Placeholder for storing files before zipping
    user_data[user_id] = []

    @Client.on_message(filters.private & filters.user(ADMIN) & ~filters.command(["done"]))
    async def collect_files(bot, msg):
        if user_id in user_data:
            file_id = msg.document.file_id
            user_data[user_id].append(file_id)
            await msg.reply_text("✅ **File added to the archive list.**")

    @Client.on_message(filters.private & filters.command("done") & filters.user(ADMIN))
    async def create_archive(bot, msg):
        if user_id not in user_data or len(user_data[user_id]) == 0:
            await msg.reply_text("❌ **No files added. Please send some files first.**")
            return

        # Creating a zip file
        zip_filename = os.path.join(DOWNLOAD_LOCATION, f"{user_id}_archive.zip")
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file_id in user_data[user_id]:
                file_path = await bot.download_media(file_id)
                zipf.write(file_path, os.path.basename(file_path))
                os.remove(file_path)  # Clean up the file after adding to the zip

        await msg.reply_text("🚀 **Uploading the archive...**")
        c_time = time.time()
        await bot.send_document(
            chat_id=user_id,
            document=zip_filename,
            caption="**Here's your archive!**",
            progress=progress_message,
            progress_args=("Upload Started..... Thanks To All Who Supported ❤", msg, c_time)
        )

        # Clean up
        os.remove(zip_filename)
        del user_data[user_id]

    @Client.on_message(filters.private & filters.command("cancel") & filters.user(ADMIN))
    async def cancel_archiving(bot, msg):
        if user_id in user_data:
            del user_data[user_id]
        await msg.reply_text("❌ **Archiving process canceled.**")
