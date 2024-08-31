import shutil
import os
from pyrogram import Client, filters
from config import ADMIN
from IPython.display import display, Javascript
from IPython import get_ipython

# Paths
ARCHIVE_EXTRACTOR_PATH = "/content/Simple-Rename-Bot/main/archive_extractor.py"
MOVE_TO_PATH = "/content/archive_extractor.py"

@Client.on_message(filters.private & filters.command("remove") & filters.user(ADMIN))
async def remove_archive_extractor(bot, msg):
    # Move archive_extractor.py to a different location
    if os.path.exists(ARCHIVE_EXTRACTOR_PATH):
        shutil.move(ARCHIVE_EXTRACTOR_PATH, MOVE_TO_PATH)
        await msg.reply_text("📁 `archive_extractor.py` has been moved to /content/.")

        # Stop the current running cell
        await stop_and_rerun()

@Client.on_message(filters.private & filters.command("enter") & filters.user(ADMIN))
async def enter_archive_extractor(bot, msg):
    # Move archive_extractor.py back to its original location
    if os.path.exists(MOVE_TO_PATH):
        shutil.move(MOVE_TO_PATH, ARCHIVE_EXTRACTOR_PATH)
        await msg.reply_text("📁 `archive_extractor.py` has been moved back to /content/Simple-Rename-Bot/main/.")

        # Stop the current running cell
        await stop_and_rerun()

async def stop_and_rerun():
    # Stop the current cell and trigger a rerun
    display(Javascript('IPython.notebook.kernel.restart();'))

    # Alternatively, you can raise SystemExit to stop the current cell
    # raise SystemExit("Stopping current cell to rerun.")

    # If you're not in Colab, use the following to exit the script:
    # os._exit(0)
