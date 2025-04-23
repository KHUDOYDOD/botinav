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

# Load environment variables explicitly
logger.info("Loading environment variables from .env file")
load_dotenv()

# Установка токена напрямую, чтобы избежать проблем с переменными окружения
token = '7629015533:AAHXAGXM6XpgCmzg0keO0DTkyme78EfzK8E'
os.environ['BOT_TOKEN'] = token
logger.info(f"Установлен токен бота: {token[:10]}...")

# Исправление проблемы с forex_pairs и crypto_pairs
# Сначала импортируем CURRENCY_PAIRS
from config import CURRENCY_PAIRS

# Теперь создаем forex_pairs и crypto_pairs заново, чтобы избежать проблем с импортом
forex_pairs = {k: v for k, v in CURRENCY_PAIRS.items() if 'USD' not in k or '=X' in v}
crypto_pairs = {k: v for k, v in CURRENCY_PAIRS.items() if '-USD' in v}

# Вместо добавления переменных в __builtins__, обновим модуль config
import config
config.forex_pairs = forex_pairs
config.crypto_pairs = crypto_pairs

# Отладочный вывод
logger.info(f"Forex pairs: {list(forex_pairs.keys())[:5]}")
logger.info(f"Crypto pairs: {list(crypto_pairs.keys())[:5]}")

# Запуск бота
try:
    logger.info("Запуск телеграм бота...")
    from bot import main as run_bot
    run_bot()
except Exception as e:
    logger.error(f"Ошибка при запуске бота: {e}")
    raise