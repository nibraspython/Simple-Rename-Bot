import time, os
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes
from moviepy.editor import VideoFileClip

upload_progress = {}

@Client.on_message(filters.private & filters.command("rename") & filters.user(ADMIN))
async def rename_file(bot, msg):
    reply = msg.reply_to_message
    if len(msg.command) < 2 or not reply:
        return await msg.reply_text("Please Reply To A File or video or audio with filename + .extension e.g., (.mkv or .mp4 or .zip)")
    
    media = reply.document or reply.audio or reply.video
    if not media:
        return await msg.reply_text("Please Reply To A File or video or audio with filename + .extension e.g., (.mkv or .mp4 or .zip)")
    
    og_media = getattr(reply, reply.media.value)
    new_name = msg.text.split(" ", 1)[1]
    sts = await msg.reply_text("🔄 Trying to Download.....📥")
    c_time = time.time()
    downloaded = await reply.download(file_name=new_name, progress=progress_message, progress_args=("Download Started..... **Thanks To All Who Supported ❤**", sts, c_time))
    filesize = humanbytes(og_media.file_size)

    # Get video duration
    video_clip = VideoFileClip(downloaded)
    duration = int(video_clip.duration)
    video_clip.close()

    if CAPTION:
        try:
            cap = CAPTION.format(file_name=new_name, file_size=filesize, duration=duration)
        except Exception as e:
            return await sts.edit(text=f"Your caption Error: unexpected keyword ●> ({e})")
    else:
        cap = f"{new_name}\n\n💽 size: {filesize}\n🕒 duration: {duration} seconds"

    dir = os.listdir(DOWNLOAD_LOCATION)
    if len(dir) == 0:
        file_thumb = await bot.download_media(og_media.thumbs[0].file_id)
        og_thumbnail = file_thumb
    else:
        try:
            og_thumbnail = f"{DOWNLOAD_LOCATION}/thumbnail.jpg"
        except Exception as e:
            print(e)
            og_thumbnail = None

    # Create inline keyboard with a progress button
    progress_key = f"progress_{msg.message_id}"
    upload_progress[progress_key] = {
        "total_size": og_media.file_size,
        "uploaded_size": 0,
        "completed": 0,
        "tasks": 1  # You can track multiple tasks if needed
    }
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Show Progress", callback_data=progress_key)]
    ])

    await sts.edit("🚀 Uploading started..... 📤**Thanks To All Who Supported ❤**", reply_markup=keyboard)
    c_time = time.time()
    
    try:
        await bot.send_video(
            msg.chat.id, 
            video=downloaded, 
            thumb=og_thumbnail, 
            caption=cap, 
            duration=duration, 
            progress=upload_progress_message, 
            progress_args=(sts, c_time, progress_key)
        )
    except Exception as e:
        return await sts.edit(f"Error: {e}")

    # Once the upload is complete, remove the progress data
    upload_progress.pop(progress_key, None)

async def upload_progress_message(current, total, msg, start_time, progress_key):
    if progress_key in upload_progress:
        upload_progress[progress_key]["uploaded_size"] = current
        upload_progress[progress_key]["completed"] = (current / total) * 100
    await progress_message(current, total, msg, start_time)

@Client.on_callback_query(filters.regex(r"^progress_"))
async def progress_callback(bot, query: CallbackQuery):
    progress_key = query.data
    if progress_key in upload_progress:
        progress_data = upload_progress[progress_key]
        total_size = humanbytes(progress_data["total_size"])
        uploaded_size = humanbytes(progress_data["uploaded_size"])
        completed = progress_data["completed"]
        tasks = progress_data["tasks"]
        
        await query.answer(
            f"Total: {total_size}\nUploaded: {uploaded_size}\nCompleted: {completed:.2f}%\nTasks: {tasks}",
            show_alert=True
        )
    else:
        await query.answer("No progress data available", show_alert=True)
