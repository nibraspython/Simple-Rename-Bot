import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN  # Import ADMIN from your config
import hashlib

# Global dictionary to track states per user
user_states = {}

# Define a state for awaiting playlist URL
AWAITING_PLAYLIST_URL = "awaiting_playlist_url"

def create_keyboard(page, current_page, total_pages, playlist_id):
    buttons = [
        [InlineKeyboardButton(text=f"🎥 {video['title']}", callback_data=f"url_{video['url']}")]
        for video in page
    ]
    
    navigation_buttons = []
    if current_page > 0:
        navigation_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"previous_{current_page - 1}_{playlist_id}"))
    if current_page < total_pages - 1:
        navigation_buttons.append(InlineKeyboardButton(text="➡️ Next", callback_data=f"next_{current_page + 1}_{playlist_id}"))
    
    if navigation_buttons:
        buttons.append(navigation_buttons)
    
    return InlineKeyboardMarkup(buttons)

def generate_playlist_id(playlist_url):
    # Generate a unique ID based on the playlist URL
    return hashlib.md5(playlist_url.encode()).hexdigest()

@Client.on_message(filters.private & filters.command("playlist") & filters.user(ADMIN))
async def playlist_links(bot, msg):
    user_id = msg.from_user.id
    # Set the state to awaiting playlist URL
    user_states[user_id] = AWAITING_PLAYLIST_URL
    await msg.reply_text("🎶 Please send your playlist URL to extract the video links.")

@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def process_playlist(bot, msg):
    user_id = msg.from_user.id
    # Check if the user is in the correct state
    if user_states.get(user_id) != AWAITING_PLAYLIST_URL:
        return  # Ignore messages unless we're awaiting a URL
    
    playlist_url = msg.text.strip()
    if "youtube.com/playlist" not in playlist_url:
        return await msg.reply_text("🚫 Invalid Playlist URL. Please send a valid YouTube playlist URL.")
    
    sts = await msg.reply_text("🔄 Processing your playlist... Please wait.")
    user_states.pop(user_id, None)  # Clear the awaiting URL state
    
    try:
        ydl_opts = {
            "extract_flat": True,
            "skip_download": True,
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            
            if 'entries' not in playlist_info:
                return await sts.edit("🚫 No videos found in this playlist.")
            
            video_entries = playlist_info['entries']
            playlist_title = playlist_info.get("title", "Unnamed Playlist")
            
            # Generate a unique ID for the playlist
            playlist_id = generate_playlist_id(playlist_url)
            
            # Store playlist data using the unique ID
            user_states[playlist_id] = video_entries
        
        max_buttons = 10
        total_pages = len(video_entries) // max_buttons + (1 if len(video_entries) % max_buttons else 0)
        pages = [video_entries[i:i + max_buttons] for i in range(0, len(video_entries), max_buttons)]
        
        # Show the first page of videos
        await sts.edit(
            text=f"🎉 Playlist: {playlist_title}\n\n🎥 Select a video to get the link:",
            reply_markup=create_keyboard(pages[0], 0, total_pages, playlist_id)
        )
    except Exception as e:
        await sts.edit(f"Error: {e}")

@Client.on_callback_query(filters.regex(r"previous_\d+|next_\d+"))
async def navigate_playlist(bot, query):
    action, page_num, playlist_id = query.data.split("_")
    current_page = int(page_num)
    
    # Retrieve video entries from stored playlist data using the unique ID
    video_entries = user_states.get(playlist_id)
    if not video_entries:
        return await query.message.edit("🚫 No videos found in this playlist.")
    
    max_buttons = 10
    total_pages = len(video_entries) // max_buttons + (1 if len(video_entries) % max_buttons else 0)
    pages = [video_entries[i:i + max_buttons] for i in range(0, len(video_entries), max_buttons)]
    
    # Ensure we are within valid page range
    if current_page < 0 or current_page >= total_pages:
        return await query.message.edit("🚫 Invalid page number.")
    
    # Update the inline keyboard with the new page
    await query.message.edit_reply_markup(create_keyboard(pages[current_page], current_page, total_pages, playlist_id))

@Client.on_callback_query(filters.regex(r"url_"))
async def send_video_link(bot, query):
    # Extract the URL from the callback data and send it as if the user sent it
    url = query.data.split("url_")[1]
    await bot.send_message(chat_id=query.message.chat.id, text=url)
