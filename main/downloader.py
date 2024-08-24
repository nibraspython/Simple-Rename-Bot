import time
import os
from pyrogram import Client, filters, enums
from main.utils import progress_message, humanbytes
from config import DOWNLOAD_LOCATION, ADMIN
from yt_dlp import YoutubeDL
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def ytdl_command(bot, msg):
    await msg.reply_text("🎥 Send your YouTube video links to download:")

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def ytdl_process(bot, msg):
    urls = msg.text.split()
    for url in urls:
        sts = await msg.reply_text("🔄 Gathering video info.....📥")
        try:
            with YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'Unknown Title')
                thumbnail_url = info.get('thumbnail', None)
                views = info.get('view_count', 0)
                likes = info.get('like_count', 0)
                formats = info.get('formats', [])
                keyboard = []

                for f in formats:
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none':  # Ensure the format has both video and audio
                        res = f.get('format_note', 'N/A')
                        size = f.get('filesize', None)
                        if size is None:
                            size = f.get('filesize_approx', 0)  # Use approximate filesize if actual size is not available
                        size = humanbytes(size)
                        button_text = f"📽 {res} - {size}"
                        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"{url}|{f['format_id']}")])

                # Ensure at least one resolution button is shown
                if not keyboard:
                    await sts.edit("No suitable formats found with both video and audio.")
                    return

                caption = (f"**{title}**\n"
                           f"👀 **Views**: {views}\n"
                           f"👍 **Likes**: {likes}\n"
                           f"📽 **Select your resolution below:**")

                await sts.delete()
                await bot.send_photo(
                    chat_id=msg.chat.id, 
                    photo=thumbnail_url, 
                    caption=caption, 
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            await sts.edit(f"Error: {e}")

@Client.on_callback_query(filters.regex(r'^https://www\.youtube\.com'))
async def ytdl_download(bot, query):
    url, format_id = query.data.split('|')
    sts = await query.message.reply_text("🔄 Downloading video.....📥")
    c_time = time.time()
    try:
        ydl_opts = {
            'format': format_id + '+bestaudio',  # Download video with best audio
            'outtmpl': f'{DOWNLOAD_LOCATION}/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            title = info.get('title', 'Unknown Title')
            filesize = info.get('filesize_approx', 0) or 0  # Use filesize_approx for more reliable size
            filesize = humanbytes(filesize)
            duration = info.get('duration', 0) or 0

        # Download the thumbnail
        thumbnail = f"{DOWNLOAD_LOCATION}/{title}.jpg"
        await bot.download_media(info['thumbnail'], file_name=thumbnail)

        # Prepare caption
        caption = f"{title}\n\n💽 size: {filesize}\n🕒 duration: {int(duration)} seconds"
        await sts.edit("🚀 Uploading started..... 📤 Thanks To All Who Supported ❤")
        c_time = time.time()

        await bot.send_video(
            query.message.chat.id,
            video=file_path,
            thumb=thumbnail,
            caption=caption,
            duration=int(duration),
            progress=progress_message,
            progress_args=("Upload Started..... Thanks To All Who Supported ❤", sts, c_time)
        )
    except Exception as e:
        await sts.edit(f"Error: {e}")
    finally:
        try:
            os.remove(file_path)
            os.remove(thumbnail)
        except Exception as e:
            print(f"Error deleting files: {e}")
        await sts.delete()
