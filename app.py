
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
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="60">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Торговый бот | TRADEPO.RU</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css">
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/wow.js/1.1.2/wow.min.js"></script>
        <style>
            :root {
                --primary-color: #7aa2f7;
                --secondary-color: #bb9af7; 
                --dark-bg: #1a1b26;
                --card-bg: #24283b;
                --feature-bg: #2f3342;
                --text-color: #c0caf5;
                --muted-text: #565f89;
                --highlight: #ff9e64;
                --success: #9ece6a;
                --danger: #f7768e;
            }
            
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
            
            body { 
                background-color: var(--dark-bg); 
                color: var(--text-color); 
                font-family: 'Montserrat', sans-serif; 
                padding: 20px;
                max-width: 1100px;
                margin: 0 auto;
                line-height: 1.6;
            }
            
            .header {
                text-align: center;
                margin-bottom: 40px;
                padding: 40px 0;
                position: relative;
                overflow: hidden;
            }
            
            .header::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(135deg, rgba(122, 162, 247, 0.1) 0%, rgba(187, 154, 247, 0.1) 100%);
                border-radius: 20px;
                z-index: -1;
            }
            
            .glowing-btn {
                position: relative;
                z-index: 1;
                overflow: hidden;
            }
            
            .glowing-btn::after {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: conic-gradient(from 0deg, transparent 0%, var(--primary-color) 25%, var(--secondary-color) 50%, transparent 75%);
                opacity: 0;
                z-index: -1;
                transition: opacity 0.3s;
                animation: rotate 4s linear infinite;
            }
            
            .glowing-btn:hover::after {
                opacity: 0.15;
            }
            
            @keyframes rotate {
                100% { transform: rotate(360deg); }
            }
            
            .status-card {
                background-color: var(--card-bg);
                padding: 30px;
                border-radius: 16px;
                margin: 30px 0;
                box-shadow: 0 10px 30px rgba(0,0,0,0.25);
                position: relative;
                overflow: hidden;
            }
            
            .status-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 5px;
                background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
            }
            
            .features-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 25px;
                margin: 35px 0;
            }
            
            .feature-card {
                background-color: var(--feature-bg);
                padding: 25px;
                border-radius: 14px;
                transition: all 0.4s ease;
                border: 1px solid transparent;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                height: 100%;
                display: flex;
                flex-direction: column;
            }
            
            .feature-card:hover {
                transform: translateY(-10px);
                border-color: rgba(122, 162, 247, 0.3);
                box-shadow: 0 15px 25px rgba(0,0,0,0.2);
            }
            
            .feature-title {
                font-weight: 600;
                margin-bottom: 15px;
                color: var(--primary-color);
                font-size: 20px;
            }
            
            .feature-icon {
                font-size: 36px;
                margin-bottom: 20px;
                background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                display: inline-block;
            }
            
            .currency-section {
                margin: 40px 0;
            }
            
            .currency-list {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                margin-top: 15px;
                margin-bottom: 25px;
            }
            
            .currency-pair {
                background-color: var(--feature-bg);
                padding: 10px 20px;
                border-radius: 50px;
                font-size: 15px;
                transition: all 0.3s ease;
                border: 1px solid transparent;
            }
            
            .currency-pair:hover {
                border-color: var(--primary-color);
                transform: scale(1.05);
            }
            
            .contact-section {
                margin-top: 50px;
                position: relative;
            }
            
            .btn {
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
                color: #ffffff;
                text-decoration: none;
                border-radius: 50px;
                font-weight: 700;
                font-size: 16px;
                margin-top: 25px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(122, 162, 247, 0.4);
            }
            
            .btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 10px 20px rgba(122, 162, 247, 0.5);
            }
            
            .btn::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                transform: translateX(-100%);
            }
            
            .btn:hover::after {
                transform: translateX(100%);
                transition: transform 0.6s ease;
            }
            
            .footer {
                margin-top: 70px;
                text-align: center;
                font-size: 14px;
                color: var(--muted-text);
                padding: 30px 0;
                border-top: 1px solid rgba(86, 95, 137, 0.3);
            }
            
            h1 {
                color: #ffffff;
                font-size: 2.8em;
                margin-bottom: 15px;
                font-weight: 700;
                background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                display: inline-block;
            }
            
            h2 {
                color: var(--secondary-color);
                font-size: 1.8em;
                font-weight: 600;
                margin-bottom: 20px;
                position: relative;
                display: inline-block;
            }
            
            h2::after {
                content: '';
                position: absolute;
                bottom: -5px;
                left: 0;
                width: 40px;
                height: 3px;
                background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
                border-radius: 3px;
            }
            
            h3 {
                color: var(--highlight);
                margin: 20px 0 12px;
                font-weight: 600;
            }
            
            p {
                margin-bottom: 15px;
            }
            
            .stats-container {
                display: flex;
                justify-content: space-around;
                flex-wrap: wrap;
                margin: 30px 0;
            }
            
            .stat-item {
                text-align: center;
                padding: 0 20px;
                margin: 10px;
            }
            
            .stat-number {
                font-size: 2.5em;
                font-weight: 700;
                color: var(--primary-color);
                margin-bottom: 5px;
            }
            
            .stat-label {
                color: var(--muted-text);
                font-size: 0.9em;
            }
            
            .demo-section {
                margin: 40px 0;
                text-align: center;
            }
            
            .demo-image {
                max-width: 100%;
                border-radius: 15px;
                box-shadow: 0 15px 30px rgba(0,0,0,0.3);
                margin: 20px 0;
                border: 2px solid var(--card-bg);
            }
            
            @media (max-width: 768px) {
                body {
                    padding: 15px;
                }
                
                .features-grid {
                    grid-template-columns: 1fr;
                }
                
                h1 {
                    font-size: 2.2em;
                }
                
                .stat-item {
                    flex-basis: 45%;
                }
            }
        </style>
    </head>
    <body>
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                new WOW().init();
                
                // Добавляем классы анимации к элементам
                document.querySelectorAll('.feature-card').forEach(function(card, index) {
                    card.classList.add('wow', 'animate__animated', 'animate__fadeInUp');
                    card.setAttribute('data-wow-delay', (0.1 * index) + 's');
                });
                
                document.querySelectorAll('.stat-item').forEach(function(item, index) {
                    item.classList.add('wow', 'animate__animated', 'animate__fadeIn');
                    item.setAttribute('data-wow-delay', (0.1 * index) + 's');
                });
                
                document.querySelectorAll('.currency-pair').forEach(function(pair, index) {
                    pair.classList.add('wow', 'animate__animated', 'animate__fadeInRight');
                    pair.setAttribute('data-wow-delay', (0.05 * index) + 's');
                });
                
                document.querySelectorAll('.status-card').forEach(function(card) {
                    card.classList.add('wow', 'animate__animated', 'animate__fadeIn');
                });
                
                // Создаем эффект живого числа для статистики
                document.querySelectorAll('.stat-number').forEach(function(statEl) {
                    const targetValue = parseFloat(statEl.textContent);
                    
                    if (!isNaN(targetValue)) {
                        let currentValue = 0;
                        const duration = 2000;
                        const increment = targetValue / (duration / 16);
                        const isPercent = statEl.textContent.includes('%');
                        
                        statEl.textContent = '0' + (isPercent ? '%' : '');
                        
                        const counter = setInterval(function() {
                            currentValue += increment;
                            
                            if (currentValue >= targetValue) {
                                clearInterval(counter);
                                currentValue = targetValue;
                            }
                            
                            statEl.textContent = isPercent 
                                ? Math.floor(currentValue) + '%'
                                : currentValue.toFixed(1).replace('.0', '');
                        }, 16);
                    }
                });
            });
        </script>
        
        <div class="header wow animate__animated animate__fadeIn">
            <h1>🚀 Продвинутый бот анализа финансовых рынков</h1>
            <p>Профессиональный помощник трейдера с точностью сигналов до 95%</p>
            <a href="https://t.me/bot_username" class="btn glowing-btn wow animate__animated animate__pulse animate__infinite">Начать торговлю в Telegram</a>
        </div>
        
        <div class="stats-container">
            <div class="stat-item">
                <div class="stat-number">95%</div>
                <div class="stat-label">Точность сигналов</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">30+</div>
                <div class="stat-label">Валютных пар</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">24/7</div>
                <div class="stat-label">Торговля и поддержка</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">5</div>
                <div class="stat-label">Языков интерфейса</div>
            </div>
        </div>
        
        <div class="demo-section wow animate__animated animate__fadeIn">
            <h2>🔍 Мгновенный анализ рынка</h2>
            <p>Нейросеть анализирует десятки индикаторов и предоставляет чёткие торговые сигналы</p>
            <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin: 30px 0;">
                <div style="flex: 1 1 400px; max-width: 600px;">
                    <img src="/analysis_sample.png" alt="Пример анализа рынка" class="demo-image wow animate__animated animate__zoomIn" data-wow-delay="0.3s">
                    <p style="font-size: 14px; color: var(--muted-text); margin-top: 10px;">Детальный анализ EUR/USD с техническими индикаторами</p>
                </div>
                <div style="flex: 1 1 400px; max-width: 600px;">
                    <img src="/welcome_image.png" alt="Приветственное изображение" class="demo-image wow animate__animated animate__zoomIn" data-wow-delay="0.5s">
                    <p style="font-size: 14px; color: var(--muted-text); margin-top: 10px;">Персонализированное приветствие для пользователей бота</p>
                </div>
            </div>
            <div style="margin: 40px 0;">
                <h3 style="color: var(--primary-color);">Преимущества визуального анализа</h3>
                <ul style="list-style-type: none; padding: 0; display: flex; flex-wrap: wrap; gap: 20px; margin-top: 20px;">
                    <li style="flex: 1 1 300px; background-color: var(--feature-bg); padding: 15px; border-radius: 10px; display: flex; align-items: center;">
                        <span style="font-size: 24px; margin-right: 10px;">📊</span>
                        <span>Наглядное отображение ключевых уровней</span>
                    </li>
                    <li style="flex: 1 1 300px; background-color: var(--feature-bg); padding: 15px; border-radius: 10px; display: flex; align-items: center;">
                        <span style="font-size: 24px; margin-right: 10px;">🔍</span>
                        <span>Моментальное определение тренда</span>
                    </li>
                    <li style="flex: 1 1 300px; background-color: var(--feature-bg); padding: 15px; border-radius: 10px; display: flex; align-items: center;">
                        <span style="font-size: 24px; margin-right: 10px;">⚡</span>
                        <span>Быстрые и точные торговые сигналы</span>
                    </li>
                </ul>
            </div>
        </div>
        
        <div class="status-card">
            <h2>📊 Профессиональные инструменты</h2>
            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon">💹</div>
                    <div class="feature-title">Технический анализ</div>
                    <div>Полный анализ для 30+ валютных пар с высокой точностью прогнозов на любом таймфрейме</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📈</div>
                    <div class="feature-title">Надёжные индикаторы</div>
                    <div>RSI, MACD, EMA, Bollinger Bands и другие проверенные индикаторы для максимальной прибыли</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">⚡️</div>
                    <div class="feature-title">Мгновенные сигналы</div>
                    <div>Точность до 95% на всех торговых инструментах с уведомлениями в реальном времени</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📱</div>
                    <div class="feature-title">Мультиязычность</div>
                    <div>Русский, Английский, Таджикский, Узбекский, Казахский - для трейдеров со всего мира</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📊</div>
                    <div class="feature-title">Детальные графики</div>
                    <div>Четкие и информативные графики с ключевыми точками входа и уровнями поддержки/сопротивления</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">⏱</div>
                    <div class="feature-title">Гибкие таймфреймы</div>
                    <div>Анализ на таймфреймах 1, 5, 15, 30 минут для краткосрочных и среднесрочных стратегий</div>
                </div>
            </div>
        </div>
        
        <div class="status-card">
            <h2>📱 Как использовать бота</h2>
            <ol style="margin: 20px 0; padding-left: 25px;">
                <li style="margin-bottom: 15px;">Найдите бота в Telegram по имени @bot_username</li>
                <li style="margin-bottom: 15px;">Отправьте запрос на регистрацию с помощью команды /register</li>
                <li style="margin-bottom: 15px;">После подтверждения выберите предпочитаемый язык интерфейса</li>
                <li style="margin-bottom: 15px;">Выберите интересующую вас валютную пару для анализа</li>
                <li style="margin-bottom: 15px;">Получите мгновенный анализ рынка с точными сигналами для торговли</li>
            </ol>
        </div>
        
        <div class="currency-section wow animate__animated animate__fadeIn">
            <h2>💎 Доступные торговые инструменты</h2>
            
            <div style="margin: 30px auto; text-align: center;">
                <div style="display: inline-block; position: relative; z-index: 10;">
                    <button id="select-currency-btn" style="background: linear-gradient(135deg, var(--primary-color), var(--secondary-color)); color: white; border: none; padding: 14px 30px; border-radius: 50px; font-weight: 600; font-size: 16px; cursor: pointer; box-shadow: 0 5px 15px rgba(122, 162, 247, 0.4); transition: all 0.3s ease;">
                        Выбрать валютную пару для анализа
                    </button>
                    <div id="currency-dropdown" style="display: none; position: absolute; top: 100%; left: 0; width: 100%; max-height: 300px; overflow-y: auto; background-color: var(--card-bg); margin-top: 10px; border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); z-index: 100;">
                        <div style="padding: 15px;">
                            <input type="text" id="currency-search" placeholder="Поиск валютной пары..." style="width: 100%; padding: 10px; border-radius: 5px; border: 1px solid var(--primary-color); background-color: var(--feature-bg); color: var(--text-color); margin-bottom: 10px;">
                            
                            <div id="currency-list" style="display: grid; grid-template-columns: 1fr; gap: 5px;">
                                <!-- Форекс пары -->
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">💶</span>EUR/USD
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">💷</span>GBP/USD
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">💴</span>USD/JPY
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">💰</span>USD/CHF
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">🍁</span>USD/CAD
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">🦘</span>AUD/USD
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">🥝</span>NZD/USD
                                </div>
                                
                                <!-- Кросс-курсы -->
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">💶💷</span>EUR/GBP
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">💶💴</span>EUR/JPY
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">💷💴</span>GBP/JPY
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">🦘💴</span>AUD/JPY
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">💶🦘</span>EUR/AUD
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">💷💰</span>GBP/CHF
                                </div>
                                
                                <!-- Криптовалюты -->
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">₿</span>BTC/USD
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">⟠</span>ETH/USD
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">✨</span>XRP/USD
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">◎</span>SOL/USD
                                </div>
                                <div class="currency-select-item" style="padding: 10px; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center;">
                                    <span style="margin-right: 10px;">🐕</span>DOGE/USD
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                document.addEventListener('DOMContentLoaded', function() {
                    const selectCurrencyBtn = document.getElementById('select-currency-btn');
                    const currencyDropdown = document.getElementById('currency-dropdown');
                    const currencySearch = document.getElementById('currency-search');
                    const currencyItems = document.querySelectorAll('.currency-select-item');
                    
                    // Показать/скрыть выпадающий список
                    selectCurrencyBtn.addEventListener('click', function() {
                        if (currencyDropdown.style.display === 'none') {
                            currencyDropdown.style.display = 'block';
                            setTimeout(() => {
                                currencySearch.focus();
                            }, 100);
                        } else {
                            currencyDropdown.style.display = 'none';
                        }
                    });
                    
                    // Закрыть выпадающий список при клике вне его
                    document.addEventListener('click', function(event) {
                        if (!event.target.closest('#currency-dropdown') && 
                            !event.target.closest('#select-currency-btn')) {
                            currencyDropdown.style.display = 'none';
                        }
                    });
                    
                    // Функционал поиска
                    currencySearch.addEventListener('input', function() {
                        const searchTerm = currencySearch.value.toLowerCase();
                        currencyItems.forEach(item => {
                            const text = item.textContent.toLowerCase();
                            if (text.includes(searchTerm)) {
                                item.style.display = 'flex';
                            } else {
                                item.style.display = 'none';
                            }
                        });
                    });
                    
                    // Подсветка при наведении
                    currencyItems.forEach(item => {
                        item.addEventListener('mouseover', function() {
                            this.style.backgroundColor = 'var(--feature-bg)';
                        });
                        
                        item.addEventListener('mouseout', function() {
                            this.style.backgroundColor = 'transparent';
                        });
                        
                        // Выбор валютной пары
                        item.addEventListener('click', function() {
                            try {
                                const pairText = this.textContent.trim();
                                selectCurrencyBtn.textContent = 'Выбрано: ' + pairText;
                                currencyDropdown.style.display = 'none';
                                
                                // Анимируем кнопку
                                selectCurrencyBtn.classList.add('animate__animated', 'animate__pulse');
                                setTimeout(() => {
                                    selectCurrencyBtn.classList.remove('animate__animated', 'animate__pulse');
                                }, 1000);
                                
                                // Получаем только символ валютной пары без эмодзи
                                const pairSymbol = pairText.replace(/[^\w\/]/g, '');
                                
                                // Создаем ссылку для открытия бота с выбранной парой
                                const botLink = `https://t.me/your_bot_username?start=analyze_${pairSymbol}`;
                                
                                // Выводим сообщение об успешном выборе
                                const successMessage = document.createElement('div');
                                successMessage.style.position = 'fixed';
                                successMessage.style.top = '20px';
                                successMessage.style.left = '50%';
                                successMessage.style.transform = 'translateX(-50%)';
                                successMessage.style.padding = '15px 25px';
                                successMessage.style.backgroundColor = 'var(--success-color)';
                                successMessage.style.color = '#ffffff';
                                successMessage.style.borderRadius = '8px';
                                successMessage.style.boxShadow = '0 5px 15px rgba(0,0,0,0.2)';
                                successMessage.style.zIndex = '1000';
                                successMessage.innerHTML = `Выбрана пара: <strong>${pairText}</strong>`;
                                document.body.appendChild(successMessage);
                                
                                // Удаляем сообщение через 3 секунды
                                setTimeout(() => {
                                    successMessage.style.opacity = '0';
                                    successMessage.style.transition = 'opacity 0.5s ease';
                                    setTimeout(() => {
                                        document.body.removeChild(successMessage);
                                    }, 500);
                                }, 3000);
                                
                                // Создаем кнопку для перехода в Telegram
                                const telegramButton = document.createElement('a');
                                telegramButton.href = botLink;
                                telegramButton.target = '_blank';
                                telegramButton.className = 'btn glowing-btn wow animate__animated animate__fadeIn';
                                telegramButton.style.display = 'inline-block';
                                telegramButton.style.marginTop = '20px';
                                telegramButton.textContent = `Анализировать ${pairText} в Telegram`;
                                
                                // Найдем место для вставки кнопки
                                const currencySection = document.querySelector('.currency-section');
                                if (currencySection) {
                                    // Проверяем, есть ли уже кнопка
                                    const existingButton = currencySection.querySelector('.analyze-button-container');
                                    if (existingButton) {
                                        existingButton.innerHTML = '';
                                        existingButton.appendChild(telegramButton);
                                    } else {
                                        const buttonContainer = document.createElement('div');
                                        buttonContainer.className = 'analyze-button-container';
                                        buttonContainer.style.textAlign = 'center';
                                        buttonContainer.style.margin = '30px 0';
                                        buttonContainer.appendChild(telegramButton);
                                        
                                        // Безопасная вставка кнопки
                                        if (currencySection.querySelector('h3')) {
                                            // Если есть заголовок h3, вставляем перед ним
                                            currencySection.insertBefore(buttonContainer, currencySection.querySelector('h3'));
                                        } else {
                                            // Если заголовка нет, просто добавляем в конец секции
                                            currencySection.appendChild(buttonContainer);
                                        }
                                    }
                                }
                            } catch (error) {
                                console.error('Ошибка при выборе валютной пары:', error);
                                
                                // Выводим сообщение об ошибке
                                const errorMessage = document.createElement('div');
                                errorMessage.style.position = 'fixed';
                                errorMessage.style.top = '20px';
                                errorMessage.style.left = '50%';
                                errorMessage.style.transform = 'translateX(-50%)';
                                errorMessage.style.padding = '15px 25px';
                                errorMessage.style.backgroundColor = 'var(--danger-color)';
                                errorMessage.style.color = '#ffffff';
                                errorMessage.style.borderRadius = '8px';
                                errorMessage.style.boxShadow = '0 5px 15px rgba(0,0,0,0.2)';
                                errorMessage.style.zIndex = '1000';
                                errorMessage.innerHTML = 'Не удалось выбрать валютную пару. Пожалуйста, попробуйте еще раз.';
                                document.body.appendChild(errorMessage);
                                
                                // Удаляем сообщение через 3 секунды
                                setTimeout(() => {
                                    errorMessage.style.opacity = '0';
                                    errorMessage.style.transition = 'opacity 0.5s ease';
                                    setTimeout(() => {
                                        document.body.removeChild(errorMessage);
                                    }, 500);
                                }, 3000);
                            }
                        });
                    });
                });
            </script>
            
            <h3 style="margin-top: 50px;">🏆 Основные валютные пары</h3>
            <div class="currency-list">
                <div class="currency-pair">💶 EUR/USD</div>
                <div class="currency-pair">💷 GBP/USD</div>
                <div class="currency-pair">💴 USD/JPY</div>
                <div class="currency-pair">💰 USD/CHF</div>
                <div class="currency-pair">🍁 USD/CAD</div>
                <div class="currency-pair">🦘 AUD/USD</div>
                <div class="currency-pair">🥝 NZD/USD</div>
            </div>
            
            <h3>🌟 Кросс-курсы</h3>
            <div class="currency-list">
                <div class="currency-pair">💶💷 EUR/GBP</div>
                <div class="currency-pair">💶💴 EUR/JPY</div>
                <div class="currency-pair">💷💴 GBP/JPY</div>
                <div class="currency-pair">🦘💴 AUD/JPY</div>
                <div class="currency-pair">💶🦘 EUR/AUD</div>
                <div class="currency-pair">💷💰 GBP/CHF</div>
            </div>
            
            <h3>💰 Криптовалюты</h3>
            <div class="currency-list">
                <div class="currency-pair">₿ BTC/USD</div>
                <div class="currency-pair">⟠ ETH/USD</div>
                <div class="currency-pair">✨ XRP/USD</div>
                <div class="currency-pair">◎ SOL/USD</div>
                <div class="currency-pair">🐕 DOGE/USD</div>
            </div>
        </div>
        
        <div class="status-card">
            <h2>💼 Преимущества для профессиональных трейдеров</h2>
            <div class="features-grid">
                <div class="feature-card">
                    <div class="feature-icon">🔄</div>
                    <div class="feature-title">Автоматический анализ</div>
                    <div>Анализ рынка происходит автоматически каждые несколько минут, обеспечивая актуальность данных</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📊</div>
                    <div class="feature-title">Многофакторный анализ</div>
                    <div>Комплексная оценка рынка по более чем 10 различным индикаторам и алгоритмам</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🧠</div>
                    <div class="feature-title">Образовательный раздел</div>
                    <div>Полезные материалы для начинающих трейдеров и профессионалов</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">📱</div>
                    <div class="feature-title">Мобильный доступ</div>
                    <div>Получайте сигналы в любой точке мира через Telegram на вашем смартфоне</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">🔒</div>
                    <div class="feature-title">Безопасность</div>
                    <div>Конфиденциальность ваших данных и высокий уровень шифрования</div>
                </div>
                <div class="feature-card">
                    <div class="feature-icon">💬</div>
                    <div class="feature-title">Персональная поддержка</div>
                    <div>Индивидуальная консультация от опытных трейдеров 24/7</div>
                </div>
            </div>
        </div>
        
        <div class="status-card">
            <h2>📖 Образовательные материалы</h2>
            <p>Наш бот предоставляет доступ к образовательным ресурсам прямо в Telegram через удобное меню.</p>
            
            <div style="margin: 30px 0;">
                <h3 style="color: var(--primary-color); margin-bottom: 15px;">📚 Библиотека знаний</h3>
                <div class="features-grid" style="grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));">
                    <div class="feature-card">
                        <div class="feature-title">📗 Для начинающих</div>
                        <div>Основы рынка Форекс и криптовалют</div>
                        <div>Базовые стратегии торговли</div>
                        <div>Управление рисками</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-title">📘 Продвинутый уровень</div>
                        <div>Технический анализ</div>
                        <div>Волновая теория Эллиотта</div>
                        <div>Паттерны японских свечей</div>
                    </div>
                    <div class="feature-card">
                        <div class="feature-title">📙 Стратегии торговли</div>
                        <div>Скальпинг и дейтрейдинг</div>
                        <div>Позиционная торговля</div>
                        <div>Алгоритмические стратегии</div>
                    </div>
                </div>
            </div>
            
            <div style="margin: 40px 0;">
                <h3 style="color: var(--primary-color); margin-bottom: 15px;">🎓 Видеокурсы и вебинары</h3>
                <p>Доступ к эксклюзивным обучающим видеоматериалам и регулярным вебинарам от опытных трейдеров.</p>
                <ul style="list-style-type: none; margin: 20px 0; padding: 0;">
                    <li style="margin-bottom: 10px; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: var(--secondary-color);">✓</span>
                        Еженедельные разборы рыночных событий
                    </li>
                    <li style="margin-bottom: 10px; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: var(--secondary-color);">✓</span>
                        Мастер-классы по использованию индикаторов
                    </li>
                    <li style="margin-bottom: 10px; padding-left: 25px; position: relative;">
                        <span style="position: absolute; left: 0; color: var(--secondary-color);">✓</span>
                        Психология трейдинга и управление эмоциями
                    </li>
                </ul>
            </div>
        </div>
        
        <div class="status-card">
            <h2>❓ Часто задаваемые вопросы</h2>
            
            <div style="margin: 20px 0;">
                <div style="margin-bottom: 25px;">
                    <h3 style="color: var(--primary-color); font-size: 18px; margin-bottom: 10px;">Какова точность сигналов бота?</h3>
                    <p>Алгоритм анализа обеспечивает точность сигналов до 95% в зависимости от рыночных условий. Каждый сигнал сопровождается уровнем уверенности и подробным анализом.</p>
                </div>
                
                <div style="margin-bottom: 25px;">
                    <h3 style="color: var(--primary-color); font-size: 18px; margin-bottom: 10px;">Как получить доступ к боту?</h3>
                    <p>Для получения доступа необходимо найти бота в Telegram, отправить запрос на регистрацию и дождаться подтверждения от администратора. После этого вы получите полный доступ ко всем функциям.</p>
                </div>
                
                <div style="margin-bottom: 25px;">
                    <h3 style="color: var(--primary-color); font-size: 18px; margin-bottom: 10px;">На каких языках доступен бот?</h3>
                    <p>Бот поддерживает 5 языков: русский, английский, таджикский, узбекский и казахский. Вы можете выбрать предпочитаемый язык в настройках.</p>
                </div>
                
                <div style="margin-bottom: 25px;">
                    <h3 style="color: var(--primary-color); font-size: 18px; margin-bottom: 10px;">Есть ли ограничения на количество запросов?</h3>
                    <p>Нет, вы можете запрашивать анализ любой доступной валютной пары неограниченное количество раз. Рекомендуемый интервал между запросами - не менее 5 минут для получения актуальных данных.</p>
                </div>
                
                <div style="margin-bottom: 25px;">
                    <h3 style="color: var(--primary-color); font-size: 18px; margin-bottom: 10px;">Можно ли использовать бота для алгоритмической торговли?</h3>
                    <p>Да, сигналы бота могут использоваться для автоматизированной торговли. API для интеграции доступен по запросу для премиум-пользователей.</p>
                </div>
            </div>
        </div>
        
        <div class="status-card">
            <h2>🔍 Как работает анализ рынка</h2>
            
            <p style="margin: 20px 0;">Наша система анализирует рынок, используя комплексный подход, включающий следующие компоненты:</p>
            
            <div style="display: flex; flex-wrap: wrap; gap: 15px; margin: 25px 0;">
                <div style="flex: 1 1 300px; background-color: var(--feature-bg); padding: 20px; border-radius: 12px;">
                    <h3 style="color: var(--highlight); margin-bottom: 15px;">Технический анализ</h3>
                    <ul style="list-style-type: none; padding: 0;">
                        <li style="margin-bottom: 8px; padding-left: 20px; position: relative;">
                            <span style="position: absolute; left: 0; color: var(--primary-color);">•</span>
                            Анализ трендов и ключевых уровней
                        </li>
                        <li style="margin-bottom: 8px; padding-left: 20px; position: relative;">
                            <span style="position: absolute; left: 0; color: var(--primary-color);">•</span>
                            Индикаторы RSI, MACD, Bollinger Bands
                        </li>
                        <li style="margin-bottom: 8px; padding-left: 20px; position: relative;">
                            <span style="position: absolute; left: 0; color: var(--primary-color);">•</span>
                            Свечные паттерны и формации
                        </li>
                    </ul>
                </div>
                
                <div style="flex: 1 1 300px; background-color: var(--feature-bg); padding: 20px; border-radius: 12px;">
                    <h3 style="color: var(--highlight); margin-bottom: 15px;">Объемный анализ</h3>
                    <ul style="list-style-type: none; padding: 0;">
                        <li style="margin-bottom: 8px; padding-left: 20px; position: relative;">
                            <span style="position: absolute; left: 0; color: var(--primary-color);">•</span>
                            Изучение объемов торгов
                        </li>
                        <li style="margin-bottom: 8px; padding-left: 20px; position: relative;">
                            <span style="position: absolute; left: 0; color: var(--primary-color);">•</span>
                            Дивергенции цены и объема
                        </li>
                        <li style="margin-bottom: 8px; padding-left: 20px; position: relative;">
                            <span style="position: absolute; left: 0; color: var(--primary-color);">•</span>
                            Анализ ликвидности рынка
                        </li>
                    </ul>
                </div>
                
                <div style="flex: 1 1 300px; background-color: var(--feature-bg); padding: 20px; border-radius: 12px;">
                    <h3 style="color: var(--highlight); margin-bottom: 15px;">Алгоритмический подход</h3>
                    <ul style="list-style-type: none; padding: 0;">
                        <li style="margin-bottom: 8px; padding-left: 20px; position: relative;">
                            <span style="position: absolute; left: 0; color: var(--primary-color);">•</span>
                            Многофакторный анализ данных
                        </li>
                        <li style="margin-bottom: 8px; padding-left: 20px; position: relative;">
                            <span style="position: absolute; left: 0; color: var(--primary-color);">•</span>
                            Расчет вероятности движения
                        </li>
                        <li style="margin-bottom: 8px; padding-left: 20px; position: relative;">
                            <span style="position: absolute; left: 0; color: var(--primary-color);">•</span>
                            Адаптивный алгоритм к рыночным условиям
                        </li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="status-card contact-section">
            <h2>📱 Контакты и доступ</h2>
            <p>Бот работает в Telegram и доступен после одобрения заявки администратором.</p>
            
            <div style="display: flex; flex-wrap: wrap; justify-content: space-between; margin: 30px 0;">
                <div style="flex: 1 1 300px; margin-bottom: 20px;">
                    <h3 style="color: var(--highlight); margin-bottom: 15px;">Связаться с нами</h3>
                    <p><strong>Поддержка 24/7:</strong> @tradeporu</p>
                    <p><strong>Официальный сайт:</strong> TRADEPO.RU</p>
                    <p><strong>Электронная почта:</strong> support@tradepo.ru</p>
                </div>
                
                <div style="flex: 1 1 300px; margin-bottom: 20px;">
                    <h3 style="color: var(--highlight); margin-bottom: 15px;">Режим работы</h3>
                    <p>Бот работает круглосуточно, 7 дней в неделю</p>
                    <p>Техническое обслуживание: каждый понедельник с 03:00 до 04:00 МСК</p>
                </div>
            </div>
            
            <p style="font-size: 18px; margin: 25px 0; font-weight: 600; text-align: center;">Начните торговлю с профессиональным инструментом анализа и получайте точные сигналы прямо сейчас!</p>
            <div style="text-align: center;">
                <a href="https://t.me/your_bot_username" class="btn glowing-btn">Начать торговлю в Telegram</a>
            </div>
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
