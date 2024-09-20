import time, os
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# Load Google Drive credentials from the token.pickle file
def create_drive_service():
    creds = Credentials.from_authorized_user_file('/mnt/data/token.pickle', ['https://www.googleapis.com/auth/drive.file'])
    return build('drive', 'v3', credentials=creds)

@Client.on_message(filters.private & filters.command("gupload") & filters.user(ADMIN))
async def upload_to_gdrive(bot, msg):
    reply = msg.reply_to_message
    if not reply or not (reply.document or reply.audio or reply.video):
        return await msg.reply_text("Please reply to a file (document, video, or audio) to upload to Google Drive.")
    
    # Get the media and original file name
    media = reply.document or reply.audio or reply.video
    og_media = getattr(reply, reply.media.value)
    new_name = media.file_name
    
    # Start downloading the file with progress bar
    sts = await msg.reply_text(f"🔄 Downloading **{new_name}**...📥")
    c_time = time.time()
    downloaded = await reply.download(file_name=new_name, progress=progress_message, progress_args=(f"Downloading **{new_name}**...", sts, c_time))
    filesize = humanbytes(og_media.file_size)

    # Google Drive Upload
    await sts.edit(f"🚀 Uploading **{new_name}** to Google Drive... 📤")
    
    try:
        # Create Google Drive service
        drive_service = create_drive_service()
        file_metadata = {'name': new_name}
        media_body = MediaFileUpload(downloaded, resumable=True)

        # Upload the file to Google Drive
        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media_body, fields='id').execute()

        # Notify user on successful upload
        await sts.edit(f"✅ File **{new_name}** uploaded successfully to Google Drive!\n💽 Size: {filesize}")
    except Exception as e:
        await sts.edit(f"❌ Upload failed: {e}")
    
    # Clean up the downloaded file
    try:
        os.remove(downloaded)
    except Exception as e:
        print(f"Error removing file: {e}")
