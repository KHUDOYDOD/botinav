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
    status = "✅ Bot is running and healthy" if bot_health else "⚠️ Bot is running but not responding" if bot_pid else "❌ Bot is not running"

    return f"""
    <html>
        <head>
            <title>Bot Status</title>
            <meta http-equiv="refresh" content="30">
        </head>
        <body>
            <h1>{status}</h1>
            <p>Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </body>
    </html>
    """

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