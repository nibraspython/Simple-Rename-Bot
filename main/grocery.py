import os
import zipfile
import shutil
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, ADMIN
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio

# Dictionary to store categories and selected items
categories = {
    "foods": ["butter", "bread", "cheese"],
    "spices": ["salt", "pepper", "turmeric"],
    "vegetables": ["carrot", "ලීක්ස්", "potato"],
    "meat items": ["chicken", "beef", "lamb"],
    "other items": ["oil", "sugar", "rice"]
}
selected_items = {}

# File path for storing selected items
selected_items_file = os.path.join(DOWNLOAD_LOCATION, "selected_items.txt")

def get_image_path(item):
    # Assuming images are stored in a specific directory named 'grocery_images'
    image_directory = os.path.join(DOWNLOAD_LOCATION, "grocery_images")
    # Create the image path by combining the directory and item name
    return os.path.join(image_directory, f"{item}.png")  # Assuming images are named as 'item_name.png'

# Step 1: Handle the /grocery command
@Client.on_message(filters.private & filters.command("grocery") & filters.reply & filters.user(ADMIN))
async def handle_grocery_command(bot, msg):
    reply = msg.reply_to_message
    if reply.document and reply.document.file_name.endswith(".zip"):
        await msg.reply_text("📦 Extracting zip file...")
        try:
            # Download and extract the zip file
            zip_path = os.path.join(DOWNLOAD_LOCATION, reply.document.file_name)
            await reply.download(zip_path)

            extract_dir = os.path.join(DOWNLOAD_LOCATION, "grocery_images")
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            os.remove(zip_path)
            await msg.reply_text("✅ Zip file extraction completed.")
            
            # Show categories selection with inline buttons
            await show_category_selection(bot, msg)

        except Exception as e:
            await msg.reply_text(f"❌ Error during extraction: {e}")
    else:
        await msg.reply_text("❌ Please reply to a valid .zip file.")

