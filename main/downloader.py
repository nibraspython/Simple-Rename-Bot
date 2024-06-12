import logging
import yt_dlp
from asyncio import sleep
from threading import Thread
from os import makedirs, path as ospath, remove
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_LOCATION, ADMIN
from main.utils import progress_message, humanbytes, getTime

class YTDLProgress:
    def __init__(self):
        self.header = ""
        self.speed = ""
        self.percentage = 0.0
        self.eta = ""
        self.done = ""
        self.left = ""

YTDL = YTDLProgress()

async def YTDL_Status(link, num, message):
    global YTDL
    name = await get_YT_Name(link)
    header = f"<b>📥 DOWNLOADING FROM » </b><i>🔗Link {str(num).zfill(2)}</i>\n\n<code>{name}</code>\n"

    YTDL_Thread = Thread(target=YouTubeDL, name="YouTubeDL", args=(link,))
    YTDL_Thread.start()

    while YTDL_Thread.is_alive():
        if YTDL.header:
            try:
                await message.edit_text(text=header + YTDL.header)
            except Exception:
                pass
        else:
            try:
                await message.edit_text(
                    text=header +
                         f"\n⬇️ **Download Progress:** {YTDL.percentage}%\n"
                         f"⚡️ **Speed:** {YTDL.speed}\n"
                         f"⏳ **Estimated Time Remaining:** {YTDL.eta}\n"
                         f"📦 **Downloaded:** {YTDL.done} of {YTDL.left}"
                )
            except Exception:
                pass

        await sleep(2.5)

class MyLogger:
    def debug(self, msg):
        global YTDL
        if "item" in str(msg):
            msgs = msg.split(" ")
            YTDL.header = f"\n⏳ __Getting Video Information {msgs[-3]} of {msgs[-1]}__"

    @staticmethod
    def warning(msg):
        pass

    @staticmethod
    def error(msg):
        pass

