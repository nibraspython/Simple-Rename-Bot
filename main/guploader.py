import time
import os
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# Initialize GoogleAuth and GoogleDrive
gauth = GoogleAuth()
drive = GoogleDrive(gauth)

auth_stage = {}  # Dictionary to keep track of users in the authentication stage

@Client.on_message(filters.private & filters.command("gupload") & filters.user(ADMIN))
async def gdrive_upload(bot, msg):
    user_id = msg.from_user.id
    if user_id not in auth_stage:
        # Start authentication process
        auth_url = gauth.GetAuthUrl()
        auth_stage[user_id] = 'auth'  # Set the stage to authentication
        await msg.reply_text(f"Please authenticate by visiting the following URL: {auth_url}\n"
                             "After authentication, send the verification code here.")

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def handle_auth_and_upload(bot, msg):
    user_id = msg.from_user.id

    if user_id in auth_stage:
        if auth_stage[user_id] == 'auth':
            # Handle Google Drive authentication
            auth_code = msg.text.strip()
            try:
                gauth.Authenticate(auth_code)
                gauth.SaveCredentialsFile("mycreds.txt")  # Save credentials
                drive.auth = gauth
                auth_stage[user_id] = 'upload'  # Move to upload stage
                await msg.reply_text("✅ Authentication successful! Please send the path of the folder that contains the files you want to upload.")
            except Exception as e:
                await msg.reply_text(f"❌ Authentication failed: {str(e)}")
                del auth_stage[user_id]
        elif auth_stage[user_id] == 'upload':
            # Handle file upload
            folder_path = msg.text.strip()
            if not os.path.exists(folder_path):
                return await msg.reply_text("❌ The specified path does not exist. Please try again.")

            files = os.listdir(folder_path)
            if not files:
                return await msg.reply_text("📁 The folder is empty. Please try again with a different folder.")
            
            await msg.reply_text(f"📤 Starting upload of {len(files)} files to Google Drive...")

            for file_name in files:
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path):
                    sts = await msg.reply_text(f"🚀 Uploading `{file_name}`...")
                    c_time = time.time()

                    # Create a Google Drive file instance and set its content
                    gfile = drive.CreateFile({'title': file_name})
                    gfile.SetContentFile(file_path)

                    # Upload the file with progress display using existing progress_message
                    gfile.Upload(param={'progress': progress_message, 'progress_args': (f"Uploading {file_name}...", sts, c_time)})
                    
                    await sts.edit_text(f"✅ `{file_name}` uploaded successfully.")

            await msg.reply_text("🎉 All files have been uploaded to Google Drive successfully!")

            # Clean up the auth_stage entry
            del auth_stage[user_id]
        else:
            await msg.reply_text("❌ Invalid stage. Please start over by sending /gupload.")
    else:
        await msg.reply_text("❌ Please start the process by sending /gupload.")
