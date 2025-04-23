
import os
import logging
import dotenv
from dotenv import load_dotenv
from threading import Thread
from keep_alive import keep_alive

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    try:
        # Start keep-alive server
        keep_alive()
        
        # Import and run the bot
        from bot import main as run_bot
        logger.info("Starting bot...")
        run_bot()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
