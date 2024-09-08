import os
import wave
import json
import time
from pyrogram import Client, filters, types
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message
from vosk import Model, KaldiRecognizer

# Dictionary to store the original video message per user
user_video_messages = {}

# Load Vosk model (adjust the path to your model directory)
model_path = "model-en"  # Adjust this for Hindi: "model-hi"
model = Model(model_path)

@Client.on_message(filters.private & filters.command("subgen") & filters.user(ADMIN))
async def generate_subtitles(bot, msg):
    await msg.reply_text("🎥 Please send the video for which you want to generate subtitles.")

@Client.on_message(filters.private & filters.video & filters.user(ADMIN))
async def receive_video(bot, video_msg):
    # Store the received video message in the dictionary using the user's ID as the key
    user_video_messages[video_msg.from_user.id] = video_msg

    await video_msg.reply_text(
        "🎬 Video received! Now, please select the language for subtitle generation.",
        reply_markup=types.inlineKeyboardMarkup([
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
        # Extract audio from video for Vosk transcription
        audio_path = f"{video_path.rsplit('.', 1)[0]}.wav"
        os.system(f"ffmpeg -i {video_path} -ar 16000 -ac 1 -f wav {audio_path}")

        # Transcribe the audio using Vosk
        transcript = transcribe_audio_vosk(audio_path)

        # Save the transcript as an SRT file
        srt_path = f"{video_path.rsplit('.', 1)[0]}.srt"
        with open(srt_path, "w") as srt_file:
            srt_file.write(transcript)

        await query.message.edit_text("🚀 Uploading subtitles...📤")
        c_time = time.time()
        await bot.send_document(query.message.chat.id, document=srt_path, caption="🎉 Subtitles generated!", progress=progress_message, progress_args=("Upload Started..... Thanks To All Who Supported ❤", query.message, c_time))

    except Exception as e:
        # Log the error
        print(f"Error during subtitle generation: {e}")
        await query.message.edit_text(f"❌ Error during subtitle generation: {e}")

    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(srt_path):
            os.remove(srt_path)
        # Remove the video message from the dictionary after processing
        user_video_messages.pop(query.from_user.id, None)

        # Log completion of the process
        print("Subtitle generation process completed.")

def transcribe_audio_vosk(audio_path):
    wf = wave.open(audio_path, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
        raise ValueError("Audio file must be WAV format mono PCM with a 16kHz sample rate.")

    recognizer = KaldiRecognizer(model, wf.getframerate())
    recognizer.SetWords(True)
    transcript = ""
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            transcript += format_srt_segment(result)
        else:
            partial_result = json.loads(recognizer.PartialResult())
            transcript += partial_result.get("partial", "") + "\n"
    
    final_result = json.loads(recognizer.FinalResult())
    transcript += format_srt_segment(final_result)
    return transcript

def format_srt_segment(segment):
    start_time = segment['result'][0]['start']
    end_time = segment['result'][-1]['end']
    text = segment['text']
    srt_segment = f"{start_time}\n{start_time:.3f} --> {end_time:.3f}\n{text}\n\n"
    return srt_segment
