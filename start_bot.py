import os
import logging
import sys
from dotenv import load_dotenv

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
logger.info("Loading environment variables from .env file")
load_dotenv()

# Check if the token is properly loaded
bot_token = os.environ.get('BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
if not bot_token:
    logger.error("Токен бота не найден! Устанавливаю токен напрямую...")
    # Explicitly set the token
    os.environ['BOT_TOKEN'] = '7629015533:AAHXAGXM6XpgCmzg0keO0DTkyme78EfzK8E'
    bot_token = os.environ.get('BOT_TOKEN')
    logger.info(f"Установлен токен бота: {bot_token[:10]}...")

# Import and run the bot
try:
    logger.info("Запуск телеграм бота...")
    from bot import main as run_bot
    run_bot()
except Exception as e:
    logger.error(f"Ошибка при запуске бота: {e}")
    raise