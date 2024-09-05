from os import environ

API_ID = int(environ.get("API_ID", "14631157"))
API_HASH = environ.get("API_HASH", "aa7c2b3be68a7488abdb9de6ce78d311")
BOT_TOKEN = environ.get("BOT_TOKEN", "7341561892:AAHDXnPLYUxW0Qh5XG8ynGGY1lKW8PumNqk")
TG_MAX_FILE_SIZE = 2097152000  # 2GB for Telegram
CHUNK_SIZE = 1024 * 1024  # 1MB
PROCESS_MAX_TIMEOUT = 300  # 5 minutes
CAPTION = "{file_name}\n\n💽 size: {file_size}\n🕒 duration: {duration} seconds"
ADMIN = int(environ.get("ADMIN", "5380833276"))          
CAPTION = environ.get("CAPTION", "video")
OPENAI_API_KEY = "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"

# for thumbnail ( back end is MrMKN brain 😉)
DOWNLOAD_LOCATION = "./DOWNLOADS"
START_IMAGE_URL = "https://te.legra.ph/file/bce41bc329362c454abed.jpg"
