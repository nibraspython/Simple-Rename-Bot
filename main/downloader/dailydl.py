import time, os
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes
from yt_dlp import YoutubeDL

# Dailymotion Download Function
def download_dailymotion(url):
    ydl_opts = {
        'format': 'best',  # download the best quality
        'outtmpl': f'{DOWNLOAD_LOCATION}/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        return file_path, info.get('title'), info.get('duration', 0), info.get('filesize', 0)

@Client.on_message(filters.private & filters.command("dailydl") & filters.user(ADMIN))
async def dailymotion_download(bot, msg):
    reply = msg.reply_to_message
    if not reply or not reply.text:
        return await msg.reply_text("Please reply to a message containing one or more Dailymotion URLs.")
    
    urls = reply.text.split()  # Split the message to extract multiple URLs
    if not urls:
        return await msg.reply_text("Please provide valid Dailymotion URLs.")

    # Iterate over each URL
    for url in urls:
        try:
            # Display processing message
            sts = await msg.reply_text(f"🔄 Processing your request for {url}...")

            # Start downloading the video
            c_time = time.time()
            downloaded, video_title, duration, file_size = download_dailymotion(url)
            human_size = humanbytes(file_size)
            
            await sts.edit(f"📥 Downloading: {video_title}\nResolution: Highest\n💽 Size: {human_size}")
            
            # Download complete message
            await sts.edit("✅ Download Completed! 📥")
            
            # Thumbnail Handling (Check if the message contains video or document and extract thumbnail)
            thumbnail = None
            if reply.video and reply.video.thumbs:
                thumbnail = await bot.download_media(reply.video.thumbs[0].file_id)
            elif reply.document and reply.document.thumbs:
                thumbnail = await bot.download_media(reply.document.thumbs[0].file_id)
            
            # Prepare the caption with emojis
            cap = f"🎬 **{video_title}**\n\n💽 Size: {human_size}\n🕒 Duration: {duration // 60} mins {duration % 60} secs"
            
            # Upload to Telegram
            await sts.edit(f"🚀 Uploading: {video_title} 📤")
            c_time = time.time()
            
            await bot.send_video(
                msg.chat.id,
                video=downloaded,
                thumb=thumbnail,
                caption=cap,
                duration=duration,
                progress=progress_message,
                progress_args=(f"🚀 Uploading {video_title}... 📤", sts, c_time),
            )
            
            # Remove downloaded files
            os.remove(downloaded)
            if thumbnail:
                os.remove(thumbnail)
                
            await sts.edit(f"✅ Successfully uploaded: {video_title}")

        except Exception as e:
            await msg.reply_text(f"❌ Failed to process {url}. Error: {str(e)}")

    # All URLs processed
    await msg.reply_text("🎉 All URLs processed successfully!")
