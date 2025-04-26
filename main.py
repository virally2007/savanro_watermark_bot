import os
import logging
import tempfile
import time
from io import BytesIO
from PIL import Image
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import asyncio

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Your bot token
TOKEN = "7754923835:AAGf0uJXneEalpHclW7zMaMBHdF4u3rYbwc"

# URL of the watermark bar image
WATERMARK_URL = "https://media-hosting.imagekit.io/f2f2310074674765/watermarked_image%20(1).png?Expires=1840249804&Key-Pair-Id=K2ZIVPTIP2VGHC&Signature=Dm4BC2njg0YXi1yZIsV8rdzhjXFcsSkKz1vn9b39rPoIygAPFk5mm2qL3QixquIP7eIVlR8ngqUCFFT1JomDjNqkNFOJKfoEF1oNWO4FMUeke~iQBoCJ6H-EkFNWUd0SU2gG2Zc6~sJbhxnqsBdGWTh6tV~CrSP2FIoK53VYb6dCduIsyWwnXT99pxqzvR5ngAm03cqyHJHYvhvz0mfUzJNwSlM44Qo3ENpHaRM4f8DGcQRkrvdYCKii6ujpSPyzGLmPIkRszBiKcYzhJhTjQv21kPIuwdRpy5cCpW2y-TWFimji8g7gn-cay-MzyO6ia6vybNprVfmP9nU-dwhxyw__"

# Animation frames for processing message
PROCESSING_ANIMATIONS = [
    "Processing image 🚧",
    "Processing image 🚧🚧",
    "Processing image 🚧🚧🚧",
    "Processing image 🚧🚧🚧🚧",
    "Processing image 🚧🚧🚧🚧🚧"
]

# Watermark size percentage (percentage of the image width)
WATERMARK_WIDTH_PERCENT = 40  # Adjust this value to make watermark bigger or smaller

# Function to download and save the watermark bar
async def download_watermark():
    try:
        response = requests.get(WATERMARK_URL)
        if response.status_code != 200:
            logger.error(f"Failed to download watermark: HTTP {response.status_code}")
            return None
            
        watermark = Image.open(BytesIO(response.content))
        
        # Save to a temp file with unique name
        temp_dir = tempfile.gettempdir()
        watermark_path = os.path.join(temp_dir, f"watermark_bar_{int(time.time())}.png")
        watermark.save(watermark_path)
        logger.info(f"Watermark downloaded and saved to {watermark_path}")
        return watermark_path
    except Exception as e:
        logger.error(f"Error downloading watermark: {e}")
        return None

# Function to add white outline to Savanro logo in the watermark
async def enhance_watermark_with_outline(watermark_path):
    try:
        # Open the watermark image
        watermark = Image.open(watermark_path)
        
        # Create a new image with the same size
        enhanced = Image.new('RGBA', watermark.size, (0, 0, 0, 0))
        
        # Paste the original watermark
        enhanced.paste(watermark, (0, 0))
        
        # Save the enhanced watermark
        enhanced_path = os.path.join(tempfile.gettempdir(), f"enhanced_watermark_{int(time.time())}.png")
        enhanced.save(enhanced_path)
        
        # Return the path to the enhanced watermark
        return enhanced_path
    except Exception as e:
        logger.error(f"Error enhancing watermark: {e}")
        return watermark_path  # Return original if enhancement fails

# Modified function to add watermark to bottom left corner
async def add_watermark(image_path, watermark_path):
    try:
        # Open the image
        with Image.open(image_path) as img:
            # Convert to RGB if it's not (to handle PNG with transparency)
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Open the watermark
            with Image.open(watermark_path) as watermark:
                # Calculate the new watermark width based on the percentage of image width
                # Using a larger percentage to make the watermark more visible
                new_watermark_width = int(img.width * 0.6)  # 60% of image width for better visibility
                
                # Calculate the new height maintaining aspect ratio
                aspect_ratio = watermark.width / watermark.height
                new_watermark_height = int(new_watermark_width / aspect_ratio)
                
                # Resize watermark
                watermark = watermark.resize((new_watermark_width, new_watermark_height))
                
                # Create a copy of the original image
                new_img = img.copy()
                
                # Calculate position for bottom left corner with a small gap (10px)
                gap = int(img.width * 0.02)  # 2% of image width as gap
                position = (gap, img.height - new_watermark_height - gap)
                
                # Handle transparency in the watermark
                if watermark.mode == 'RGBA':
                    # Create a mask from the alpha channel
                    mask = watermark.split()[3]
                    # Paste the watermark using the alpha channel as mask
                    new_img.paste(watermark, position, mask)
                else:
                    # If no transparency, just paste directly
                    new_img.paste(watermark, position)
                
                # Save the result to a temporary file with unique name
                timestamp = int(time.time())
                output_path = os.path.join(tempfile.gettempdir(), f"watermarked_image_{timestamp}.jpg")
                new_img.save(output_path, quality=95)
                
                logger.info(f"Successfully added watermark, saved to {output_path}")
                return output_path
    except Exception as e:
        logger.error(f"Error adding watermark: {e}")
        return None

