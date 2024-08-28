from pyrogram import Client, filters
from config import ADMIN

SECTION_NAME_FILE = "/content/section_name.txt"

@Client.on_message(filters.private & filters.command("next") & filters.user(ADMIN))
async def prompt_for_section(bot, msg):
    await msg.reply_text("Send the name of the section to run (e.g., 'Section 1').")
@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def handle_section_name(bot, msg):
    section_name = msg.text.strip()
    if section_name:
        with open(SECTION_NAME_FILE, "w") as f:
            f.write(section_name)
        await msg.reply_text(f"Section '{section_name}' set to run.")
    else:
        await msg.reply_text("Please provide a valid section name.")
