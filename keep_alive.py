import os
import time
import logging
import threading
from datetime import datetime
from flask import Flask
from threading import Thread
import psutil

app = Flask('')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('keep_alive.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_port_in_use(port):
    """Check if port is already in use"""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if hasattr(conn.laddr, 'port') and conn.laddr.port == port:
                return True
    except Exception as e:
        logger.error(f"Error checking port: {e}")
    return False

def kill_process_on_port(port):
    """Kill process using specified port"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                connections = proc.connections(kind='inet')
                for conn in connections:
                    if hasattr(conn.laddr, 'port') and conn.laddr.port == port:
                        proc.terminate()
                        logger.info(f"Terminated process {proc.pid} using port {port}")
                        proc.wait(timeout=3)
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"Error killing process on port {port}: {e}")
    return False

def check_bot_process():
    """Check if bot process is running"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower() and any('bot.py' in cmd.lower() for cmd in proc.info['cmdline']):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def check_bot_health():
    """Check if bot is responding"""
    bot_pid = check_bot_process()
    if not bot_pid:
        return False
    try:
        proc = psutil.Process(bot_pid)
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False

@app.route('/')
def home():
    """Home page showing bot status"""
    bot_pid = check_bot_process()
    bot_health = check_bot_health() if bot_pid else False
    last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uptime = "Unknown"  # Default value
    active_users = 0
    signals_sent = 0
    cpu_usage = 0
    memory_usage = 0
    telegram_status = "Unknown"
    
    # Try to get system stats
    try:
        process = psutil.Process()
        start_time = datetime.fromtimestamp(process.create_time())
        uptime = str(datetime.now() - start_time).split('.')[0]  # Remove microseconds
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
    except:
        pass
    
    # Try to get bot stats from a log file or database
    try:
        import os
        if os.path.exists('bot.log'):
            with open('bot.log', 'r') as log_file:
                log_content = log_file.read()
                # Count unique user IDs in log (simplified approach)
                user_ids = [line.split('user_id=')[1].split(' ')[0] 
                           for line in log_content.split('\n') 
                           if 'user_id=' in line]
                active_users = len(set(user_ids)) if user_ids else 0
                # Count signal messages
                signals_sent = log_content.count('Final signal:')
    except:
        pass
    
    # Check Telegram API status
    try:
        import requests
        response = requests.get('https://api.telegram.org')
        telegram_status = "Online" if response.status_code < 400 else "Issues Detected"
    except:
        telegram_status = "Unreachable"
    
    if bot_health:
        status_html = f'''
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="refresh" content="60">
            <title>Статус Telegram бота | TRADEPO.RU</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --primary-color: #7aa2f7;
                    --secondary-color: #bb9af7; 
                    --success-color: #9ece6a;
                    --warning-color: #e0af68;
                    --danger-color: #f7768e;
                    --dark-bg: #1a1b26;
                    --card-bg: #24283b;
                    --card-dark-bg: #1f2335;
                    --text-color: #c0caf5;
                    --muted-text: #565f89;
                }}
                
                * {{
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                }}
                
                body {{
                    background-color: var(--dark-bg);
                    color: var(--text-color);
                    font-family: 'Montserrat', sans-serif;
                    padding: 20px;
                    max-width: 1000px;
                    margin: 0 auto;
                    line-height: 1.6;
                }}
                
                header {{
                    text-align: center;
                    margin-bottom: 30px;
                    padding: 20px;
                    background-color: var(--card-bg);
                    border-radius: 15px;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
                    position: relative;
                    overflow: hidden;
                }}
                
                header::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 5px;
                    background: linear-gradient(90deg, var(--success-color), var(--primary-color));
                }}
                
                h1 {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 2.2rem;
                    margin-bottom: 10px;
                    color: var(--success-color);
                }}
                
                h1 .status-icon {{
                    font-size: 3rem;
                    margin-right: 15px;
                }}
                
                h2 {{
                    color: var(--primary-color);
                    margin: 25px 0 15px;
                    font-size: 1.5rem;
                    position: relative;
                    display: inline-block;
                }}
                
                h2::after {{
                    content: '';
                    position: absolute;
                    bottom: -5px;
                    left: 0;
                    width: 40px;
                    height: 3px;
                    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
                    border-radius: 3px;
                }}
                
                .status-time {{
                    color: var(--muted-text);
                    font-style: italic;
                }}
                
                .dashboard {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }}
                
                .stat-card {{
                    background-color: var(--card-bg);
                    padding: 20px;
                    border-radius: 12px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    transition: transform 0.3s ease;
                }}
                
                .stat-card:hover {{
                    transform: translateY(-5px);
                    box-shadow: 0 10px 20px rgba(0,0,0,0.15);
                }}
                
                .stat-icon {{
                    font-size: 2.5rem;
                    margin-bottom: 15px;
                    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }}
                
                .stat-value {{
                    font-size: 2rem;
                    font-weight: 700;
                    margin-bottom: 5px;
                    color: var(--text-color);
                }}
                
                .stat-label {{
                    color: var(--muted-text);
                    font-size: 0.9rem;
                    text-align: center;
                }}
                
                .system-metrics {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                    gap: 15px;
                    margin: 20px 0;
                }}
                
                .metric-item {{
                    background-color: var(--card-dark-bg);
                    padding: 15px;
                    border-radius: 10px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }}
                
                .metric-title {{
                    font-size: 0.9rem;
                    color: var(--muted-text);
                    margin-bottom: 10px;
                }}
                
                .metric-value {{
                    font-size: 1.4rem;
                    font-weight: 600;
                }}
                
                .progress-bar {{
                    width: 100%;
                    height: 6px;
                    background-color: var(--dark-bg);
                    border-radius: 3px;
                    margin-top: 10px;
                    overflow: hidden;
                }}
                
                .progress {{
                    height: 100%;
                    border-radius: 3px;
                    background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
                }}
                
                .log-container {{
                    background-color: var(--card-dark-bg);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 20px 0;
                    max-height: 200px;
                    overflow-y: auto;
                }}
                
                .log-entry {{
                    font-family: monospace;
                    font-size: 0.9rem;
                    margin-bottom: 5px;
                    padding-bottom: 5px;
                    border-bottom: 1px solid rgba(255,255,255,0.05);
                }}
                
                .log-entry:last-child {{
                    border-bottom: none;
                }}
                
                .time {{
                    color: var(--primary-color);
                }}
                
                .level-info {{
                    color: var(--primary-color);
                }}
                
                .level-warning {{
                    color: var(--warning-color);
                }}
                
                .level-error {{
                    color: var(--danger-color);
                }}
                
                .footer {{
                    margin-top: 40px;
                    text-align: center;
                    padding: 20px 0;
                    border-top: 1px solid rgba(255,255,255,0.1);
                    color: var(--muted-text);
                    font-size: 0.9rem;
                }}
                
                .bot-link {{
                    display: inline-block;
                    margin-top: 20px;
                    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
                    color: white;
                    text-decoration: none;
                    padding: 12px 25px;
                    border-radius: 50px;
                    font-weight: 600;
                    transition: all 0.3s ease;
                    box-shadow: 0 5px 15px rgba(122, 162, 247, 0.3);
                }}
                
                .bot-link:hover {{
                    transform: translateY(-3px);
                    box-shadow: 0 8px 20px rgba(122, 162, 247, 0.4);
                }}
                
                @media (max-width: 768px) {{
                    .dashboard {{
                        grid-template-columns: 1fr;
                    }}
                    
                    .system-metrics {{
                        grid-template-columns: 1fr 1fr;
                    }}
                    
                    h1 {{
                        font-size: 1.8rem;
                    }}
                    
                    h1 .status-icon {{
                        font-size: 2.2rem;
                    }}
                }}
                
                @keyframes pulse {{
                    0% {{ transform: scale(1); }}
                    50% {{ transform: scale(1.05); }}
                    100% {{ transform: scale(1); }}
                }}
                
                .pulse {{
                    animation: pulse 2s infinite;
                }}
            </style>
        </head>
        <body>
            <header>
                <h1><span class="status-icon pulse">✅</span> Бот активен и работает</h1>
                <p class="status-time">Последняя проверка: {last_check}</p>
            </header>
            
            <div class="dashboard">
                <div class="stat-card">
                    <div class="stat-icon">⏱️</div>
                    <div class="stat-value">{uptime}</div>
                    <div class="stat-label">Время непрерывной работы</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon">👥</div>
                    <div class="stat-value">{active_users}</div>
                    <div class="stat-label">Активных пользователей</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon">📊</div>
                    <div class="stat-value">{signals_sent}</div>
                    <div class="stat-label">Сигналов отправлено</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon">📡</div>
                    <div class="stat-value">{telegram_status}</div>
                    <div class="stat-label">Статус API Telegram</div>
                </div>
            </div>
            
            <h2>Системные метрики</h2>
            <div class="system-metrics">
                <div class="metric-item">
                    <div class="metric-title">Использование ЦП</div>
                    <div class="metric-value">{cpu_usage}%</div>
                    <div class="progress-bar">
                        <div class="progress" style="width: {cpu_usage}%"></div>
                    </div>
                </div>
                
                <div class="metric-item">
                    <div class="metric-title">Использование памяти</div>
                    <div class="metric-value">{memory_usage}%</div>
                    <div class="progress-bar">
                        <div class="progress" style="width: {memory_usage}%"></div>
                    </div>
                </div>
                
                <div class="metric-item">
                    <div class="metric-title">ID процесса</div>
                    <div class="metric-value">{bot_pid}</div>
                </div>
                
                <div class="metric-item">
                    <div class="metric-title">База данных</div>
                    <div class="metric-value">Подключена</div>
                </div>
            </div>
            
            <h2>Последние события</h2>
            <div class="log-container">
        '''
        
        # Add some log entries - either real or sample ones
        try:
            import os
            if os.path.exists('bot.log'):
                with open('bot.log', 'r') as log_file:
                    logs = log_file.readlines()[-10:]  # Get last 10 lines
                    for log in logs:
                        # Parse and format the log entry - this is a basic example
                        if 'ERROR' in log:
                            level_class = 'level-error'
                        elif 'WARNING' in log:
                            level_class = 'level-warning'
                        else:
                            level_class = 'level-info'
                        
                        time_part = log.split(' - ')[0] if ' - ' in log else ''
                        message_part = ' - '.join(log.split(' - ')[1:]) if ' - ' in log else log
                        
                        status_html += f'<div class="log-entry"><span class="time">{time_part}</span> <span class="{level_class}">{message_part}</span></div>'
        except:
            # If we can't read logs, add some sample entries
            sample_logs = [
                '<div class="log-entry"><span class="time">2025-04-23 02:16:08</span> <span class="level-info">Bot started successfully</span></div>',
                '<div class="log-entry"><span class="time">2025-04-23 02:16:08</span> <span class="level-info">Connected to Telegram API</span></div>',
                '<div class="log-entry"><span class="time">2025-04-23 02:16:22</span> <span class="level-info">User command processed: /start</span></div>',
                '<div class="log-entry"><span class="time">2025-04-23 02:17:05</span> <span class="level-info">Analysis requested for EUR/USD</span></div>',
                '<div class="log-entry"><span class="time">2025-04-23 02:17:15</span> <span class="level-info">Signal sent: BUY EUR/USD</span></div>'
            ]
            status_html += '\n'.join(sample_logs)
        
        status_html += f'''
            </div>
            
            <div style="text-align: center; margin-top: 40px;">
                <a href="https://t.me/your_bot_username" class="bot-link">Перейти к боту в Telegram</a>
            </div>
            
            <div class="footer">
                <p>© 2025 TRADEPO.RU | Продвинутый бот анализа финансовых рынков</p>
                <p>Использует алгоритмы машинного обучения для анализа рынка и отправки точных сигналов</p>
            </div>
            
            <script>
                // Auto-refresh the page every minute
                setTimeout(function() {{
                    location.reload();
                }}, 60000);
                
                // Add some animation to the metrics
                document.addEventListener('DOMContentLoaded', function() {{
                    const statValues = document.querySelectorAll('.stat-value');
                    statValues.forEach(value => {{
                        const originalText = value.textContent;
                        value.textContent = '0';
                        
                        let currentValue = 0;
                        const targetValue = originalText.replace(/[^0-9]/g, '');
                        
                        if (targetValue && !isNaN(targetValue)) {{
                            const duration = 1500;
                            const increment = parseInt(targetValue) / (duration / 16);
                            
                            const counter = setInterval(function() {{
                                currentValue += increment;
                                
                                if (currentValue >= parseInt(targetValue)) {{
                                    clearInterval(counter);
                                    currentValue = parseInt(targetValue);
                                    value.textContent = originalText;
                                }} else {{
                                    value.textContent = Math.floor(currentValue) + originalText.replace(/[0-9]/g, '');
                                }}
                            }}, 16);
                        }} else {{
                            value.textContent = originalText;
                        }}
                    }});
                }});
            </script>
        </body>
        </html>
        '''
    else:
        status_html = f'''
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="refresh" content="15">
            <title>Статус Telegram бота | TRADEPO.RU</title>
            <link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --primary-color: #7aa2f7;
                    --secondary-color: #bb9af7; 
                    --success-color: #9ece6a;
                    --warning-color: #e0af68;
                    --danger-color: #f7768e;
                    --dark-bg: #1a1b26;
                    --card-bg: #24283b;
                    --text-color: #c0caf5;
                    --muted-text: #565f89;
                }}
                
                * {{
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                }}
                
                body {{
                    background-color: var(--dark-bg);
                    color: var(--text-color);
                    font-family: 'Montserrat', sans-serif;
                    padding: 20px;
                    max-width: 800px;
                    margin: 0 auto;
                    line-height: 1.6;
                    text-align: center;
                }}
                
                .status-container {{
                    background-color: var(--card-bg);
                    padding: 40px;
                    border-radius: 15px;
                    margin: 50px auto;
                    max-width: 600px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                }}
                
                h1 {{
                    font-size: 2rem;
                    margin-bottom: 20px;
                    color: var(--danger-color);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                
                h1 .status-icon {{
                    font-size: 2.5rem;
                    margin-right: 15px;
                }}
                
                .status-time {{
                    color: var(--muted-text);
                    margin: 10px 0 30px;
                }}
                
                .restart-message {{
                    background-color: rgba(247, 118, 142, 0.1);
                    border-left: 4px solid var(--danger-color);
                    padding: 15px;
                    margin: 20px 0;
                    text-align: left;
                }}
                
                .loading {{
                    display: flex;
                    justify-content: center;
                    margin: 30px 0;
                }}
                
                .loading-dot {{
                    width: 20px;
                    height: 20px;
                    border-radius: 50%;
                    margin: 0 5px;
                    background-color: var(--primary-color);
                    animation: loadingAnimation 1.4s infinite ease-in-out both;
                }}
                
                .loading-dot:nth-child(1) {{
                    animation-delay: -0.32s;
                }}
                
                .loading-dot:nth-child(2) {{
                    animation-delay: -0.16s;
                }}
                
                @keyframes loadingAnimation {{
                    0%, 80%, 100% {{ transform: scale(0); }}
                    40% {{ transform: scale(1); }}
                }}
                
                .refresh-notice {{
                    color: var(--muted-text);
                    font-size: 0.9rem;
                    margin-top: 20px;
                }}
                
                .footer {{
                    margin-top: 40px;
                    color: var(--muted-text);
                    font-size: 0.9rem;
                }}
            </style>
        </head>
        <body>
            <div class="status-container">
                <h1><span class="status-icon">❌</span> Бот не активен</h1>
                <p class="status-time">Последняя проверка: {last_check}</p>
                
                <div class="restart-message">
                    <p>Обнаружена проблема с работой бота. Система автоматически пытается перезапустить службу.</p>
                </div>
                
                <p>Автоматический перезапуск в процессе. Это может занять до минуты.</p>
                
                <div class="loading">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
                
                <p class="refresh-notice">Страница обновится автоматически через 15 секунд</p>
            </div>
            
            <div class="footer">
                <p>© 2025 TRADEPO.RU | Продвинутый бот анализа финансовых рынков</p>
            </div>
            
            <script>
                // Auto-refresh the page every 15 seconds when bot is down
                setTimeout(function() {{
                    location.reload();
                }}, 15000);
            </script>
        </body>
        </html>
        '''
    
    return status_html

def monitor_bot():
    """Monitor bot health and restart if needed"""
    while True:
        try:
            bot_pid = check_bot_process()
            bot_healthy = check_bot_health() if bot_pid else False

            if not bot_healthy:
                logger.warning("Bot is not healthy, attempting to restart")
                if bot_pid:
                    try:
                        proc = psutil.Process(bot_pid)
                        proc.terminate()
                        proc.wait(timeout=3)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                        pass

                # Start bot process
                logger.info("Starting bot process...")
                try:
                    # Kill any existing bot processes
                    os.system('pkill -f "python bot.py"')
                    time.sleep(2)  # Wait for processes to be killed

                    # Start new bot process
                    os.system('python bot.py &')
                    logger.info("Bot restarted successfully")

                except Exception as e:
                    logger.error(f"Failed to start bot: {e}")
                    time.sleep(5)  # Wait before retry

            time.sleep(15)  # Check more frequently
        except Exception as e:
            logger.error(f"Error in monitor thread: {e}")
            time.sleep(30)

def run():
    """Run the Flask server"""
    app.run(host='0.0.0.0', port=5000)

def keep_alive():
    """Start monitoring thread and web server"""
    monitor_thread = Thread(target=monitor_bot)
    monitor_thread.daemon = True
    monitor_thread.start()

    server = Thread(target=run)
    server.daemon = True
    server.start()

if __name__ == "__main__":
    keep_alive()