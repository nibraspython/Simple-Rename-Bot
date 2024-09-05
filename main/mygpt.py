import openai
from pyrogram import Client, filters
from config import OPENAI_API_KEY  # Store your OpenAI API key in the config file

# Initialize the OpenAI API client
openai.api_key = OPENAI_API_KEY

@Client.on_message(filters.private & filters.command("chatgpt"))
async def chatgpt(bot, msg):
    user_input = msg.text.split(maxsplit=1)
    if len(user_input) < 2:
        return await msg.reply_text("Please provide a prompt to send to GPT-4.")
    
    prompt = user_input[1]
    await msg.reply_text("🤖 Thinking...")

    try:
        # Call GPT-4 API
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        gpt_reply = response.choices[0].message['content'].strip()

        # Send GPT-4 response back to the user
        await msg.reply_text(gpt_reply)
    except Exception as e:
        await msg.reply_text(f"An error occurred: {e}")

