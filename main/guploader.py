import time, os
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes

@Client.on_message(filters.private & filters.command("gupload") & filters.user(ADMIN))
async def gdrive_upload(bot, msg):
    await msg.reply_text("📂 Please send the path of the folder that contains the files you want to upload.")
    
    @Client.on_message(filters.private & filters.text & filters.user(ADMIN))
    async def upload_files_to_gdrive(bot, path_msg):
        folder_path = path_msg.text.strip()
        if not os.path.exists(folder_path):
            return await path_msg.reply_text("❌ The specified path does not exist. Please try again.")

        files = os.listdir(folder_path)
        if not files:
            return await path_msg.reply_text("📁 The folder is empty. Please try again with a different folder.")
        
        await path_msg.reply_text(f"📤 Starting upload of {len(files)} files to Google Drive...")

        for file_name in files:
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                sts = await path_msg.reply_text(f"🚀 Uploading `{file_name}`...")
                c_time = time.time()

                # Create a Google Drive file instance and set its content
                gfile = drive.CreateFile({'title': file_name})
                gfile.SetContentFile(file_path)

                # Upload the file with progress display
                gfile.Upload(param={'progress': progress_message, 'progress_args': (f"Uploading {file_name}...", sts, c_time)})
                
                await sts.edit_text(f"✅ `{file_name}` uploaded successfully.")

        await path_msg.reply_text("🎉 All files have been uploaded to Google Drive successfully!")

    bot.add_handler(filters.private & filters.text & filters.user(ADMIN), upload_files_to_gdrive)
