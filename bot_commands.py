# bot_commands.py

from pyrogram import Client, filters
from config import ADMIN

# Import command handlers from separate files
from downloader import ytdl, youtube_link_handler, yt_callback_handler, description_callback_handler
from trimmer import start_trim_process, receive_media, receive_durations, trim_confirm_callback, trim_cancel_callback
from archive_creator import start_zip, add_file_to_zip, ask_for_zip_name, cancel_zip_creation, create_zip_file
from start_text import start_text  # Import start text handler

@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def ytdl_command(bot, msg):
    await ytdl(bot, msg)

@Client.on_message(filters.private & filters.user(ADMIN) & filters.regex(r'https?://(www\.)?youtube\.com/watch\?v='))
async def youtube_link_handler_command(bot, msg):
    await youtube_link_handler(bot, msg)

@Client.on_callback_query(filters.regex(r'^yt_\d+_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler_command(bot, query):
    await yt_callback_handler(bot, query)

@Client.on_callback_query(filters.regex(r'^desc_https?://(www\.)?youtube\.com/watch\?v='))
async def description_callback_handler_command(bot, query):
    await description_callback_handler(bot, query)

@Client.on_message(filters.private & filters.command("trim") & filters.user(ADMIN))
async def start_trim_process_command(bot, msg):
    await start_trim_process(bot, msg)

@Client.on_message(filters.private & filters.media & filters.user(ADMIN))
async def receive_media_command(bot, msg):
    await receive_media(bot, msg)

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def receive_durations_command(bot, msg):
    await receive_durations(bot, msg)

@Client.on_callback_query(filters.regex("trim_confirm") & filters.user(ADMIN))
async def trim_confirm_callback_command(bot, query):
    await trim_confirm_callback(bot, query)

@Client.on_callback_query(filters.regex("trim_cancel") & filters.user(ADMIN))
async def trim_cancel_callback_command(bot, query):
    await trim_cancel_callback(bot, query)

@Client.on_message(filters.private & filters.command("zip") & filters.user(ADMIN))
async def start_zip_command(bot, msg):
    await start_zip(bot, msg)

@Client.on_message(filters.private & filters.document & filters.user(ADMIN))
async def add_file_to_zip_command(bot, msg):
    await add_file_to_zip(bot, msg)

@Client.on_callback_query(filters.regex("done_zip"))
async def ask_for_zip_name_command(bot, query):
    await ask_for_zip_name(bot, query)

@Client.on_callback_query(filters.regex("cancel_zip"))
async def cancel_zip_creation_command(bot, query):
    await cancel_zip_creation(bot, query)

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def create_zip_file_command(bot, msg):
    await create_zip_file(bot, msg)

@Client.on_message(filters.command("start"))
async def start_text_command(bot, msg):
    await start_text(bot, msg)
