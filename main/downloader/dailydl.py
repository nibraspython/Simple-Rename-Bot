import os
import yt_dlp
from pyrogram import Client, filters
from moviepy.editor import VideoFileClip
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import humanbytes
import time

ydl_opts = {
    "format": "best",
    "noplaylist": False,
    "ignoreerrors": True,
    "geo_bypass": True,
    "restrictfilenames": True,
    "no_warnings": True,
    "quiet": True,
}

@Client.on_message(filters.private & filters.command("dailydl") & filters.user(ADMIN))
async def download_videos(bot, msg):
    reply = msg.reply_to_message
    if not reply or not reply.text:
        return await msg.reply_text("❗ Please reply to a message containing Dailymotion URLs.")
    
    urls = reply.text.strip().splitlines()
    total_urls = len(urls)
    if total_urls == 0:
        return await msg.reply_text("❗ No valid URLs found in the message.")
    
    for idx, url in enumerate(urls, 1):
        progress_message = await msg.reply_text(f"🔄 Processing URL {idx}/{total_urls}...\n\n🔗 {url}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                if not info_dict:
                    await progress_message.reply(f"❗ Unable to retrieve video info for URL {url}")
                    continue

                video_title = info_dict.get('title', 'Unknown Video')
                formats = info_dict.get('formats', [])
                highest_res_format = max(formats, key=lambda f: f.get('height', 0), default=None)

                if not highest_res_format:
                    await progress_message.reply(f"❗ No valid formats found for **{video_title}**.")
                    continue

                format_id = highest_res_format['format_id']
                file_size = humanbytes(highest_res_format.get('filesize', 0))
                resolution = f"{highest_res_format.get('height', 0)}p"

                await msg.reply(f"🎬 **{video_title}**\n\n📥 Downloading the highest resolution available...\n"
                                f"⚙️ **Resolution:** {resolution}\n📦 **Size:** {file_size}")

                ydl_opts.update({"format": format_id})
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=True)
                    file_path = ydl.prepare_filename(info_dict)

                    if not file_path or not os.path.exists(file_path):
                        await progress_message.reply(f"❗ File not found after download for **{video_title}**.")
                        continue

                    # Ensure valid extension
                    if not file_path.lower().endswith(('.mp4', '.mkv', '.webm', '.avi', '.mov')):
                        file_path += '.mp4'

                    # Move file to the DOWNLOAD_LOCATION
                    new_file_path = os.path.join(DOWNLOAD_LOCATION, os.path.basename(file_path))
                    os.rename(file_path, new_file_path)
                    file_path = new_file_path

            # Log file path to confirm
            await msg.reply(f"✅ Downloaded to: {file_path}")

            # Check if file exists before proceeding to upload
            if not os.path.exists(file_path):
                await msg.reply(f"❗ File not found for upload: {file_path}")
                continue

            # Process video for duration and thumbnail
            try:
                video_clip = VideoFileClip(file_path)
                duration = int(video_clip.duration)
                video_clip.close()
            except Exception as e:
                await msg.reply(f"❗ Error processing video file: {e}")
                continue

            # Generate thumbnail
            thumbnail = os.path.join(DOWNLOAD_LOCATION, f"{os.path.splitext(os.path.basename(file_path))[0]}_thumb.jpg")
            os.system(f"ffmpeg -i {file_path} -vf 'thumbnail,scale=320:180' -frames:v 1 \"{thumbnail}\"")

            # Confirm file is ready for upload
            await msg.reply(f"🚀 **Uploading Started** for **{video_title}**")
            c_time = time.time()

            try:
                await bot.send_video(
                    msg.chat.id,
                    video=file_path,
                    thumb=thumbnail if os.path.exists(thumbnail) else None,  # Only use thumbnail if it exists
                    duration=duration,
                    caption=f"**{video_title}**\n🕒 Duration: {duration} seconds\n⚙️ Resolution: {resolution}\n📦 Size: {file_size}",
                    progress=progress_message,
                    progress_args=(f"📤 Uploading...\n\n**{video_title}**...", progress_message, c_time)
                )
            except Exception as e:
                await msg.reply(f"❗ Error during file upload: {e}")
                continue

            # Clean up downloaded files after upload
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(thumbnail):
                os.remove(thumbnail)

        except yt_dlp.utils.DownloadError as e:
            await msg.reply(f"❗ yt-dlp error for URL {idx}/{total_urls}: {str(e)}")
        except Exception as e:
            await msg.reply(f"❗ Error for URL {idx}/{total_urls}: {e}")

    await msg.reply_text(f"✅ All {total_urls} URLs have been processed.")
