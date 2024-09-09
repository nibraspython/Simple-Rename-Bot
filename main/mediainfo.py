import os
from pyrogram import Client, filters
from config import ADMIN
import telegraph
from telegraph import upload_file
from pymediainfo import MediaInfo

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
    file_size = media.file_size
    
    # Initial message
    sts = await msg.reply_text(f"🔄 Processing your file: **{file_name}**...")

    # Get media info without downloading
    file_info = f"File Name: {file_name}\nFile Size: {file_size} bytes\n\n"

    try:
        media_info = MediaInfo.parse(media)
        for track in media_info.tracks:
            if track.track_type == "General":
                file_info += f"Format: {track.format}\nDuration: {track.duration / 1000:.2f} seconds\n\n"
            if track.track_type == "Video":
                file_info += (
                    f"Video:\nCodec: {track.codec_id}\n"
                    f"Resolution: {track.width}x{track.height}\n"
                    f"Frame Rate: {track.frame_rate} FPS\n\n"
                )
            if track.track_type == "Audio":
                file_info += (
                    f"Audio:\nCodec: {track.codec_id}\n"
                    f"Channels: {track.channel_s}\n"
                    f"Sampling Rate: {track.sampling_rate} Hz\n\n"
                )
    except Exception as e:
        return await sts.edit(f"Error generating media info: {e}")

    # Upload media info to Telegraph
    response = telegraph_client.create_page(
        title=file_name,
        html_content=file_info.replace("\n", "<br>")
    )

    telegraph_url = f"https://telegra.ph/{response['path']}"

    # Update the message with media info and Telegraph link
    await sts.edit(
        f"📄 **File Name:** {file_name}\n"
        f"💾 **File Size:** {file_size} bytes\n"
        f"🔗 **Media Info:** [Open Telegraph]({telegraph_url})\n\n"
        "✅ *Generated successfully!*",
        disable_web_page_preview=True
    )
