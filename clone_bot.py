import os
import logging
from dotenv import load_dotenv
from threading import Thread
from bot import main as run_bot

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    try:
        # Run the bot in the main thread
        logger.info("Starting Telegram bot...")
        run_bot()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")