# Step 2: Show category selection
async def show_category_selection(bot, msg):
    keyboard = [
        [InlineKeyboardButton("Foods", callback_data="category_foods")],
        [InlineKeyboardButton("Spices", callback_data="category_spices")],
        [InlineKeyboardButton("Vegetables", callback_data="category_vegetables")],
        [InlineKeyboardButton("Meat Items", callback_data="category_meat items")],
        [InlineKeyboardButton("Other Items", callback_data="category_other items")],
        [InlineKeyboardButton("Done", callback_data="category_done")]
    ]
    await msg.reply_text(
        "🍽 Select your category:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Step 3: Handle category selection
@Client.on_callback_query(filters.regex(r"^category_"))
async def handle_category_selection(bot, query):
    category = query.data.split("_")[1]
    
    if category == "done":
        # Proceed to next steps (image creation, etc.)
        await process_selected_items(bot, query.message)
        return

    # Show items in the selected category with navigation
    await show_items_in_category(bot, query.message, category, 0)

# Step 4: Show items in the selected category with navigation
async def show_items_in_category(bot, msg, category, index):
    items = categories[category]
    current_items = items[index:index+3]  # Show 3 items at a time

    # Generate item buttons and navigation buttons
    item_buttons = [
        [InlineKeyboardButton(item.capitalize(), callback_data=f"item_{category}_{item}")] 
        for item in current_items
    ]
    navigation_buttons = []
    if index > 0:
        navigation_buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"prev_{category}_{index-3}"))
    if index + 3 < len(items):
        navigation_buttons.append(InlineKeyboardButton("▶️ Next", callback_data=f"next_{category}_{index+3}"))
    navigation_buttons.append(InlineKeyboardButton("🔙 Back", callback_data="back"))

    keyboard = item_buttons + [navigation_buttons]
    
    await msg.edit_text(
        f"🍽 {category.capitalize()} items:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Step 5: Handle item selection
@Client.on_callback_query(filters.regex(r"^item_"))
async def handle_item_selection(bot, query):
    _, category, item = query.data.split("_")

    # Add the selected item to the list
    selected_items.setdefault(category, []).append(item)

    # Save the selection to the file
    with open(selected_items_file, "a") as f:
        f.write(f"{category}: {item}\n")

    # Show temporary "item added" message
    added_msg = await query.message.reply_text(f"✅ Item added: {item.capitalize()}")
    await asyncio.sleep(2)
    await added_msg.delete()

    # Refresh the category selection screen
    await show_items_in_category(bot, query.message, category, 0)

# Step 6: Handle navigation (previous, next, back)
@Client.on_callback_query(filters.regex(r"^prev_|^next_|^back"))
async def handle_navigation(bot, query):
    if query.data.startswith("back"):
        await show_category_selection(bot, query.message)
    else:
        _, category, index = query.data.split("_")
        await show_items_in_category(bot, query.message, category, int(index))

    # Create grocery list image
    output_image_path = os.path.join(DOWNLOAD_LOCATION, "grocery_list.png")
    create_grocery_image(categorized_items, output_image_path)

# Step 7: Process selected items after "Done"
async def process_selected_items(bot, msg):
    await msg.edit_text("🖼 Creating your grocery list image...")

    # Read selected items from the file
    if not os.path.exists(selected_items_file):
        await msg.reply_text("❌ No items selected.")
        return

    with open(selected_items_file, "r") as f:
        items = f.readlines()

    # Filter and organize items by category with image paths
    categorized_items = {}
    for line in items:
        category, item = line.strip().split(": ")
        # Assume a function `get_image_path` that returns the image path for an item
        image_path = get_image_path(item)  # Function to fetch image paths
        categorized_items.setdefault(category, []).append({"image_path": image_path, "name": item})

    # Define the path for the grocery list image to be saved
    output_image_path = os.path.join(DOWNLOAD_LOCATION, "grocery_list.png")

    # Create grocery list image
    create_grocery_image(categorized_items, output_image_path)

    await bot.send_photo(
        chat_id=msg.chat.id,
        photo=output_image_path,
        caption="🛒 Your Grocery List 🛍",
    )

    # Clean up
    if os.path.exists(selected_items_file):
        os.remove(selected_items_file)    

# Assuming you've already set the correct path for your background image
background_image_path = "/content/Simple-Rename-Bot/background_image.jpg"

def create_grocery_image_with_background(categorized_items, output_image_path):
    # Load the background image
    background = Image.open(background_image_path)

    # Set up the drawing context for the background
    draw = ImageDraw.Draw(background)
    
    # Calculate space for grocery items (on the left side)
    left_margin = 150  # Left margin for positioning the boxes
    top_margin = 200   # Start from 200px down from the top
    box_size = (600, 550)  # Box size for each item (adjust as needed)
    margin = 50  # Margin between boxes
    items_per_column = 3  # Number of items to show per column for better layout
    shadow_offset = 20  # Shadow offset for 3D effect
    corner_radius = 40  # Rounded corners for item boxes
    box_color = (255, 255, 255)  # White box color
    shadow_color = (170, 170, 170)  # Gray shadow color

    # Load font (adjust path accordingly)
    font_path = "/content/Simple-Rename-Bot/Roboto-Black.ttf"  # Ensure the path is correct
    try:
        item_font = ImageFont.truetype(font_path, 80)  # Font size for item names
    except OSError:
        item_font = ImageFont.load_default()

    # Initialize the position for the first item
    y_offset = top_margin
    x_offset = left_margin
    
    # Iterate through categorized_items to create the grocery list
    for category, items in categorized_items.items():
        for i, item in enumerate(items):
            img_path = item['image_path']
            name = item['name']

            # Open each item image and resize
            try:
                item_img = Image.open(img_path)
                item_img = item_img.resize((box_size[0] - 50, box_size[1] - 200))  # Resize to fit the box
            except Exception as e:
                print(f"Error loading image {img_path}: {e}")
                continue

            # Calculate x and y positions for the item box
            if i % items_per_column == 0 and i > 0:
                y_offset += box_size[1] + 4 * margin  # Increase vertical spacing

            # Draw shadow to simulate 3D effect
            draw.rounded_rectangle([(x_offset + shadow_offset, y_offset + shadow_offset), 
                                    (x_offset + box_size[0] + shadow_offset, y_offset + box_size[1] + shadow_offset)], 
                                   fill=shadow_color, radius=corner_radius)

            # Draw the main box for the item with rounded corners
            draw.rounded_rectangle([(x_offset, y_offset), 
                                    (x_offset + box_size[0], y_offset + box_size[1])], 
                                   fill=box_color, radius=corner_radius)

            # Paste the item image in the center of the box
            img_x = x_offset + (box_size[0] - item_img.size[0]) // 2
            img_y = y_offset + (box_size[1] - item_img.size[1]) // 2 - 100  # Adjust for item name space
            background.paste(item_img, (img_x, img_y))

            # Draw the item name below the image
            name_bbox = draw.textbbox((0, 0), name, font=item_font)
            name_w = name_bbox[2] - name_bbox[0]
            draw.text((x_offset + (box_size[0] - name_w) / 2, y_offset + box_size[1] - 100), 
                      name.capitalize(), fill="black", font=item_font)

    # Save the final image with the background and items
    background.save(output_image_path)

# Example usage:
# Assuming categorized_items is a dictionary with items and their image paths
# create_grocery_image_with_background(categorized_items, "grocery_list_with_bg.png")
