import time
import os
from moviepy.editor import VideoFileClip, concatenate_videoclips
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes

class VideoManager:
    def __init__(self):
        self.chat_data = {}

    def start_merge_process(self, chat_id):
        self.chat_data[chat_id] = {"files": [], "waiting_for_name": False, "active": True}

    def add_file(self, chat_id, file):
        if chat_id not in self.chat_data:
            self.start_merge_process(chat_id)
        self.chat_data[chat_id]["files"].append(file)

    def get_files(self, chat_id):
        return self.chat_data.get(chat_id, {}).get("files", [])

    def clear_files(self, chat_id):
        if chat_id in self.chat_data:
            self.chat_data[chat_id]["files"] = []

    def set_waiting_for_name(self, chat_id, state):
        if chat_id not in self.chat_data:
            self.start_merge_process(chat_id)
        self.chat_data[chat_id]["waiting_for_name"] = state

    def is_waiting_for_name(self, chat_id):
        return self.chat_data.get(chat_id, {}).get("waiting_for_name", False)
    
    def is_active(self, chat_id):
        return self.chat_data.get(chat_id, {}).get("active", False)

    def deactivate(self, chat_id):
        if chat_id in self.chat_data:
            self.chat_data[chat_id]["active"] = False

video_manager = VideoManager()

@Client.on_message(filters.private & filters.command("merge") & filters.user(ADMIN))
async def start_merge_process(bot, msg):
    chat_id = msg.chat.id
    video_manager.start_merge_process(chat_id)
    await msg.reply_text("🎬 Send your video files (.mp4 or .mkv) to merge.\n\nUse /done when finished or /cancel to abort.")

@Client.on_message(filters.private & filters.user(ADMIN) & ~filters.command(["merge", "done", "cancel"]))
async def add_file_to_merge(bot, msg):
    chat_id = msg.chat.id
    if not video_manager.is_active(chat_id):
        return  # Ignore messages if merging process is not active
    
    media = msg.video
    if not media or not (media.file_name.endswith(".mp4") or media.file_name.endswith(".mkv")):
        return await msg.reply_text("Please send a valid video file (.mp4 or .mkv).")
    
    video_manager.add_file(chat_id, media)
    files = video_manager.get_files(chat_id)
    file_names = "\n".join([file.file_name for file in files])
    file_count = len(files)
    
    await msg.reply_text(f"🎥 Videos added: {file_count}\n{file_names}",
                         reply_markup=InlineKeyboardMarkup([
                             [InlineKeyboardButton("✅ Done", callback_data="done")],
                             [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
                         ]))

@Client.on_callback_query(filters.regex(r"done|cancel"))
async def handle_done_cancel(bot, query):
    chat_id = query.message.chat.id
    if query.data == "cancel":
        video_manager.clear_files(chat_id)
        video_manager.deactivate(chat_id)
        await query.message.edit_text("❌ Merging process canceled.")
        return
    
    if query.message.text != "📛 Send your custom name without extension for the merged video file.":
        await query.message.edit_text("📛 Send your custom name without extension for the merged video file.")
    video_manager.set_waiting_for_name(chat_id, True)

@Client.on_message(filters.private & filters.user(ADMIN))
async def handle_custom_name(bot, msg):
    chat_id = msg.chat.id
    if not video_manager.is_active(chat_id):
        return  # Ignore messages if merging process is not active
    
    if video_manager.is_waiting_for_name(chat_id):
        custom_name = msg.text.strip()
        if not custom_name:
            return await msg.reply_text("Please provide a valid name for the merged video file.")
        
        files = video_manager.get_files(chat_id)
        if not files:
            return await msg.reply_text("No videos to merge.")
        
        video_path = os.path.join(DOWNLOAD_LOCATION, f"{custom_name}.mp4")
        sts = await msg.reply_text("🔄 Downloading videos...")
        
        # Download files
        c_time = time.time()
        downloaded_files = []
        for file in files:
            downloaded = await bot.download_media(file, progress=progress_message,
                                                  progress_args=("Downloading...", sts, c_time))
            downloaded_files.append(downloaded)
        
        # Merge videos
        sts = await sts.edit("🔄 Merging videos...")
        clips = [VideoFileClip(file_path) for file_path in downloaded_files]
        final_clip = concatenate_videoclips(clips)
        final_clip.write_videofile(video_path)
        
        # Upload merged video
        c_time = time.time()
        await bot.send_document(chat_id, video_path, caption=f"🎉 Here is your merged video: {custom_name}.mp4",
                                progress=progress_message, progress_args=("Uploading...", sts, c_time))
        
        # Cleanup
        for file_path in downloaded_files:
            os.remove(file_path)
        os.remove(video_path)
        
        video_manager.clear_files(chat_id)
        video_manager.set_waiting_for_name(chat_id, False)
        video_manager.deactivate(chat_id)
        await sts.delete()