def YouTubeDL(url):
    global YTDL

    def my_hook(d):
        global YTDL

        if d["status"] == "downloading":
            total_bytes = d.get("total_bytes", 0)
            dl_bytes = d.get("downloaded_bytes", 0)
            speed = d.get("speed", "N/A")
            eta = d.get("eta", 0)

            if total_bytes:
                percent = round((float(dl_bytes) * 100 / float(total_bytes)), 2)
                YTDL.percentage = percent

            YTDL.speed = humanbytes(speed) if speed else "N/A"
            YTDL.eta = getTime(eta) if eta else "N/A"
            YTDL.done = humanbytes(dl_bytes) if dl_bytes else "N/A"
            YTDL.left = humanbytes(total_bytes) if total_bytes else "N/A"
            YTDL.header = ""

        elif d["status"] == "finished":
            YTDL.header = "Download completed"

    ydl_opts = {
        "format": "best",
        "allow_multiple_video_streams": True,
        "allow_multiple_audio_streams": True,
        "writethumbnail": True,
        "concurrent_fragment_downloads": 4,
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferredformat": "mp4"}],
        "progress_hooks": [my_hook],
        "writesubtitles": "srt",
        "extractor_args": {"subtitlesformat": "srt"},
        "logger": MyLogger(),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        if not ospath.exists(DOWNLOAD_LOCATION):
            makedirs(DOWNLOAD_LOCATION)
        try:
            info_dict = ydl.extract_info(url, download=False)
            YTDL.header = "⌛ __Please WAIT a bit...__"
            ydl_opts["outtmpl"] = {
                "default": f"{DOWNLOAD_LOCATION}/%(title)s.%(ext)s",
            }
            ydl.download([url])
        except Exception as e:
            logging.error(f"YTDL ERROR: {e}")

async def get_YT_Name(link):
    with yt_dlp.YoutubeDL({"logger": MyLogger()}) as ydl:
        try:
            info = ydl.extract_info(link, download=False)
            if "title" in info and info["title"]:
                return info["title"]
            else:
                return "UNKNOWN DOWNLOAD NAME"
        except Exception as e:
            return "UNKNOWN DOWNLOAD NAME"

@Client.on_message(filters.private & filters.command("ytdl") & filters.user(ADMIN))
async def ytdl(bot, msg):
    await msg.reply_text("🎥 Please send your YouTube links to download.")

@Client.on_message(filters.private & filters.user(ADMIN) & filters.regex(r'https?://(www\.)?youtube\.com/watch\?v='))
async def youtube_link_handler(bot, msg):
    url = msg.text.strip()
    processing_message = await msg.reply_text("🔄 **Processing your request...**")
    await YTDL_Status(url, 1, processing_message)

@Client.on_callback_query(filters.regex(r'^yt_\d+_https?://(www\.)?youtube\.com/watch\?v='))
async def yt_callback_handler(bot, query):
    data = query.data.split('_')
    format_id = data[1]
    url = '_'.join(data[2:])

    c_time = time.time()
    await query.message.edit_text("⬇️ **Download started...**")

    def progress_hook(d):
        download_progress_callback(d, query.message, c_time)

    ydl_opts = {
        'format': f'{format_id}+bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_LOCATION, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'merge_output_format': 'mp4'  # Specify to merge to mp4 format
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            downloaded_path = ydl.prepare_filename(info_dict)
    except Exception as e:
        await query.message.edit_text(f"❌ **Error during download:** {e}")
        return

    # If the downloaded file is not already in MP4 format, convert it to MP4
    if not downloaded_path.endswith(".mp4"):
        mp4_path = downloaded_path.rsplit('.', 1)[0] + ".mp4"
        subprocess.run(
            ['ffmpeg', '-i', downloaded_path, '-c:v', 'libx264', '-c:a', 'aac', mp4_path],
            check=True
        )
        remove(downloaded_path)
        downloaded_path = mp4_path

    video = VideoFileClip(downloaded_path)
    duration = int(video.duration)
    video_width, video_height = video.size
    filesize = humanbytes(os.path.getsize(downloaded_path))

    thumb_url = info_dict.get('thumbnail', None)
    thumb_path = os.path.join(DOWNLOAD_LOCATION, 'thumb.jpg')
    response = requests.get(thumb_url)
    if response.status_code == 200:
        with open(thumb_path, 'wb') as thumb_file:
            thumb_file.write(response.content)

        with Image.open(thumb_path) as img:
            img_width, img_height = img.size
            scale_factor = max(video_width / img_width, video_height / img_height)
            new_size = (int(img_width * scale_factor), int(img_height * scale_factor))
            img = img.resize(new_size, Image.ANTIALIAS)
            left = (img.width - video_width) / 2
            top = (img.height - video_height) / 2
            right = (img.width + video_width) / 2
            bottom = (img.height + video_height) / 2
            img = img.crop((left, top, right, bottom))
            img.save(thumb_path)
    else:
        thumb_path = None

    button_text = query.data.split('_')[2]

    caption = (
        f"**🎬 {info_dict['title']}**\n\n"
        f"💽 **Size:** {filesize}\n"
        f"🕒 **Duration:** {duration} seconds\n"
        f"📹 **Resolution:** {button_text}\n\n"
        f"✅ **Download completed!"
    )

    await query.message.edit_text("🚀 **Uploading started...** 📤")

    c_time = time.time()
    try:
        await bot.send_video(
            chat_id=query.message.chat.id,
            video=downloaded_path,
            thumb=thumb_path,
            caption=caption,
            duration=duration,
            progress=progress_message,
            progress_args=("Upload Started..... Thanks To All Who Supported ❤", query.message, c_time)
        )
    except Exception as e:
        await query.message.edit_text(f"❌ **Error during upload:** {e}")
        return

    remove(downloaded_path)
    if thumb_path:
        remove(thumb_path)

    await query.message.delete()
