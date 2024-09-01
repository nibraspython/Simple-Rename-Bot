from google_drive_auth import authenticate_drive

drive_service = authenticate_drive()

def upload_to_drive(file_path, file_name, mime_type='application/octet-stream'):
    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_path, mimetype=mime_type)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

@Client.on_message(filters.private & filters.command("gupload") & filters.user(ADMIN))
async def gupload(bot, msg):
    await msg.reply_text("📁 Please send the path of the folder that contains your files (e.g., content/downloads/).")

@Client.on_message(filters.private & filters.reply & filters.user(ADMIN))
async def upload_files(bot, msg):
    folder_path = msg.text.strip()
    if not os.path.isdir(folder_path):
        return await msg.reply_text("🚫 Invalid folder path. Please send a valid path.")

    files = os.listdir(folder_path)
    if not files:
        return await msg.reply_text("🚫 No files found in the specified folder.")

    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            sts = await msg.reply_text(f"🔄 Uploading {file_name}...")
            try:
                file_id = upload_to_drive(file_path, file_name)
                await sts.edit(f"✅ Successfully uploaded {file_name} to Google Drive.\nFile ID: {file_id}")
            except Exception as e:
                await sts.edit(f"❌ Failed to upload {file_name}. Error: {e}")
