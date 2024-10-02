import time
from pyrogram import Client, filters
from aiotelegraph import Telegraph

# Initialize Telegraph account
telegraph = Telegraph()
telegraph.create_account(short_name='budget_saver')

# Store savings data temporarily
savings_data = {}  # Dictionary to store the date and savings amount
telegraph_content = ""  # HTML content for the Telegraph page

# Command to initiate budget saving
@Client.on_message(filters.private & filters.command("budget"))
async def start_budgeting(bot, msg):
    await msg.reply_text("Please send today's date in this format: `YYYY-MM-DD`")

    # Wait for the user to send the date
    @Client.on_message(filters.private & filters.text)
    async def receive_date(client, date_msg):
        date_text = date_msg.text.strip()
        if len(date_text) != 10 or date_text[4] != '-' or date_text[7] != '-':
            return await date_msg.reply_text("Invalid format. Please send the date in `YYYY-MM-DD` format.")
        
        # Store the date
        savings_data['date'] = date_text
        await date_msg.reply_text("Now, send your saving amount (in numbers).")

        # Wait for the saving amount
        @Client.on_message(filters.private & filters.text)
        async def receive_saving(client, saving_msg):
            try:
                saving_price = float(saving_msg.text)
            except ValueError:
                return await saving_msg.reply_text("Please send a valid number.")

            # Store the saving amount
            savings_data['price'] = saving_price

            # Update the Telegraph content
            global telegraph_content
            telegraph_content += f"<p>Date: {savings_data['date']} - Saved: {savings_data['price']} units</p>"

            # Create or update the Telegraph page
            response = telegraph.create_page(
                title="Daily Savings Tracker",
                html_content=telegraph_content
            )

            # Send the Telegraph URL to the user
            telegraph_url = f"https://telegra.ph/{response['path']}"
            await saving_msg.reply_text(f"Added to the site! ✅\nView your savings here: {telegraph_url}")

