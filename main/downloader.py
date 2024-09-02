import os
import time
from pyrogram import Client, filters
from config import ADMIN
from main.utils import progress_message, humanbytes

# Define paths and rclone remote
RCLONE_CONFIG_PATH = '/content/Simple-Rename-Bot/rclone.conf'  # Path to the rclone configuration file
RCLONE_PATH = '/usr/bin/rclone'  # Path to the rclone executable
RCLONE_REMOTE = 'Colab to Drive:/'  # Use your correct remote name here

@Client.on_message(filters.private & filters.command("gupload") & filters.user(ADMIN))
async def upload_file(bot, msg):
    # Ask the user for the file path
    await msg.reply_text("📂 Please send the path to your file to upload to Google Drive.")

    # Define a filter to capture the next message from the user
    def path_filter(_, __, incoming_message):
        return incoming_message.from_user.id == msg.from_user.id

    # Listen for the next message from the user
    response = await bot.listen(msg.chat.id, filters=filters.text & path_filter)
    file_path = response.text.strip()

    if not os.path.isfile(file_path):
        return await msg.reply_text("❌ The provided path does not exist or is not a file. Please send a valid file path.")

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    filesize_human = humanbytes(file_size)
    sts = await msg.reply_text(f"🔄 Uploading **{file_name}**..... 📤")

    c_time = time.time()

    def rclone_upload_progress(line):
        """Parse rclone progress line for transferred and percentage information."""
        parts = line.split()
        transferred = parts[1]  # e.g., "10.5M"
        progress_percentage = parts[4]  # e.g., "50%"
        return transferred, progress_percentage

    try:
        upload_command = f"{RCLONE_PATH} copy '{file_path}' {RCLONE_REMOTE} --config={RCLONE_CONFIG_PATH} --progress"
        with os.popen(upload_command) as process:
            while True:
                line = process.readline()
                if not line:
                    break

                transfer_info = rclone_upload_progress(line)
                if transfer_info:
                    transferred, progress_percentage = transfer_info
                    await sts.edit(f"🚀 Uploading **{file_name}**...\n🔄 Transferred: {transferred}\n📈 Progress: {progress_percentage}")

    except Exception as e:
        return await sts.edit(f"❌ Error during upload: {e}")

    await sts.edit(f"✅ Upload Complete!\n📁 **{file_name}**\n📦 Size: {filesize_human}")
