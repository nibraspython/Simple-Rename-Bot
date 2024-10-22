import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultVideo
from googleapiclient.discovery import build
import isodate  # To convert ISO 8601 duration format

# Your bot's API credentials and other configurations
YOUTUBE_API_KEY = "AIzaSyDp0oGuQ35JDAW6HBJCg3OBviIlWzLXTn4"

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def format_duration(duration):
    # Convert ISO 8601 duration (e.g., PT3M10S) to a human-readable format
    duration_obj = isodate.parse_duration(duration)
    total_seconds = int(duration_obj.total_seconds())
    
    # Convert to hours, minutes, and seconds
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

@Client.on_inline_query()
async def youtube_search(bot, query):
    search_query = query.query.strip()
    if not search_query:
        return

    # Search for videos using the YouTube Data API
    search_response = youtube.search().list(
        q=search_query,
        part='snippet',
        type='video',
        maxResults=5
    ).execute()

    results = []
    for item in search_response['items']:
        video_id = item['id']['videoId']
        title = item['snippet']['title']
        thumbnail = item['snippet']['thumbnails']['default']['url']
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Get video details like duration and views
        video_details = youtube.videos().list(
            id=video_id,
            part='contentDetails,statistics'
        ).execute()

        # Format duration
        duration_iso = video_details['items'][0]['contentDetails']['duration']
        duration = format_duration(duration_iso)

        views = video_details['items'][0]['statistics']['viewCount']

        # Create an inline result
        results.append(
            InlineQueryResultArticle(
                title=title,
                description=f"Duration: {duration} | Views: {views}",
                thumb_url=thumbnail,
                input_message_content=InputTextMessageContent(video_url),  # Send only the URL
                url=video_url,
            )
        )

    # Send the inline results
    await query.answer(results, cache_time=0)
