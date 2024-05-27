import time, os
import ffmpeg
from pyrogram import Client, filters, enums
from config import DOWNLOAD_LOCATION, CAPTION, ADMIN
from main.utils import progress_message, humanbytes

@Client.on_message(filters.private & filters.command("rename") & filters.user(ADMIN))             
async def rename_file(bot, msg):
    reply = msg.reply_to_message
    if len(msg.command) < 2 or not reply:
       return await msg.reply_text("Please Reply To A File, Video, or Audio with filename + .extension (e.g., `.mkv`, `.mp4`, `.zip`)")
    
    media = reply.document or reply.audio or reply.video
    if not media:
       return await msg.reply_text("Please Reply To A File, Video, or Audio with filename + .extension (e.g., `.mkv`, `.mp4`, `.zip`)")
    
    og_media = getattr(reply, reply.media.value)
    new_name = msg.text.split(" ", 1)[1]
    sts = await msg.reply_text("Trying to Download...")
    c_time = time.time()
    downloaded = await reply.download(file_name=new_name, progress=progress_message, progress_args=("Download Started...", sts, c_time)) 
    filesize = humanbytes(og_media.file_size)                
    if CAPTION:
        try:
            cap = CAPTION.format(file_name=new_name, file_size=filesize)
        except Exception as e:            
            return await sts.edit(text=f"Your caption has an error: unexpected keyword ●> ({e})")           
    else:
        cap = f"{new_name}\n\n💽 size : {filesize}"

    # Extract the duration using ffmpeg
    try:
        probe = ffmpeg.probe(downloaded)
        duration = int(float(probe['format']['duration']))
    except Exception as e:
        return await sts.edit(f"Error extracting duration: {e}")

    # Handling thumbnail
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
        
    await sts.edit("Uploading... 🔥")
    c_time = time.time()
    try:
        await bot.send_video(msg.chat.id, video=downloaded, thumb=og_thumbnail, caption=cap, duration=duration, progress=progress_message, progress_args=("Upload Started...", sts, c_time))        
    except Exception as e:  
        return await sts.edit(f"Error: {e}")                       
    try:
        if file_thumb:
            os.remove(file_thumb)
        os.remove(downloaded)      
    except:
        pass
    await sts.delete()
