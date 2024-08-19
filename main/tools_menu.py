from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import ADMIN
from main.archive_creator import handle_archive_creation  # Import archive creation function

user_data = {}

@Client.on_message(filters.private & filters.command("tools") & filters.user(ADMIN))
async def tools_menu(bot, msg):
    # Show the tools menu
    keyboard = [
        [InlineKeyboardButton("Create Archive 📦", callback_data="create_archive")],
        [InlineKeyboardButton("Audio Extractor 🎧", callback_data="audio_extractor"),
         InlineKeyboardButton("Video Merger 🎥", callback_data="video_merger")],
        [InlineKeyboardButton("Video Trimmer ✂️", callback_data="video_trimmer")]
    ]
    await msg.reply_text("🎛️ **Tools Menu**\n\nSelect the tool you'd like to use:", reply_markup=InlineKeyboardMarkup(keyboard))

@Client.on_callback_query(filters.regex(r"create_archive") & filters.user(ADMIN))
async def on_create_archive(bot, query: CallbackQuery):
    # Handle the archive creation interaction
    await handle_archive_creation(bot, query)

# Other callback queries for different tools can be added here
