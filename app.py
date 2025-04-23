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
        <title>Продвинутый бот анализа финансовых рынков</title>
        <style>
            body { 
                background-color: #1a1b26; 
                color: white; 
                font-family: Arial, sans-serif; 
                padding: 20px;
                max-width: 900px;
                margin: 0 auto;
                line-height: 1.6;
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
            }
            .status-card {
                background-color: #24283b;
                padding: 25px;
                border-radius: 12px;
                margin: 20px 0;
                box-shadow: 0 8px 16px rgba(0,0,0,0.2);
            }
            .features-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .feature-card {
                background-color: #2f3342;
                padding: 20px;
                border-radius: 10px;
                transition: transform 0.3s ease;
            }
            .feature-card:hover {
                transform: translateY(-5px);
            }
            .feature-title {
                font-weight: bold;
                margin-bottom: 10px;
                color: #7aa2f7;
                font-size: 18px;
            }
            .feature-icon {
                font-size: 24px;
                margin-bottom: 15px;
            }
            .currency-section {
                margin: 30px 0;
            }
            .currency-list {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }
            .currency-pair {
                background-color: #2f3342;
                padding: 8px 15px;
                border-radius: 20px;
                font-size: 14px;
            }
            .contact-section {
                margin-top: 40px;
            }
            .btn {
                display: inline-block;
                padding: 12px 25px;
                background-color: #7aa2f7;
                color: #1a1b26;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
                margin-top: 20px;
                transition: background-color 0.3s ease;
            }
            .btn:hover {
                background-color: #89b4ff;
            }
            .footer {
                margin-top: 50px;
                text-align: center;
                font-size: 14px;
                color: #565f89;
            }
            h1 {
                color: #7aa2f7;
                font-size: 2.5em;
            }
            h2 {
                color: #bb9af7;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 Продвинутый бот анализа финансовых рынков</h1>
            <p>Профессиональный помощник трейдера с точностью сигналов до 95%</p>
        </div>
        
        <div class="status-card">
            <h2>📊 Основные возможности</h2>
            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon">💹</div>
                    <div class="feature-title">Технический анализ</div>
                    <div>Полный анализ для 30+ валютных пар с высокой точностью прогнозов</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📈</div>
                    <div class="feature-title">Надёжные индикаторы</div>
                    <div>RSI, MACD, EMA и другие проверенные индикаторы для торговли</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">⚡️</div>
                    <div class="feature-title">Мгновенные сигналы</div>
                    <div>Точность до 95% на всех торговых инструментах</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📱</div>
                    <div class="feature-title">Поддержка 5 языков</div>
                    <div>Русский, Английский, Таджикский, Узбекский, Казахский</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📊</div>
                    <div class="feature-title">Подробные графики</div>
                    <div>Четкие и информативные графики с ключевыми точками входа</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">⏱</div>
                    <div class="feature-title">Разные интервалы</div>
                    <div>Анализ на таймфреймах 1, 5, 15, 30 минут для различных стратегий</div>
                </div>
            </div>
        </div>
        
        <div class="currency-section">
            <h2>💎 Валютные пары</h2>
            
            <h3>🏆 Основные пары</h3>
            <div class="currency-list">
                <div class="currency-pair">EUR/USD</div>
                <div class="currency-pair">GBP/USD</div>
                <div class="currency-pair">USD/JPY</div>
                <div class="currency-pair">USD/CHF</div>
                <div class="currency-pair">USD/CAD</div>
                <div class="currency-pair">AUD/USD</div>
                <div class="currency-pair">NZD/USD</div>
            </div>
            
            <h3>🌟 Кросс-курсы</h3>
            <div class="currency-list">
                <div class="currency-pair">EUR/GBP</div>
                <div class="currency-pair">EUR/JPY</div>
                <div class="currency-pair">GBP/JPY</div>
                <div class="currency-pair">AUD/JPY</div>
                <div class="currency-pair">EUR/AUD</div>
                <div class="currency-pair">GBP/CHF</div>
            </div>
            
            <h3>💰 Криптовалюты</h3>
            <div class="currency-list">
                <div class="currency-pair">BTC/USD</div>
                <div class="currency-pair">ETH/USD</div>
                <div class="currency-pair">XRP/USD</div>
                <div class="currency-pair">LTC/USD</div>
                <div class="currency-pair">BCH/USD</div>
            </div>
        </div>
        
        <div class="status-card contact-section">
            <h2>📱 Контакты и доступ</h2>
            <p>Бот работает в Telegram и доступен после одобрения заявки.</p>
            <p><strong>Поддержка 24/7:</strong> @tradeporu</p>
            <p><strong>Сайт:</strong> TRADEPO.RU</p>
            
            <p>Для получения доступа найдите бота в Telegram и отправьте запрос на регистрацию.</p>
            <a href="https://t.me/your_bot_username" class="btn">Перейти к боту в Telegram</a>
        </div>
        
        <div class="footer">
            <p>© 2025 Продвинутый бот анализа финансовых рынков | Все права защищены</p>
        </div>
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