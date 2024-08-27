import time
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN  # Import ADMIN from your config

# Start Command to prompt user to send playlist URL
@Client.on_message(filters.private & filters.command("playlist") & filters.user(ADMIN))
async def playlist_links(bot, msg):
    await msg.reply_text("🎶 Please send your playlist URL to extract the video links.")

# Process the playlist URL
@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def process_playlist(bot, msg):
    # Check if the previous message was the /playlist command
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
            video_entries = playlist_info['entries']
            playlist_title = playlist_info.get("title", "Unnamed Playlist")
    except Exception as e:
        return await sts.edit(f"Error: {e}")
    
    # Pagination
    max_buttons = 10
    pages = [video_entries[i:i + max_buttons] for i in range(0, len(video_entries), max_buttons)]
    
    def create_keyboard(page, current_page):
        buttons = [
            [InlineKeyboardButton(text=f"🎥 {video['title']}", callback_data=video['url'])]
            for video in page
        ]
        
        navigation_buttons = []
        if current_page > 0:
            navigation_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"previous_{current_page - 1}"))
        if current_page < len(pages) - 1:
            navigation_buttons.append(InlineKeyboardButton(text="➡️ Next", callback_data=f"next_{current_page + 1}"))
        
        if navigation_buttons:
            buttons.append(navigation_buttons)
        
        return InlineKeyboardMarkup(buttons)
    
    # Show the first page of videos
    await sts.edit(
        text=f"🎉 Playlist: {playlist_title}\n\n🎥 Select a video to get the link:",
        reply_markup=create_keyboard(pages[0], 0)
    )

# Handle callback queries for navigation
@Client.on_callback_query(filters.regex(r"previous_\d+|next_\d+"))
async def navigate_playlist(bot, query):
    action, page_num = query.data.split("_")
    current_page = int(page_num)
    pages = query.message.reply_markup.inline_keyboard  # Get pages from the current message
    pages = [row for row in pages if len(row) == 1]  # Filter out navigation buttons
    video_entries = [{"url": button.callback_data, "title": button.text[2:]} for row in pages for button in row]
    
    # Determine the next page based on action
    if action == "previous":
        current_page -= 1
    elif action == "next":
        current_page += 1
    
    # Update the inline keyboard with the new page
    await query.message.edit_reply_markup(create_keyboard(video_entries[current_page * 10:(current_page + 1) * 10], current_page))

# Handle callback queries for video links
@Client.on_callback_query(filters.regex(r"https://www\.youtube\.com/watch\?v=.*"))
async def send_video_link(bot, query):
    await query.message.reply_text(f"🎥 Here's your video link: {query.data}")
