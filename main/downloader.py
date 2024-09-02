import os
import time
from pyrogram import Client, filters
from config import ADMIN
from main.utils import progress_message, humanbytes

# Define paths and rclone remote
RCLONE_CONFIG_PATH = '/content/Simple-Rename-Bot/rclone.conf'  # Path to the rclone configuration file
RCLONE_PATH = '/usr/bin/rclone'  # Path to the rclone executable
RCLONE_REMOTE = 'Colab to Drive:/'  # Use your correct remote name here

# Step 1: Handle the /gupload command
@Client.on_message(filters.private & filters.command("gupload") & filters.user(ADMIN))
async def upload_file(bot, msg):
    await msg.reply_text("📂 Please send the path to your file to upload to Google Drive.")

    # Step 2: Set up a listener for the next message containing the file path
    @Client.on_message(filters.private & filters.user(msg.from_user.id) & filters.text)
    async def get_file_path(bot, path_msg):
        file_path = path_msg.text.strip()

        if not os.path.isfile(file_path):
            return await path_msg.reply_text("❌ The provided path does not exist or is not a file. Please send a valid file path.")

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        filesize_human = humanbytes(file_size)
        sts = await path_msg.reply_text(f"🔄 Uploading **{file_name}**..... 📤")

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

        # Remove the handler after the file path is received and processed
        bot.remove_handler(get_file_path)
