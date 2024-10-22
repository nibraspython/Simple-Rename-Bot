import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultVideo
from googleapiclient.discovery import build

# Your bot's API credentials and other configurations
YOUTUBE_API_KEY = "AIzaSyDp0oGuQ35JDAW6HBJCg3OBviIlWzLXTn4"

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

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

        duration = video_details['items'][0]['contentDetails']['duration']
        views = video_details['items'][0]['statistics']['viewCount']

        # Create an inline result
        results.append(
            InlineQueryResultArticle(
                title=title,
                description=f"Duration: {duration} | Views: {views}",
                thumb_url=thumbnail,
                input_message_content=InputTextMessageContent(f"Watch [{title}]({video_url})"),
                url=video_url,
            )
        )

    # Send the inline results
    await query.answer(results, cache_time=0)

