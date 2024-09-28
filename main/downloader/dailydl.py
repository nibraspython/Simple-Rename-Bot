import time, os, yt_dlp
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from moviepy.editor import VideoFileClip

ydl_opts = {
    "format": "best",  # Automatically choose the best available format
    "noplaylist": False,  # Allow playlists or multi-format extraction
    "ignoreerrors": True,  # Continue processing even if errors occur
    "geo_bypass": True,  # Bypass geo-restricted sites
    "restrictfilenames": True,  # Avoid special characters in filenames
    "no_warnings": True,  # Hide non-critical warnings
    "quiet": True,  # Suppress output except for errors
}

@Client.on_message(filters.private & filters.command("dailydl") & filters.user(ADMIN))
async def download_videos(bot, msg):
    reply = msg.reply_to_message
    if not reply or not reply.text:
        return await msg.reply_text("Please reply to a message containing a Dailymotion URL.")

    url = reply.text.strip()

    sts = await msg.reply_text("🔄 Processing your request...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_title = info_dict.get('title', 'Unknown Video')
            formats = info_dict.get('formats', [])

            # Sort formats by resolution (height) and select the highest available
            highest_res_format = max(formats, key=lambda f: f.get('height', 0), default=None)

            if not highest_res_format:
                await sts.edit(f"No valid formats found for {video_title}.")
                return

            format_id = highest_res_format['format_id']
            await sts.edit(f"🎬 {video_title}\nDownloading the highest resolution available...")

            # Update yt-dlp options to download the selected format
            ydl_opts.update({"format": format_id})
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info_dict)

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
            msg.chat.id,
            video=file_path,
            thumb=thumbnail,
            caption=f"{video_title}\n🕒 Duration: {duration} seconds",
            progress=progress_message,
            progress_args=(f"Uploading {video_title}...", sts, c_time)
        )

        # Cleanup
        os.remove(file_path)
        os.remove(thumbnail)

    except yt_dlp.utils.DownloadError as e:
        await sts.edit(f"yt-dlp error: {str(e)}")
    except Exception as e:
        await sts.edit(f"Error: {e}")
