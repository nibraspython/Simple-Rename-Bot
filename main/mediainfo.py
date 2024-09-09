import os
import time
from pyrogram import Client, filters
from config import ADMIN, DOWNLOAD_LOCATION
from pymediainfo import MediaInfo
from main.utils import progress_message, humanbytes
import telegraph

telegraph_client = telegraph.Telegraph()
telegraph_client.create_account(short_name="InfoBot")

@Client.on_message(filters.private & filters.command("info") & filters.user(ADMIN))
async def generate_mediainfo(bot, msg):
    reply = msg.reply_to_message
    if not reply:
        return await msg.reply_text("Please reply to a file (video, audio, or document) with the /info command.")
    
    media = reply.document or reply.audio or reply.video
    if not media:
        return await msg.reply_text("Please reply to a file (video, audio, or document) with the /info command.")
    
    file_name = media.file_name
    
    # Initial processing message
    sts = await msg.reply_text(f"🔄 Processing your file...\n\n📂 **{file_name}**")
    
    # Start downloading the file
    c_time = time.time()
    downloaded_file_path = await reply.download(
        file_name=file_name,
        progress=progress_message,
        progress_args=("📥 Downloading...\n\n📂 **{file_name}**.", sts, c_time)
    )
    
    if not downloaded_file_path:
        return await sts.edit("❌ Failed to download the file.")
    
    # Generate media info using pymediainfo
    try:
        media_info = MediaInfo.parse(downloaded_file_path)
    except Exception as e:
        return await sts.edit(f"❌ Error generating media info: {e}")

    # Format the media info for Telegraph
    media_info_text = ""
    for track in media_info.tracks:
        media_info_text += f"**Track Type:** {track.track_type}\n"
        for key, value in track.to_data().items():
            media_info_text += f"**{key.replace('_', ' ').capitalize()}:** {value}\n"
        media_info_text += "\n"

    # Post the gathered info to Telegraph
    try:
        response = telegraph_client.create_page(
            title=file_name,
            html_content=media_info_text.replace("\n", "<br>")
        )
        telegraph_url = f"https://telegra.ph/{response['path']}"
    except Exception as e:
        return await sts.edit(f"Error generating Telegraph page: {e}")

    # Update message with the info and Telegraph link
    await sts.edit(
        f"📄 **File Name:** {file_name}\n"
        f"💾 **File Size:** {humanbytes(media.file_size)}\n"
        f"🔗 **Media Info:** [Open Telegraph]({telegraph_url})\n\n"
        "✅ *Generated successfully!*",
        disable_web_page_preview=True
    )
    
    # Clean up the downloaded file
    try:
        os.remove(downloaded_file_path)
    except Exception as e:
        print(f"Error removing file: {e}")
