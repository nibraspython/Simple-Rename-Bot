import logging
from pyrogram.errors import BadRequest
from datetime import datetime

def getTime(seconds):
    """Convert seconds into HH:MM:SS format."""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def sizeUnit(size):
    """Convert size in bytes to a human-readable format."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024**2:
        return f"{size / 1024:.2f} KB"
    elif size < 1024**3:
        return f"{size / 1024**2:.2f} MB"
    else:
        return f"{size / 1024**3:.2f} GB"

async def status_bar(down_msg, speed, percentage, eta, done, left, engine, msg, is_time_over):
    """Update the status bar of a message with download progress."""
    bar_length = 12
    filled_length = int(percentage / 100 * bar_length)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    text = (
        f"\n╭「{bar}」 **»** __{percentage:.2f}%__\n├⚡️ **Speed »** __{speed}__\n├⚙️ **Engine »** __{engine}__"
        + f"\n├⏳ **Time Left »** __{eta}__"
        + f"\n├🍃 **Time Spent »** __{getTime((datetime.now() - BotTimes.start_time).seconds)}__"
        + f"\n├✅ **Processed »** __{done}__\n╰📦 **Total Size »** __{left}__"
    )
    try:
        if is_time_over():
            await msg.edit_text(
                text=down_msg + text,
                disable_web_page_preview=True,
                reply_markup=keyboard()
            )
    except BadRequest as e:
        logging.error(f"Same Status Not Modified: {str(e)}")
    except Exception as e:
        logging.error(f"Error Updating Status bar: {str(e)}")
