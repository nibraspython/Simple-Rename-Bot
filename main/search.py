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

    # Check if query starts with '@Dilrenamer_bot <channel_id>'
    if search_query.startswith('@Dilrenamer_bot'):
        channel_id = search_query.split()[1]  # Extract the channel ID
        channel_response = youtube.channels().list(
            id=channel_id,
            part='snippet,contentDetails',
            maxResults=1
        ).execute()

        if channel_response['items']:
            channel = channel_response['items'][0]
            channel_title = channel['snippet']['title']
            channel_icon = channel['snippet']['thumbnails']['default']['url']
            uploads_playlist_id = channel['contentDetails']['relatedPlaylists']['uploads']

            # Fetch videos uploaded by the channel
            video_response = youtube.playlistItems().list(
                playlistId=uploads_playlist_id,
                part='snippet',
                maxResults=5,  # Adjust as needed
            ).execute()

            results = []

            # Add channel name and icon at the top
            results.append(
                InlineQueryResultArticle(
                    title=channel_title,
                    description=f"Channel ID: {channel_id}",
                    thumb_url=channel_icon,
                    input_message_content=InputTextMessageContent(f"Channel: {channel_title}\nChannel ID: {channel_id}"),
                )
            )

            # Add videos from the channel
            for item in video_response['items']:
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
        return

    # Default search by keywords if no channel ID is provided
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
        channel_id = item['snippet']['channelId']
        channel_title = item['snippet']['channelTitle']

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
                description=f"Duration: {duration} | Views: {views} | Channel ID: {channel_id}",
                thumb_url=thumbnail,
                input_message_content=InputTextMessageContent(f"{video_url}\nChannel: {channel_title}\nChannel ID: {channel_id}"),
                url=video_url,
            )
        )

    # Send the inline results
    await query.answer(results, cache_time=0)
