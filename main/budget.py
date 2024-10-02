import time
from pyrogram import Client, filters
import telegraph

# Initialize Telegraph account
telegraph = telegraph.Telegraph()
telegraph.create_account(short_name='budget_saver')

# Store savings data and user states
user_states = {}  # Keeps track of users' progress in the conversation
savings_data = {}  # Dictionary to store the date and saving amount per user
telegraph_content = ""  # HTML content for the Telegraph page

# Command to initiate budget saving
@Client.on_message(filters.private & filters.command("budget"))
async def start_budgeting(bot, msg):
    user_id = msg.from_user.id
    # Ask for the date
    await msg.reply_text("Please send today's date in this format: `YYYY-MM-DD`")
    
    # Set user state to "awaiting_date"
    user_states[user_id] = 'awaiting_date'

# Handle the user's input after `/budget`
@Client.on_message(filters.private & filters.text)
async def handle_user_input(bot, msg):
    user_id = msg.from_user.id
    
    # Check if the user is in the middle of a budget operation
    if user_id in user_states:
        state = user_states[user_id]

        # If we're expecting a date
        if state == 'awaiting_date':
            date_text = msg.text.strip()
            
            # Validate the date format
            if len(date_text) != 10 or date_text[4] != '-' or date_text[7] != '-':
                return await msg.reply_text("Invalid format. Please send the date in `YYYY-MM-DD` format.")
            
            # Store the date for the user
            savings_data[user_id] = {'date': date_text}
            
            # Ask for the saving amount
            await msg.reply_text("Now, send your saving amount (in numbers).")
            
            # Update state to expect the saving amount
            user_states[user_id] = 'awaiting_saving'

        # If we're expecting the saving amount
        elif state == 'awaiting_saving':
            try:
                saving_price = float(msg.text)
            except ValueError:
                return await msg.reply_text("Please send a valid number.")
            
            # Store the saving amount
            savings_data[user_id]['price'] = saving_price

            # Update the Telegraph content
            global telegraph_content
            user_data = savings_data[user_id]
            telegraph_content += f"<p>Date: {user_data['date']} - Saved: {user_data['price']} units</p>"

            # Create or update the Telegraph page
            response = telegraph.create_page(
                title="Daily Savings Tracker",
                html_content=telegraph_content
            )

            # Send the Telegraph URL to the user
            telegraph_url = f"https://telegra.ph/{response['path']}"
            await msg.reply_text(f"Added to the site! ✅\nView your savings here: {telegraph_url}")
            
            # Clear user state after the process is done
            del user_states[user_id]
            del savings_data[user_id]
