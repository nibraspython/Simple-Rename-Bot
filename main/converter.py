import time
import os
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

# Dictionary to keep track of user states
user_states = {}

# Function to download file from a URL
def download_file(url, file_name, progress, progress_args):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(file_name, 'wb') as f:
            total_length = int(r.headers.get('content-length', 0))
            downloaded = 0
            start_time = time.time()
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress:
                        progress(downloaded, total_length, *progress_args, start_time=start_time)
    return file_name

# Only handle messages with the "/convert" command and from the authorized user
@Client.on_message(filters.private & filters.command("convert") & filters.user(ADMIN))
async def convert_to_mp3(bot, msg):
    user_id = msg.from_user.id
    user_states[user_id] = "awaiting_selection"
    
    # Create the inline keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Direct Link", callback_data="direct_link")],
        [InlineKeyboardButton("📹 Video", callback_data="video")]
    ])
    
    await msg.reply_text("Please choose an option:", reply_markup=keyboard)

# Handle callback queries from the inline keyboard
@Client.on_callback_query(filters.user(ADMIN))
async def handle_callback(bot, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if user_id not in user_states or user_states[user_id] != "awaiting_selection":
        return
    
    if data == "direct_link":
        user_states[user_id] = "awaiting_link"
        await callback_query.message.edit_text("Please send the direct link to the MP4 video. 📎")
    elif data == "video":
        user_states[user_id] = "awaiting_video"
        await callback_query.message.edit_text("Please send the video you want to convert to MP3. 📹")

# Handle media messages or text links after the "/convert" command
@Client.on_message(filters.private & (filters.video | filters.document | filters.text) & filters.user(ADMIN))
async def handle_conversion(bot, msg):
    user_id = msg.from_user.id

    # Check if the user is in the right state
    if user_id not in user_states:
        return

    state = user_states[user_id]
    if state == "awaiting_link":
        media_link = msg.text if msg.text and msg.text.startswith("http") else None
        if not media_link:
            return await msg.reply_text("Please provide a valid direct link to an MP4 video.")
        media = media_link
    elif state == "awaiting_video":
        media = msg.video or msg.document if isinstance(msg, Message) else None
        if not media or (media.document and media.document.mime_type != 'video/mp4'):
            return await msg.reply_text("Please send a valid video file.")
    else:
        return

    new_name = "converted_audio.mp3"
    sts = await msg.reply_text("Trying to Download! 📥")

    c_time = time.time()

    # Download the media if it's a message
    if state == "awaiting_video":
        downloaded = await bot.download_media(media, file_name=new_name, progress=progress_message, progress_args=("Download Started..... 😅", sts, c_time))
    # Otherwise, download the file directly from the link
    else:
        downloaded = download_file(media, file_name=new_name, progress=progress_message, progress_args=("Download Started..... 😅", sts, c_time))

    filesize = humanbytes(os.path.getsize(downloaded))

    # Get video duration
    try:
        video_clip = VideoFileClip(downloaded)
        duration = int(video_clip.duration)
    except Exception as e:
        await sts.edit(f"Error reading video file: {e}")
        if downloaded:
            os.remove(downloaded)
        return

    # Convert the video to MP3
    await sts.edit("Converting to MP3...")
    try:
        audio_path = f'{DOWNLOAD_LOCATION}/{new_name}'
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()
    except Exception as e:
        return await sts.edit(f"Error: {e}")

    # Remove the downloaded video
    if downloaded:
        os.remove(downloaded)

    cap = f"🎵 {new_name} \n💽 Size: {filesize} \n🕒 Duration: {duration} seconds"

    # Upload the converted MP3
    await sts.edit("Uploading...")
    c_time = time.time()
    try:
        await bot.send_audio(msg.chat.id, audio=audio_path, caption=cap, duration=duration, progress=progress_message, progress_args=("Upload Started..... 😅", sts, c_time))
    except Exception as e:
        return await sts.edit(f"Error: {e}")
    await sts.delete()

    # Reset user state
    user_states.pop(user_id, None)
