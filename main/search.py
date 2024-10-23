import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent
from googleapiclient.discovery import build
import isodate  # To convert ISO 8601 duration format
import re  # To help extract channel ID or handle from the URL

# Your bot's API credentials and other configurations
YOUTUBE_API_KEY = "AIzaSyDp0oGuQ35JDAW6HBJCg3OBviIlWzLXTn4"

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

def format_duration(duration):
    duration_obj = isodate.parse_duration(duration)
    total_seconds = int(duration_obj.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def extract_channel_info(url):
    """Extract the channel handle, username, or ID from a YouTube channel URL."""
    channel_id = None
    # Handle different types of YouTube channel URLs
    if '/channel/' in url:
        channel_id = re.search(r'channel/([^/?]+)', url).group(1)
    elif '/user/' in url:
        channel_id = re.search(r'user/([^/?]+)', url).group(1)
    elif '@' in url:
        channel_id = re.search(r'@([^/?]+)', url).group(1)
    return channel_id

@Client.on_inline_query()
async def youtube_search(bot, query):
    search_query = query.query.strip()

    # Check if the query is a YouTube channel URL
    if search_query.startswith('https://youtube.com/'):
        channel_id_or_handle = extract_channel_info(search_query)

        if channel_id_or_handle:
            # Try fetching channel by username/handle first
            try:
                # Fetch by handle or username
                channel_response = youtube.channels().list(
                    forUsername=channel_id_or_handle,
                    part='snippet,contentDetails',
                    maxResults=1
                ).execute()
            except Exception:
                channel_response = None

            # If no results, try as channel ID
            if not channel_response or 'items' not in channel_response:
                channel_response = youtube.channels().list(
                    id=channel_id_or_handle,
                    part='snippet,contentDetails',
                    maxResults=1
                ).execute()

            if 'items' in channel_response and channel_response['items']:
                # Extract channel information
                channel = channel_response['items'][0]
                channel_title = channel['snippet']['title']
                channel_icon = channel['snippet']['thumbnails']['default']['url']
                uploads_playlist_id = channel['contentDetails']['relatedPlaylists']['uploads']

                # Fetch videos uploaded by the channel, ordered by latest
                video_response = youtube.playlistItems().list(
                    playlistId=uploads_playlist_id,
                    part='snippet',
                    maxResults=10,  # Fetch more if needed
                ).execute()

                results = []

                # Add channel name and icon at the top
                results.append(
                    InlineQueryResultArticle(
                        title=channel_title,
                        description="Channel Videos",
                        thumb_url=channel_icon,
                        input_message_content=InputTextMessageContent(f"Channel: {channel_title}"),
                    )
                )

                # Add videos from the channel (latest to oldest)
                for item in video_response.get('items', []):
                    video_id = item['snippet']['resourceId']['videoId']
                    title = item['snippet']['title']
                    thumbnail = item['snippet']['thumbnails']['default']['url']
                    video_url = f"https://www.youtube.com/watch?v={video_id}"

                    # Get video details (duration, views)
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
                            input_message_content=InputTextMessageContent(video_url),
                            url=video_url,
                        )
                    )

                await query.answer(results, cache_time=0)
            else:
                # Handle the case where the channel was not found
                await query.answer([InlineQueryResultArticle(
                    title="Channel not found",
                    description="Please check the URL and try again.",
                    input_message_content=InputTextMessageContent("No channel found for the given URL.")
                )], cache_time=0)
        return

    # Default search by keywords if no channel URL is provided
    if not search_query:
        return

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
                input_message_content=InputTextMessageContent(video_url),
                url=video_url,
            )
        )

    # Send the inline results
    await query.answer(results, cache_time=0)
