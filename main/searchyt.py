import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent
from config import API_ID, API_HASH, BOT_TOKEN

def search_youtube(query):
    ydl_opts = {
        'quiet': True,
        'default_search': 'ytsearch5',  # Limit to 5 search results
        'format': 'best',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                return info['entries']
    except Exception as e:
        print(f"Error in search_youtube: {e}")
    
    return []

@Client.on_inline_query()
async def youtube_search(bot, inline_query):
    query = inline_query.query.strip()
    if not query:
        await inline_query.answer([], switch_pm_text="Type a keyword to search on YouTube", switch_pm_parameter="start", cache_time=0)
        return

    search_results = search_youtube(query)
    if not search_results:
        print("No search results found.")
        await inline_query.answer([], switch_pm_text="No results found. Try a different query.", cache_time=0)
        return

    results = []
    for video in search_results:
        title = video.get('title')
        video_id = video.get('id')
        url = video.get('url')
        duration = video.get('duration')
        views = video.get('view_count', 'N/A')
        thumbnail = video.get('thumbnail')

        results.append(
            InlineQueryResultArticle(
                id=video_id,
                title=title,
                input_message_content=InputTextMessageContent(
                    message_text=f"**{title}**\n"
                                 f"🕒 Duration: {duration} seconds\n"
                                 f"👁 Views: {views}\n"
                                 f"🔗 [Watch on YouTube]({url})"
                ),
                thumb_url=thumbnail,
                description=f"Views: {views} | Duration: {duration} seconds"
            )
        )

    await inline_query.answer(results, cache_time=0)
