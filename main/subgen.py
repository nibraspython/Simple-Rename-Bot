import time, os
from pyrogram import Client, filters, types
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message
import whisper
from googletrans import Translator

# Dictionary to store the original video and subtitle messages per user
user_video_messages = {}
user_subtitle_messages = {}

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
        # Load Whisper model
        print("Loading Whisper model...")
        model = whisper.load_model("base")
        
        # Transcribe video
        print(f"Transcribing video {video_path} with language {'Hindi' if lang == 'hindi' else 'English'}")
        result = model.transcribe(video_path, language="hi" if lang == "hindi" else "en")

        srt_path = f"{video_path.rsplit('.', 1)[0]}.srt"
        with open(srt_path, "w") as srt_file:
            for segment in result['segments']:
                srt_file.write(f"{segment['id']}\n")
                srt_file.write(f"{segment['start']} --> {segment['end']}\n")
                srt_file.write(f"{segment['text']}\n\n")

        await query.message.edit_text("🚀 Uploading subtitles...📤")
        c_time = time.time()
        await bot.send_document(query.message.chat.id, document=srt_path, caption="🎉 Subtitles generated!", progress=progress_message, progress_args=("Upload Started..... Thanks To All Who Supported ❤", query.message, c_time), reply_markup=types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("🌐 Translate", callback_data="translate_subtitles")]
        ]))

        # Store the subtitle file path and user ID for future translation
        user_subtitle_messages[query.from_user.id] = srt_path

    except Exception as e:
        print(f"Error during subtitle generation: {e}")
        await query.message.edit_text(f"❌ Error during subtitle generation: {e}")

    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        user_video_messages.pop(query.from_user.id, None)

@Client.on_callback_query(filters.regex("translate_subtitles") & filters.user(ADMIN))
async def ask_translation_language(bot, query):
    await query.message.edit_text(
        "🌍 Select the language to translate the subtitles:",
        reply_markup=types.InlineKeyboardMarkup([
            [types.InlineKeyboardButton("🇱🇰 Sinhala", callback_data="sinhala_translate")],
            [types.InlineKeyboardButton("🇬🇧 English", callback_data="english_translate")]
        ])
    )

@Client.on_callback_query(filters.regex(r"sinhala_translate|english_translate") & filters.user(ADMIN))
async def translate_subtitles(bot, query):
    lang = "si" if "sinhala" in query.data else "en"
    subtitle_path = user_subtitle_messages.get(query.from_user.id)

    if not subtitle_path:
        return await query.message.edit_text("❌ Error: Could not find the subtitles file. Please try again.")

    await query.message.edit_text(f"🔄 Translating subtitles to {'Sinhala' if lang == 'si' else 'English'}...")

    try:
        # Load the translator
        translator = Translator()

        # Read the original subtitles
        with open(subtitle_path, "r") as srt_file:
            original_text = srt_file.read()

        # Translate the text
        translated_text = translator.translate(original_text, dest=lang).text

        translated_srt_path = f"{subtitle_path.rsplit('.', 1)[0]}_{lang}.srt"
        with open(translated_srt_path, "w") as srt_file:
            srt_file.write(translated_text)

        await query.message.edit_text("🚀 Uploading translated subtitles...📤")
        c_time = time.time()
        await bot.send_document(query.message.chat.id, document=translated_srt_path, caption=f"🎉 Subtitles translated to {'Sinhala' if lang == 'si' else 'English'}!", progress=progress_message, progress_args=("Upload Started..... Thanks To All Who Supported ❤", query.message, c_time))

    except Exception as e:
        print(f"Error during subtitle translation: {e}")
        await query.message.edit_text(f"❌ Error during subtitle translation: {e}")

    finally:
        if os.path.exists(translated_srt_path):
            os.remove(translated_srt_path)
        user_subtitle_messages.pop(query.from_user.id, None)

        # Log completion of the process
        print("Subtitle translation process completed.")
