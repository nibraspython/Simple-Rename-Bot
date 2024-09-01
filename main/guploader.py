import os
import time
from pyrogram import Client, filters
from google.colab import drive
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message

# Load the saved credentials from mycreds.txt
gauth = GoogleAuth()
gauth.LoadCredentialsFile("mycreds.txt")

# Create the Google Drive service
drive_service = build('drive', 'v3', credentials=gauth.credentials)

@Client.on_message(filters.private & filters.command("gupload") & filters.user(ADMIN))
async def upload_to_drive(bot, msg):
    await msg.reply_text("📁 Send the path of the file you want to upload to Google Drive.")

@Client.on_message(filters.private & ~filters.command & filters.user(ADMIN))
async def handle_upload_path(bot, msg):
    try:
        file_path = msg.text.strip()
        if not os.path.exists(file_path):
            await msg.reply_text("❌ The specified file path does not exist.")
            return

        sts = await msg.reply_text("🚀 File uploading started..... 📤")
        c_time = time.time()

        # Get file name from the path
        file_name = os.path.basename(file_path)

        # Upload the file to Google Drive using saved credentials
        file_metadata = {'name': file_name}
        media = MediaFileUpload(file_path, resumable=True)
        
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        # Send progress and completion message
        await msg.reply_text(f"✅ Uploaded '{file_name}' to Google Drive (File ID: {file.get('id')}).")

        os.remove(file_path)  # Remove the local file after upload
        await sts.delete()  # Delete the progress message

    except Exception as e:
        await sts.edit(f"❌ Failed to upload file: {e}")
