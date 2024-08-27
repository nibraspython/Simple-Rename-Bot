import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN  # Import ADMIN from your config

# Store playlist data globally for this example
playlist_data = {}

def create_keyboard(page, current_page, total_pages):
    buttons = [
        [InlineKeyboardButton(text=f"🎥 {video['title']}", callback_data=video['url'])]
        for video in page
    ]
    
    navigation_buttons = []
    if current_page > 0:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"previous_{current_page - 1}"))
    if current_page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton(text="➡️ Next", callback_data=f"next_{current_page + 1}"))
    
    if navigation_buttons:
        buttons.append(navigation_buttons)
    
    return InlineKeyboardMarkup(buttons)

@Client.on_message(filters.private & filters.command("playlist") & filters.user(ADMIN))
async def playlist_links(bot, msg):
    await msg.reply_text("🎶 Please send your playlist URL to extract the video links.")

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def process_playlist(bot, msg):
    if not msg.reply_to_message or "/playlist" not in msg.reply_to_message.text:
        return
    
    playlist_url = msg.text.strip()
    if "youtube.com/playlist" not in playlist_url:
        return await msg.reply_text("🚫 Invalid Playlist URL. Please send a valid YouTube playlist URL.")
    
    sts = await msg.reply_text("🔄 Processing your playlist... Please wait.")
    
    try:
        ydl_opts = {
            "extract_flat": True,
            "skip_download": True,
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            video_entries = playlist_info.get('entries')
            if not video_entries:
                return await sts.edit("🚫 No videos found in this playlist.")
            
            playlist_title = playlist_info.get("title", "Unnamed Playlist")
            
            # Store playlist data
            playlist_data[playlist_url] = video_entries
        
        max_buttons = 10
        total_pages = len(video_entries) // max_buttons + (1 if len(video_entries) % max_buttons else 0)
        pages = [video_entries[i:i + max_buttons] for i in range(0, len(video_entries), max_buttons)]
        
        # Show the first page of videos
        await sts.edit(
            text=f"🎉 Playlist: {playlist_title}\n\n🎥 Select a video to get the link:",
            reply_markup=create_keyboard(pages[0], 0, total_pages)
        )
    except Exception as e:
        await sts.edit(f"Error: {e}")

@Client.on_callback_query(filters.regex(r"previous_\d+|next_\d+"))
async def navigate_playlist(bot, query):
    action, page_num = query.data.split("_")
    current_page = int(page_num)
    
    playlist_url = query.message.reply_markup.inline_keyboard[0][0].callback_data.split("&")[0]
    
    # Retrieve video entries from stored playlist data
    video_entries = playlist_data.get(playlist_url)
    if not video_entries:
        return await query.message.edit("🚫 No videos found in this playlist.")
    
    max_buttons = 10
    total_pages = len(video_entries) // max_buttons + (1 if len(video_entries) % max_buttons else 0)
    pages = [video_entries[i:i + max_buttons] for i in range(0, len(video_entries), max_buttons)]
    
    # Update the inline keyboard with the new page
    await query.message.edit_reply_markup(create_keyboard(pages[current_page], current_page, total_pages))

@Client.on_callback_query(filters.regex(r"https://www\.youtube\.com/watch\?v=.*"))
async def send_video_link(bot, query):
    await query.message.reply_text(f"🎥 Here's your video link: {query.data}")
