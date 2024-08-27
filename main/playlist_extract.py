import time
from pyrogram import Client, filters
from pytube import Playlist
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@Client.on_message(filters.private & filters.command("playlist") & filters.user(ADMIN))
async def playlist_links(bot, msg):
    await msg.reply_text("🎶 Please send your playlist URL to extract the video links.")
    
    @Client.on_message(filters.private & filters.text & filters.user(ADMIN))
    async def process_playlist(bot, msg):
        playlist_url = msg.text.strip()
        if "youtube.com/playlist" not in playlist_url:
            return await msg.reply_text("🚫 Invalid Playlist URL. Please send a valid YouTube playlist URL.")
        
        sts = await msg.reply_text("🔄 Processing your playlist... Please wait.")
        
        try:
            playlist = Playlist(playlist_url)
            video_urls = playlist.video_urls
            playlist_title = playlist.title
        except Exception as e:
            return await sts.edit(f"Error: {e}")
        
        # Pagination
        max_buttons = 10
        pages = [video_urls[i:i + max_buttons] for i in range(0, len(video_urls), max_buttons)]
        
        def create_keyboard(page, current_page):
            buttons = [
                [InlineKeyboardButton(text=f"{video.title}", url=video_url)]
                for video_url, video in zip(page, playlist.videos[current_page * max_buttons:(current_page + 1) * max_buttons])
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
        
        @Client.on_callback_query(filters.regex(r"previous_\d+|next_\d+"))
        async def navigate_playlist(bot, query):
            action, page_num = query.data.split("_")
            current_page = int(page_num)
            await query.message.edit_reply_markup(create_keyboard(pages[current_page], current_page))
