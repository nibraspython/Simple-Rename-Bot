import time, os, yt_dlp
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from moviepy.editor import VideoFileClip

ydl_opts = {"format": "best", "noplaylist": True}

@Client.on_message(filters.private & filters.command("dailydl") & filters.user(ADMIN))
async def download_videos(bot, msg):
    reply = msg.reply_to_message
    if not reply or not reply.text:
        return await msg.reply_text("Please reply to a message containing URLs of videos to download.")

    urls = reply.text.splitlines()
    
    for url in urls:
        sts = await msg.reply_text("🔄 Processing your request...")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                video_title = info_dict.get('title', 'Unknown Video')
                formats = info_dict.get('formats', [])

                # Create InlineKeyboard buttons for available resolutions
                buttons = []
                for f in formats:
                    res = f.get('format_note')
                    size = humanbytes(f.get('filesize', 0))
                    if res and size:
                        buttons.append([InlineKeyboardButton(f"{res} - {size}", callback_data=f"{url}|{f['format_id']}")])

                # Show resolution options
                await sts.edit(f"🎬 {video_title}\nSelect a resolution to download:", reply_markup=InlineKeyboardMarkup(buttons))

        except Exception as e:
            await sts.edit(f"Error: {e}")
            continue

@Client.on_callback_query()
async def button(bot, query):
    data = query.data.split("|")
    url, format_id = data[0], data[1]
    
    sts = await query.message.edit(f"🔄 Downloading your video...")
    
    try:
        ydl_opts.update({"format": format_id})
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info_dict)
            video_title = info_dict.get('title', 'Unknown Video')

        # Get thumbnail and duration
        video_clip = VideoFileClip(file_path)
        duration = int(video_clip.duration)
        video_clip.close()

        # Auto-generate thumbnail
        thumbnail = f"{DOWNLOAD_LOCATION}/{video_title}_thumb.jpg"
        os.system(f"ffmpeg -i {file_path} -vf 'thumbnail,scale=320:180' -frames:v 1 {thumbnail}")

        await sts.edit(f"🚀 Uploading {video_title}...")
        c_time = time.time()

        await bot.send_video(
            query.message.chat.id,
            video=file_path,
            thumb=thumbnail,
            caption=f"{video_title}\n🕒 Duration: {duration} seconds",
            progress=progress_message,
            progress_args=(f"Uploading {video_title}...", sts, c_time)
        )

        os.remove(file_path)
        os.remove(thumbnail)

    except Exception as e:
        await sts.edit(f"Error during download or upload: {e}")
        return

    await sts.delete()

