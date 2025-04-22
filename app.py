import os
import logging
import flask
from flask import Flask
import dotenv
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask application
app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="60">
        <title>Forex Analysis Bot</title>
        <style>
            body { 
                background-color: #1a1b26; 
                color: white; 
                font-family: Arial, sans-serif; 
                padding: 20px;
                max-width: 800px;
                margin: 0 auto;
            }
            .status-card {
                background-color: #24283b;
                padding: 20px;
                border-radius: 10px;
                margin: 10px 0;
            }
            .metric {
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #414868;
            }
            .metric:last-child {
                border-bottom: none;
            }
        </style>
    </head>
    <body>
        <h1>Forex Analysis Telegram Bot</h1>
        <div class="status-card">
            <div class="metric">
                <span>Статус:</span>
                <span>Бот запущен и доступен через Telegram</span>
            </div>
            <div class="metric">
                <span>Доступные функции:</span>
                <span>Анализ рынка, технические индикаторы, многоязычность</span>
            </div>
            <div class="metric">
                <span>Поддержка:</span>
                <span>@tradeporu</span>
            </div>
        </div>
        <p>Бот работает в Telegram. Для получения доступа найдите бота по его имени и отправьте запрос на регистрацию.</p>
    </body>
    </html>
    '''

# Start the bot in a separate thread if this file is run directly
if __name__ == '__main__':
    from threading import Thread
    from bot import main as run_bot
    import time
    
    # Run the bot in a separate thread
    bot_thread = Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Run the web server
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))