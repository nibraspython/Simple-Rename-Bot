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
    sts = await msg.reply_text(f"🔄 Processing your file: <b>{file_name}</b>...")
    
    # Start downloading the file
    c_time = time.time()
    downloaded_file_path = await reply.download(
        file_name=file_name,
        progress=progress_message,
        progress_args=("📥 Downloading...", sts, c_time)
    )
    
    if not downloaded_file_path:
        return await sts.edit("❌ Failed to download the file.")
    
    # Generate media info using pymediainfo
    try:
        media_info = MediaInfo.parse(downloaded_file_path)
    except Exception as e:
        return await sts.edit(f"❌ Error generating media info: {e}")

    # Format the media info for Telegraph
    general_info = "<b>General Information:</b><br>"
    video_info = "<b>Video Information:</b><br>"
    audio_info = "<b>Audio Information:</b><br>"

    for track in media_info.tracks:
        if track.track_type == "General":
            general_info += f"<b>File Name:</b> {file_name}<br>"
            general_info += f"<b>File Size:</b> {humanbytes(media.file_size)}<br>"
            for key, value in track.to_data().items():
                general_info += f"<b>{key.replace('_', ' ').capitalize()}:</b> {value}<br>"
        elif track.track_type == "Video":
            video_info += "<b>Video Track:</b><br>"
            for key, value in track.to_data().items():
                video_info += f"<b>{key.replace('_', ' ').capitalize()}:</b> {value}<br>"
        elif track.track_type == "Audio":
            audio_info += "<b>Audio Track:</b><br>"
            for key, value in track.to_data().items():
                audio_info += f"<b>{key.replace('_', ' ').capitalize()}:</b> {value}<br>"

    # Combine all sections
    content = f"<b>{file_name}</b><br><br>"
    content += general_info + "<br>"
    if video_info.strip():
        content += video_info + "<br>"
    if audio_info.strip():
        content += audio_info + "<br>"

    # Post the gathered info to Telegraph
    try:
        response = telegraph_client.create_page(
            title=file_name,
            html_content=content
        )
        telegraph_url = f"https://telegra.ph/{response['path']}"
    except Exception as e:
        return await sts.edit(f"❌ Error generating Telegraph page: {e}")

    # Update message with the final info and Telegraph link
    final_text = (
        f"📄 <b>File Name:</b> {file_name}<br>"
        f"💾 <b>File Size:</b> {humanbytes(media.file_size)}<br>"
        f"🔗 <b>Media Info:</b> <a href='{telegraph_url}'>Open Telegraph</a><br><br>"
        "✅ <b>Generated successfully!</b>"
    )

    await sts.edit(final_text, disable_web_page_preview=True)
    
    # Clean up the downloaded file
    try:
        os.remove(downloaded_file_path)
    except Exception as e:
        print(f"Error removing file: {e}")
