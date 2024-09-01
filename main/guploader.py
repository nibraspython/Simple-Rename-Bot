from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaFileUpload
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, ADMIN
import os

# Load the service account JSON file
SERVICE_ACCOUNT_FILE = 'service_account.json'

# Define the scope for Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']

# Create credentials using the service account file
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Build the Google Drive service
drive_service = build('drive', 'v3', credentials=creds)

@Client.on_message(filters.private & filters.command("gupload") & filters.user(ADMIN))
async def upload_to_drive(bot, msg):
    # Ask user for the folder path in Colab
    await msg.reply_text("📁 Send the path of the folder containing the files you want to upload.")

    # Create a filter to capture the next message from the same user
    def check(_, __, incoming_msg):
        return incoming_msg.chat.id == msg.chat.id and incoming_msg.from_user.id == msg.from_user.id

    # Wait for the next message from the user
    response = await bot.listen(msg.chat.id, filters=filters.text, timeout=60)
    folder_path = response.text.strip()

    if not os.path.exists(folder_path):
        return await msg.reply_text(f"❌ The path '{folder_path}' does not exist.")

    # Upload each file in the folder
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        if os.path.isfile(file_path):
            file_metadata = {'name': file_name}
            media = MediaFileUpload(file_path, resumable=True)

            file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            # Send progress and completion message
            await msg.reply_text(f"✅ Uploaded '{file_name}' to Google Drive (File ID: {file.get('id')}).")

    await msg.reply_text("🎉 All files have been uploaded successfully!")

# Start the bot
app.run()