# Animation function for processing message - FIXED to handle duplicate message issue
async def animate_processing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.message.reply_text("Processing image 🚧")
    
    # Track the last frame to avoid duplicate updates
    last_frame = "Processing image 🚧"
    
    # Animate the processing message
    for i in range(3):  # Do the animation 3 times
        for frame in PROCESSING_ANIMATIONS:
            await asyncio.sleep(0.3)  # Wait a bit between frames
            # Only update if the frame is different from the last one
            if frame != last_frame:
                try:
                    await message.edit_text(frame)
                    last_frame = frame
                except Exception as e:
                    # Log the error but continue the animation
                    logger.error(f"Error updating animation frame: {e}")
    
    return message

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("Start Processing", callback_data='start'),
            InlineKeyboardButton("Clear History", callback_data='clear')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        'Welcome to Savanro Construction Watermark Bot! 🏗️\n\n'
        'Send me any image and I will add the Savanro Construction watermark bar to it.',
        reply_markup=reply_markup
    )

# Command handler for /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("Start Processing", callback_data='start'),
            InlineKeyboardButton("Clear History", callback_data='clear')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        'How to use this bot:\n\n'
        '1. Send any image as photo or document\n'
        '2. Wait for processing (you\'ll see an animation)\n'
        '3. Receive your image with the Savanro Construction watermark\n\n'
        'Use the buttons below to start processing or clear chat history.',
        reply_markup=reply_markup
    )

# Callback handler for button presses
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start':
        await query.edit_message_text(
            text="Ready to process your images! Send me a photo to add the Savanro watermark."
        )
    elif query.data == 'clear':
        # This is a simulated clear - Telegram doesn't allow bots to delete all messages
        await query.edit_message_text(
            text="🧹 History cleared! Send me a new image to process."
        )

