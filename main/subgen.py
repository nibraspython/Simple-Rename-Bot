import time, os
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message
from moviepy.editor import VideoFileClip
import whisper

@Client.on_message(filters.private & filters.command("subgen") & filters.user(ADMIN))
async def generate_subtitles(bot, msg):
    await msg.reply_text("🎥 Please send the video for which you want to generate subtitles.")

    @Client.on_message(filters.private & filters.video & filters.user(ADMIN))
    async def receive_video(bot, video_msg):
        await video_msg.reply_text(
            "🎬 Video received! Now, please select the language for subtitle generation.",
            reply_markup=enums.InlineKeyboardMarkup([
                [enums.InlineKeyboardButton("🇮🇳 Hindi", callback_data="hindi")],
                [enums.InlineKeyboardButton("🇬🇧 English", callback_data="english")]
            ])
        )

    @Client.on_callback_query(filters.regex(r"hindi|english") & filters.user(ADMIN))
    async def on_language_selected(bot, query):
        lang = query.data
        await query.message.edit_text("🔄 Downloading video...📥")
        video_msg = query.message.reply_to_message
        media = video_msg.video
        c_time = time.time()
        video_path = await video_msg.download(file_name=f"{DOWNLOAD_LOCATION}/{media.file_name}", progress=progress_message, progress_args=("Download Started..... Thanks To All Who Supported ❤", query.message, c_time))
        await query.message.edit_text("✅ Download completed! Now generating subtitles...")

        try:
            model = whisper.load_model("base")
            result = model.transcribe(video_path, language="hi" if lang == "hindi" else "en")
            srt_path = f"{video_path.rsplit('.', 1)[0]}.srt"
            with open(srt_path, "w") as srt_file:
                srt_file.write(result['subtitles'])

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
