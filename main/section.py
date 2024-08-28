import os
from pyrogram import Client, filters
from config import ADMIN

# Initialize the Pyrogram Client
app = Client(...)

@Client.on_message(filters.private & filters.command("next") & filters.user(ADMIN))
async def next_section(bot, msg):
    await msg.reply_text("Stopping current execution and proceeding to the next section...")
    os._exit(0)  # Exit the current cell and proceed to the next section

# Include your existing functions, such as rename_file and other commands

# Start the Pyrogram Client
app.run()
