import os
import time
from pyrogram import Client, filters
from pymediainfo import MediaInfo
from config import ADMIN, DOWNLOAD_LOCATION
from main.utils import progress_message, humanbytes

@Client.on_message(filters.private & filters.command("mediainfo") & filters.user(ADMIN))
async def media_info(bot, msg):
    reply = msg.reply_to_message
    if not reply:
        return await msg.reply_text("Please reply to a file or media message to get media information.")
    
    media = reply.document or reply.audio or reply.video
    if not media:
        return await msg.reply_text("Please reply to a file or media message to get media information.")

    sts = await msg.reply_text("🔄 Trying to Download... 📥")
    c_time = time.time()
    downloaded_file = await reply.download(
        progress=progress_message,
        progress_args=("⬇️ Downloading...", sts, c_time)
    )

    try:
        media_info = MediaInfo.parse(downloaded_file)
        info_text = "<b>Media Information:</b>\n\n"
        for track in media_info.tracks:
            for key, value in track.to_data().items():
                info_text += f"<b>{key}:</b> {value}\n"

        await msg.reply_text(info_text, parse_mode="html")
    except Exception as e:
        await msg.reply_text(f"❌ Error generating media information: {e}")
    finally:
        os.remove(downloaded_file)
        await sts.delete()
