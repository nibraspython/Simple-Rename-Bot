from pyrogram import Client, filters
from pytube import YouTube

# Function to handle inline queries for YouTube video search
@Client.on_inline_query()
async def search_videos(bot, update):
    query = update.query

    # Perform YouTube video search using the query
    videos = YouTube(query).streams.filter(progressive=True).all()

    # Prepare inline results with video details
    results = []
    for video in videos:
        result = {
            "type": "video",
            "id": video.video_id,
            "title": video.title,
            "description": f"Duration: {video.length}nViews: {video.views}nLikes: {video.likes}",
            "thumb": video.thumbnail_url
        }
        results.append(result)

    # Answer the inline query with the video results
    await bot.answer_inline_query(update.id, results)
