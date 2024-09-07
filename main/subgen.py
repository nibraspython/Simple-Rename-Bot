import time, os
from pyrogram import Client, filters, types
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message
from moviepy.editor import VideoFileClip
import whisper

# Dictionary to store the original video message per user
user_video_messages = {}

@Client.on_message(filters.private & filters.command("subgen") & filters.user(ADMIN))
async def generate_subtitles(bot, msg):
    await msg.reply_text("🎥 Please send the video for which you want to generate subtitles.")

@Client.on_message(filters.private & filters.video & filters.user(ADMIN))
async def receive_video(bot, video_msg):
    # Store the received video message in the dictionary using the user's ID as the key
    user_video_messages[video_msg.from_user.id] = video_msg

    await video_msg.reply_text(
        "🎬 Video received! Now, please select the language for subtitle generation.",
        reply_markup=types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("🇮🇳 Hindi", callback_data="hindi")],
            [types.InlineKeyboardButton("🇬🇧 English", callback_data="english")]
        ])
    )

@Client.on_callback_query(filters.regex(r"hindi|english") & filters.user(ADMIN))
async def on_language_selected(bot, query):
    # Retrieve the original video message using the user's ID
    video_msg = user_video_messages.get(query.from_user.id)

    if not video_msg:
        return await query.message.edit_text("❌ Error: Could not find the video. Please try again.")

    lang = query.data
    await query.message.edit_text("🔄 Downloading video...📥")
    media = video_msg.video
    c_time = time.time()
    video_path = await video_msg.download(file_name=f"{DOWNLOAD_LOCATION}/{media.file_name}", progress=progress_message, progress_args=("Download Started..... Thanks To All Who Supported ❤", query.message, c_time))
    await query.message.edit_text("✅ Download completed! Now generating subtitles...")

    try:
        # Use Whisper correctly to transcribe the video
        model = whisper.load_model("base")
        result = model.transcribe(video_path, language="hi" if lang == "hindi" else "en")
        srt_path = f"{video_path.rsplit('.', 1)[0]}.srt"
        with open(srt_path, "w") as srt_file:
            for segment in result['segments']:
                srt_file.write(f"{segment['id']}\n")
                srt_file.write(f"{segment['start']} --> {segment['end']}\n")
                srt_file.write(f"{segment['text']}\n\n")

        await query.message.edit_text("🚀 Uploading subtitles...📤")
        c_time = time.time()
        await bot.send_document(query.message.chat.id, document=srt_path, caption="🎉 Subtitles generated!", progress=progress_message, progress_args=("Upload Started..... Thanks To All Who Supported ❤", query.message, c_time))

    except Exception as e:
        await query.message.edit_text(f"❌ Error during subtitle generation: {e}")

    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(srt_path):
            os.remove(srt_path)
        # Remove the video message from the dictionary after processing
        user_video_messages.pop(query.from_user.id, None)
