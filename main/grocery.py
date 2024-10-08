import os
import zipfile
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from config import DOWNLOAD_LOCATION, ADMIN
import shutil

# Step 1: Initial command to receive zip file
@Client.on_message(filters.private & filters.command("grocery") & filters.user(ADMIN))
async def grocery_list(bot, msg):
    await msg.reply_text("📦 Please send your zip file containing all grocery images (e.g., butter.png, leeks.png).")

# Step 2: Handling the zip file upload
@Client.on_message(filters.private & filters.document & filters.user(ADMIN))
async def receive_zip_file(bot, file_msg):
    doc = file_msg.document

    # Check if the file is a zip file
    if not doc.file_name.endswith(".zip"):
        return await file_msg.reply_text("❌ Please send a valid .zip file.")

    # Acknowledge the zip file
    sts = await file_msg.reply_text("🔄 Extracting your zip file...")

    try:
        # Download the zip file
        zip_path = os.path.join(DOWNLOAD_LOCATION, doc.file_name)
        await file_msg.download(zip_path)

        # Extract zip file
        extract_dir = os.path.join(DOWNLOAD_LOCATION, "grocery_images")
        os.makedirs(extract_dir, exist_ok=True)  # Ensure the directory exists
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        os.remove(zip_path)
        await sts.edit("✅ Zip file extracted. Now send the items you want in your list (comma separated, e.g., butter,leeks,salt).")

    except Exception as e:
        await sts.edit(f"❌ Error during extraction: {e}")
        return

# Step 3: Handling the item list for the grocery image
@Client.on_message(filters.private & filters.text & filters.user(ADMIN))
async def create_grocery_list(bot, item_msg):
    items = [item.strip().lower() for item in item_msg.text.split(",")]
    extract_dir = os.path.join(DOWNLOAD_LOCATION, "grocery_images")

    if not os.path.exists(extract_dir):
        return await item_msg.reply_text("❌ No extracted grocery images found. Please send a valid zip file first.")

    images_to_add = []
    item_names = []

    # Match items with images
    for item in items:
        item_image = os.path.join(extract_dir, f"{item}.png")
        if os.path.exists(item_image):
            images_to_add.append(item_image)
            item_names.append(item.capitalize())
        else:
            await item_msg.reply_text(f"❌ Image not found for: {item}. Skipping...")

    if not images_to_add:
        return await item_msg.reply_text("❌ No valid items found. Please try again.")

    # Create the grocery list image
    output_image_path = os.path.join(DOWNLOAD_LOCATION, "grocery_list.png")
    create_grocery_image(images_to_add, item_names, output_image_path)

    await item_msg.reply_text("🖼 Creating your grocery list image...")

    # Send the created grocery list image
    await bot.send_photo(
        chat_id=item_msg.chat.id,
        photo=output_image_path,
        caption="🛒 Your Grocery List 🛍",
    )

    # Clean up
    os.remove(output_image_path)
    shutil.rmtree(extract_dir)

# Create the grocery list image
def create_grocery_image(images, names, output_image_path):
    width = 1000  # Width of the image
    margin = 20   # Margin between images and text
    box_size = (300, 300)  # Size of each grocery item image
    num_items_per_row = 2  # Number of items per row

    # Calculate total height based on number of items
    num_rows = (len(images) + num_items_per_row - 1) // num_items_per_row
    height = 200 + (box_size[1] + margin) * num_rows  # Adjust height dynamically

    background_color = (255, 255, 255)  # White background
    box_color = (200, 200, 200)  # Light gray for text box

    # Create a blank image
    image = Image.new('RGB', (width, height), background_color)
    draw = ImageDraw.Draw(image)
    
    # Load custom font, fallback to default if not available
    try:
        title_font = ImageFont.truetype("arial.ttf", 60)  # Larger title font
        item_font = ImageFont.truetype("arial.ttf", 40)  # Larger item font
    except OSError:
        title_font = ImageFont.load_default()
        item_font = ImageFont.load_default()

    # Draw the title
    title_text = "Grocery Items"
    title_w, title_h = draw.textsize(title_text, font=title_font)
    draw.text(((width - title_w) / 2, margin), title_text, fill="black", font=title_font)

    # Add grocery images and their names
    y_offset = title_h + 3 * margin
    for i, (img_path, name) in enumerate(zip(images, names)):
        # Open each image and resize
        item_img = Image.open(img_path)
        item_img = item_img.resize(box_size)

        # Calculate x position (num_items_per_row items per row)
        x_offset = (i % num_items_per_row) * (box_size[0] + margin) + margin
        if i % num_items_per_row == 0 and i > 0:
            y_offset += box_size[1] + 3 * margin

        # Paste the image
        image.paste(item_img, (x_offset, y_offset))

        # Draw text box and item name
        draw.rectangle([(x_offset, y_offset + box_size[1]), 
                        (x_offset + box_size[0], y_offset + box_size[1] + 50)], fill=box_color)
        name_w, name_h = draw.textsize(name, font=item_font)
        draw.text((x_offset + (box_size[0] - name_w) / 2, y_offset + box_size[1]), name, fill="black", font=item_font)

    # Save the image
    image.save(output_image_path)