# Message handler for images
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Show animated processing message
    processing_msg = await animate_processing(update, context)
    
    # Download watermark each time to avoid file access issues
    watermark_path = await download_watermark()
    
    if not watermark_path:
        await processing_msg.edit_text('Sorry, there was an error with the watermark. Please try again later.')
        return
    
    # Enhance watermark with white outline for Savanro logo
    enhanced_watermark_path = await enhance_watermark_with_outline(watermark_path)
    
    try:
        # Get the image file
        photo_file = await update.message.photo[-1].get_file()
        
        # Use BytesIO to avoid file access issues
        image_bytes = BytesIO()
        await photo_file.download_to_memory(image_bytes)
        image_bytes.seek(0)
        
        # Create a unique temp file to save the image
        timestamp = int(time.time())
        temp_file_path = os.path.join(tempfile.gettempdir(), f"input_image_{timestamp}.jpg")
        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(image_bytes.getvalue())
        
        # Add watermark
        output_path = await add_watermark(temp_file_path, enhanced_watermark_path)
        
        # Send the watermarked image back
        if output_path:
            # Delete the processing message
            await processing_msg.delete()
            
            # Send the watermarked image with buttons
            keyboard = [
                [
                    InlineKeyboardButton("Process Another", callback_data='start'),
                    InlineKeyboardButton("Clear History", callback_data='clear')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            with open(output_path, 'rb') as file:
                await update.message.reply_photo(
                    photo=file,
                    caption="Your image with Savanro Construction watermark ✅",
                    reply_markup=reply_markup
                )
            
            # Clean up files with a slight delay to ensure they're not in use
            try:
                await asyncio.sleep(1)  # Use asyncio.sleep instead of time.sleep
                if os.path.exists(output_path):
                    os.unlink(output_path)
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                if os.path.exists(watermark_path):
                    os.unlink(watermark_path)
                if os.path.exists(enhanced_watermark_path) and enhanced_watermark_path != watermark_path:
                    os.unlink(enhanced_watermark_path)
            except Exception as e:
                logger.error(f"Error cleaning up files: {e}")
        else:
            await processing_msg.edit_text('Sorry, there was an error processing your image.')
    except Exception as e:
        logger.error(f"Error in handle_image: {e}")
        await processing_msg.edit_text(f"An error occurred: {str(e)}")

# Handle document uploads (for higher resolution images)
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Only process image documents
    document = update.message.document
    if not document.mime_type or not document.mime_type.startswith('image/'):
        await update.message.reply_text("Please send an image file.")
        return
        
    # Show animated processing message
    processing_msg = await animate_processing(update, context)
    
    # Download watermark each time to avoid file access issues
    watermark_path = await download_watermark()
    
    if not watermark_path:
        await processing_msg.edit_text('Sorry, there was an error with the watermark. Please try again later.')
        return
    
    # Enhance watermark with white outline for Savanro logo
    enhanced_watermark_path = await enhance_watermark_with_outline(watermark_path)
    
    try:
        # Get the document file
        doc_file = await document.get_file()
        
        # Use BytesIO to avoid file access issues
        image_bytes = BytesIO()
        await doc_file.download_to_memory(image_bytes)
        image_bytes.seek(0)
        
        # Create a unique temp file to save the image
        timestamp = int(time.time())
        temp_file_path = os.path.join(tempfile.gettempdir(), f"input_doc_{timestamp}.jpg")
        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(image_bytes.getvalue())
        
        # Add watermark
        output_path = await add_watermark(temp_file_path, enhanced_watermark_path)
        
        # Send the watermarked image back
        if output_path:
            # Delete the processing message
            await processing_msg.delete()
            
            # Send the watermarked image with buttons
            keyboard = [
                [
                    InlineKeyboardButton("Process Another", callback_data='start'),
                    InlineKeyboardButton("Clear History", callback_data='clear')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            with open(output_path, 'rb') as file:
                await update.message.reply_document(
                    document=file,
                    caption="Your image with Savanro Construction watermark ✅",
                    reply_markup=reply_markup
                )
            
            # Clean up files with a slight delay to ensure they're not in use
            try:
                await asyncio.sleep(1)  # Use asyncio.sleep instead of time.sleep
                if os.path.exists(output_path):
                    os.unlink(output_path)
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                if os.path.exists(watermark_path):
                    os.unlink(watermark_path)
                if os.path.exists(enhanced_watermark_path) and enhanced_watermark_path != watermark_path:
                    os.unlink(enhanced_watermark_path)
            except Exception as e:
                logger.error(f"Error cleaning up files: {e}")
        else:
            await processing_msg.edit_text('Sorry, there was an error processing your image.')
    except Exception as e:
        logger.error(f"Error in handle_document: {e}")
        await processing_msg.edit_text(f"An error occurred: {str(e)}")

# Command handler to adjust watermark size
async def set_watermark_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Get the size percentage from the command arguments
        args = context.args
        if not args or not args[0].isdigit() or int(args[0]) <= 0 or int(args[0]) > 100:
            await update.message.reply_text(
                "Please provide a valid size percentage between 1 and 100.\n"
                "Example: /size 40"
            )
            return
            
        global WATERMARK_WIDTH_PERCENT
        WATERMARK_WIDTH_PERCENT = int(args[0])
        
        await update.message.reply_text(
            f"Watermark size set to {WATERMARK_WIDTH_PERCENT}% of image width."
        )
    except Exception as e:
        logger.error(f"Error in set_watermark_size: {e}")
        await update.message.reply_text("An error occurred while setting the watermark size.")

# Main function to run the bot
def main() -> None:
    # Create the Application and pass it your bot's token
    application = Application.builder().token(TOKEN).build()

    # Register an error handler
    application.add_error_handler(error_handler)

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("size", set_watermark_size))

    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Add message handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()
    logger.info("Bot started. Press Ctrl+C to stop.")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")
    
    # If an update caused an error and we can reply to it
    if update and update.effective_message:
        await update.effective_message.reply_text("Sorry, something went wrong. Please try again.")

if __name__ == '__main__':
    main()
