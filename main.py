import os
import logging
import dotenv
from dotenv import load_dotenv
import flask
from flask import Flask
from threading import Thread

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import app from app.py
from app import app

# Start the bot in a background thread if this is the main module
if __name__ == "__main__":
    try:
        # Import and run the bot in a separate thread
        from bot import main as run_bot
        bot_thread = Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        # Start Flask app if not being run by gunicorn
        # Use a different port for Flask to avoid conflict with bot
        app.run(host='0.0.0.0', port=int(os.environ.get('FLASK_PORT', 8080)))
    except Exception as e:
        logger.error(f"Error starting bot: {e}")