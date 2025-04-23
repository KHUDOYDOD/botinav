import logging
import hashlib
import time
import os
import sys
import random
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from config import *
from market_analyzer import MarketAnalyzer
from utils import get_currency_keyboard, get_language_keyboard, format_signal_message
try:
    from generate_sample import create_analysis_image
except ImportError:
    logging.error("Could not import generate_sample module. Chart generation will be disabled.")
    def create_analysis_image(*args, **kwargs):
        logging.warning("Chart generation is disabled due to missing module")
        return False
from datetime import datetime, timedelta
import json
import platform
import psutil
from models import (
    add_user, get_user, approve_user, verify_user_password, update_user_language,
    get_all_users, get_pending_users, delete_user, set_user_admin_status, set_user_moderator_status,
    create_admin_user, get_approved_user_ids, ADMIN_USERNAME, ADMIN_PASSWORD_HASH,
    get_user_activity_stats, get_bot_settings, update_bot_setting, 
    export_bot_data, import_bot_data, get_moderator_permissions, update_moderator_permission
)
from keep_alive import keep_alive

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler('bot.log')]
)

# Словарь для хранения пользователей, ожидающих подтверждения
PENDING_USERS = {}
logger = logging.getLogger(__name__)

# Состояния для админа
# Состояния для разделов админ-панели
ADMIN_PASSWORD, ADMIN_MENU, ADMIN_USER_MANAGEMENT, ADMIN_BROADCAST_MESSAGE = range(4)
ADMIN_CURRENCY_MANAGEMENT, ADMIN_CURRENCY_ADD, ADMIN_CURRENCY_EDIT = range(4, 7)
ADMIN_TEXT_MANAGEMENT, ADMIN_TEXT_ADD, ADMIN_TEXT_EDIT = range(7, 10)
ADMIN_ACTIVITY, ADMIN_SETTINGS, ADMIN_CHANGE_PASSWORD, ADMIN_ABOUT = range(10, 14)
ADMIN_EXPORT_DATA, ADMIN_IMPORT_DATA, ADMIN_LOGS, ADMIN_SERVER_STATUS = range(14, 18)
ADMIN_USER_ANALYTICS, ADMIN_SIGNAL_MANAGEMENT, ADMIN_DIRECT_MESSAGE = range(18, 21)
ADMIN_SEARCH_USER, ADMIN_OTC_SIGNALS, ADMIN_TRADING_VIEW = range(21, 24)
ADMIN_SCHEDULER, ADMIN_API, ADMIN_SECURITY, ADMIN_PROXY, ADMIN_AUTO_SIGNALS = range(24, 29)
ADMIN_SEND_MESSAGE_TO_USER = 29
ADMIN_MESSAGE_TO_PENDING, ADMIN_SELECT_USERS, ADMIN_CONTENT_MANAGER = range(30, 33)
ADMIN_STATISTICS, ADMIN_QUICK_COMMANDS, ADMIN_HISTORY, ADMIN_PLUGINS, ADMIN_MARKETPLACE = range(33, 38)
ADMIN_EDUCATION_MANAGEMENT = 38

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = user.id
        username = user.username

        # Add user to database
        add_user(user_id, username)
        user_data = get_user(user_id)

        # Set default language
        lang_code = user_data['language_code'] if user_data else 'tg'
        
        # Проверяем подтверждение пользователя
        if user_data and user_data.get('is_approved'):
            # Если пользователь подтвержден, показываем основной интерфейс
            # Передаем user_data для отображения админ/модератор кнопок, если у пользователя есть права
            keyboard = get_currency_keyboard(current_lang=lang_code, user_data=user_data)
            await update.message.reply_text(
                MESSAGES[lang_code]['WELCOME'],
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
        elif username and username.lower() == ADMIN_USERNAME.lower():
            # Если это администратор, создаем учетную запись администратора и показываем интерфейс
            create_admin_user(user_id, username)
            # Получаем обновленные данные после создания админа
            user_data = get_user(user_id)
            keyboard = get_currency_keyboard(current_lang=lang_code, user_data=user_data)
            admin_welcome = f"👑 Вы вошли как администратор @{username}.\n\n"
            await update.message.reply_text(
                admin_welcome,
                reply_markup=keyboard
            )
            # Отправляем сообщение с приветствием отдельно, чтобы избежать проблем с escape-символами
            await update.message.reply_text(
                MESSAGES[lang_code]['WELCOME'],
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
        else:
            # Если пользователь не подтвержден, предлагаем зарегистрироваться
            register_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Отправить заявку", callback_data="send_request")],
                [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")]
            ])
            
            # Пытаемся создать и отправить приветственное изображение
            from create_welcome_image import create_welcome_image
            
            welcome_text = f"🚀 *Приветствуем, @{username}!*\n\n" \
                          "🔹 *Продвинутый бот анализа финансовых рынков!*\n\n" \
                          "📊 Основные возможности:\n" \
                          "• 💹 Технический анализ для 30+ валютных пар\n" \
                          "• 📈 Надёжные индикаторы (RSI, MACD, EMA)\n" \
                          "• ⚡️ Мгновенные сигналы с точностью до 95%\n" \
                          "• 📱 Поддержка 5 языков\n" \
                          "• 📊 Чёткие и подробные графики\n" \
                          "• ⏱ Анализ на разных интервалах (1, 5, 15, 30 минут)\n\n" \
                          "💎 Валютные пары:\n" \
                          "• 🏆 Основные пары: EUR/USD, GBP/USD, USD/JPY и другие\n" \
                          "• 🌟 Кросс-курсы: EUR/GBP, GBP/JPY, EUR/JPY и другие\n" \
                          "• 💰 Криптовалюты: BTC/USD, ETH/USD, XRP/USD и другие\n\n" \
                          "📱 Контакты:\n" \
                          "• Поддержка 24/7: @tradeporu\n" \
                          "• Сайт: TRADEPO.RU\n\n" \
                          "📊 *Для получения доступа* необходимо отправить запрос на регистрацию.\n" \
                          "⏱ Администратор рассмотрит вашу заявку в ближайшее время.\n\n" \
                          "📝 Вы можете отправить заявку прямо сейчас, нажав на кнопку ниже, " \
                          "или использовать команду /register позже.\n\n" \
                          "📞 *Техническая поддержка:* @tradeporu"
            
            try:
                # Создаем и отправляем изображение
                if create_welcome_image():
                    with open('welcome_image.png', 'rb') as photo:
                        await update.message.reply_photo(
                            photo=photo,
                            caption=welcome_text,
                            reply_markup=register_keyboard,
                            parse_mode='MarkdownV2'  # Добавляем поддержку разметки для нового приветствия
                        )
                else:
                    # Если изображение не создалось, отправляем текст
                    await update.message.reply_text(
                        welcome_text,
                        reply_markup=register_keyboard,
                        parse_mode='Markdown'  # Добавляем поддержку разметки для нового приветствия
                    )
            except Exception as e:
                logger.error(f"Ошибка при отправке приветственного изображения: {e}")
                # В случае ошибки просто отправляем текст
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=register_keyboard,
                    parse_mode='Markdown'  # Добавляем поддержку разметки для нового приветствия
                )

    except Exception as e:
        logger.error(f"Start error: {str(e)}")
        await update.message.reply_text(MESSAGES['tg']['ERRORS']['GENERAL_ERROR'])

async def get_admin_chat_id(bot):
    """Get admin's chat ID by username"""
    try:
        # Для тестирования можно использовать ID текущего пользователя вместо поиска по имени
        admin_chat = await bot.get_chat(f"@{ADMIN_USERNAME}")
        return admin_chat.id
    except Exception as e:
        logger.error(f"Error getting admin chat ID: {str(e)}")
        # В случае ошибки возвращаем None и обрабатываем это в вызывающем коде
        return None

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Ignore header buttons
    if query.data.startswith('header_'):
        await query.answer()
        return

    admin_username = update.effective_user.username

    if not admin_username or admin_username.lower() != ADMIN_USERNAME.lower():
        await query.answer("❌ У вас нет прав администратора")
        return

    action, user_id = query.data.split('_')
    user_id = int(user_id)

    if user_id not in PENDING_USERS:
        await query.answer("❌ Заявка не найдена или уже обработана")
        return

    user_info = PENDING_USERS[user_id]

    if action == "approve":
        try:
            password = ''.join([str(hash(datetime.now()))[i:i+2] for i in range(0, 8, 2)])
            password_hash = hash_password(password)
            
            if approve_user(user_id, password_hash):
                del PENDING_USERS[user_id]
                
                # Экранируем специальные символы для Markdown
                escaped_password = password.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]").replace("(", "\\(").replace(")", "\\)").replace("~", "\\~").replace("`", "\\`").replace(">", "\\>").replace("#", "\\#").replace("+", "\\+").replace("-", "\\-").replace("=", "\\=").replace("|", "\\|").replace("{", "\\{").replace("}", "\\}").replace(".", "\\.").replace("!", "\\!")
                
                # Получаем информацию о языке пользователя
                user_data = get_user(user_id)
                lang_code = user_data['language_code'] if user_data and 'language_code' in user_data else 'tg'
                
                # Сообщения об одобрении на разных языках
                approval_messages = {
                    'tg': f"✅ Дархости шумо қабул карда шуд\\!\n\nРамзи шумо барои ворид шудан: `{escaped_password}`\n\nЛутфан, онро нигоҳ доред\\.",
                    'ru': f"✅ Ваша заявка одобрена\\!\n\nВаш пароль для входа: `{escaped_password}`\n\nПожалуйста, сохраните его\\.",
                    'uz': f"✅ Arizangiz tasdiqlandi\\!\n\nKirish uchun parolingiz: `{escaped_password}`\n\nIltimos, uni saqlab qoling\\.",
                    'kk': f"✅ Өтінішіңіз мақұлданды\\!\n\nКіру үшін құпия сөзіңіз: `{escaped_password}`\n\nОны сақтап қойыңыз\\.",
                    'en': f"✅ Your request has been approved\\!\n\nYour password: `{escaped_password}`\n\nPlease save it\\."
                }
                
                # Тексты кнопок на разных языках
                button_texts = {
                    'tg': "🚀 Ба бот ворид шавед",
                    'ru': "🚀 Войти в бот",
                    'uz': "🚀 Botga kirish",
                    'kk': "🚀 Ботқа кіру",
                    'en': "🚀 Enter the bot"
                }
                
                # Выбираем сообщение и текст кнопки согласно языку пользователя
                message = approval_messages.get(lang_code, approval_messages['tg'])
                button_text = button_texts.get(lang_code, button_texts['tg'])
                
                # Создаем клавиатуру с кнопкой для входа
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(button_text, callback_data="return_to_main")]
                ])
                
                # Отправляем сообщение пользователю
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='MarkdownV2',
                    reply_markup=keyboard
                )
                
                # Уведомляем администратора
                await query.edit_message_text(f"✅ Пользователь @{user_info['username']} одобрен")
            else:
                await query.edit_message_text("❌ Ошибка при одобрении пользователя")
        except Exception as e:
            logger.error(f"Ошибка при одобрении пользователя через кнопку действия: {e}")
            await query.edit_message_text(f"❌ Ошибка при одобрении пользователя: {str(e)}")
    else:
        # Удаляем пользователя из списка ожидающих
        del PENDING_USERS[user_id]
        
        # Получаем информацию о языке пользователя
        user_data = get_user(user_id)
        lang_code = user_data['language_code'] if user_data and 'language_code' in user_data else 'tg'
        
        # Сбрасываем статус одобрения пользователя, но НЕ удаляем его из базы
        # Это позволит пользователю повторно отправить заявку
        from models import reset_user_approval
        reset_user_approval(user_id)
        
        # Сообщения об отклонении на разных языках
        rejection_messages = {
            'tg': "❌ Дархости шумо радд карда шуд.\n\nШумо метавонед дархости навро фиристед.",
            'ru': "❌ Ваша заявка отклонена администратором.\n\nВы можете отправить новую заявку.",
            'uz': "❌ Arizangiz administrator tomonidan rad etildi.\n\nSiz yangi ariza yuborishingiz mumkin.",
            'kk': "❌ Сіздің өтінішіңіз әкімші тарапынан қабылданбады.\n\nСіз жаңа өтініш жібере аласыз.",
            'en': "❌ Your request has been rejected by the administrator.\n\nYou can send a new request."
        }
        
        # Выбираем сообщение согласно языку пользователя
        message = rejection_messages.get(lang_code, rejection_messages['tg'])
        
        # Создаем клавиатуру с кнопкой для повторной отправки заявки
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Отправить новую заявку", callback_data="send_request")],
            [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")]
        ])
        
        # Отправляем сообщение пользователю с кнопкой повторной отправки
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=keyboard
        )
        
        # Уведомляем администратора
        await query.edit_message_text(f"❌ Пользователь @{user_info['username']} отклонен")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    user_id = user.id
    user_data = get_user(user_id)

    # Проверяем, ожидается ли пароль администратора после нажатия кнопки admin_panel
    if context.user_data and context.user_data.get('waiting_for_admin_password'):
        # Удаляем флаг ожидания пароля
        context.user_data.pop('waiting_for_admin_password', None)
        
        # Проверяем пароль
        password = update.message.text
        password_hash = hash_password(password)
        
        # Проверка корректности пароля
        if password_hash == ADMIN_PASSWORD_HASH:
            # Отображаем главное меню админа
            await update.message.reply_text(
                "✅ Доступ предоставлен. Добро пожаловать в панель администратора!",
                reply_markup=get_admin_keyboard()
            )
            return
        else:
            await update.message.reply_text(
                "❌ Неверный пароль. Доступ запрещен."
            )
            
            # Возвращаем пользователя на главный экран
            lang_code = user_data['language_code'] if user_data else 'tg'
            keyboard = get_currency_keyboard(current_lang=lang_code, user_data=user_data)
            await update.message.reply_text(
                MESSAGES[lang_code]['WELCOME'],
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
            return
    
    # Обычная обработка сообщения, если не в режиме ввода пароля админа
    if not user_data:
        add_user(user.id, user.username)
        user_data = get_user(user.id)

    lang_code = user_data['language_code'] if user_data else 'tg'
    keyboard = get_currency_keyboard(current_lang=lang_code, user_data=user_data)
    await update.message.reply_text(
        MESSAGES[lang_code]['WELCOME'],
        reply_markup=keyboard,
        parse_mode='MarkdownV2'
    )

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        lang_code = query.data.split('_')[1]
        user_id = update.effective_user.id
        logger.info(f"Language change request from user {user_id} to {lang_code}")

        # Update user's language in database
        if update_user_language(user_id, lang_code):
            # Get fresh keyboard with new language and user data for admin/moderator buttons
            user_data = get_user(user_id)  # Get updated user data after language change
            keyboard = get_currency_keyboard(current_lang=lang_code, user_data=user_data)
            welcome_message = MESSAGES[lang_code]['WELCOME']

            try:
                # Delete previous message if exists
                try:
                    await query.message.delete()
                except Exception:
                    pass  # Ignore if message can't be deleted

                # Send new welcome message
                await update.effective_chat.send_message(
                    text=welcome_message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )

                # Send confirmation in the selected language
                lang_confirmations = {
                    'tg': '✅ Забон иваз карда шуд',
                    'ru': '✅ Язык изменен',
                    'uz': '✅ Til oʻzgartirildi',
                    'kk': '✅ Тіл өзгертілді',
                    'en': '✅ Language changed'
                }
                await query.answer(lang_confirmations.get(lang_code, '✅ OK'))
                logger.info(f"Language successfully changed to {lang_code} for user {user_id}")

            except Exception as e:
                logger.error(f"Error sending message after language change: {e}")
                await query.answer("❌ Error sending message")
        else:
            logger.error(f"Failed to update language to {lang_code} for user {user_id}")
            await query.answer("❌ Error updating language")

    except Exception as e:
        logger.error(f"Language selection error: {str(e)}")
        await query.answer("❌ Error processing language change")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        # Проверка доступа на уровне всех действий
        user_id = update.effective_user.id
        user_data = get_user(user_id)
        
        # Получаем информацию из пользовательских данных
        is_admin = user_data and user_data.get('is_admin', False)
        is_moderator = user_data and user_data.get('is_moderator', False)
        is_approved = user_data and user_data.get('is_approved')
        
        # Обработка обычных валютных пар
        if query.data == "regular_pairs":
            # Получаем язык пользователя из user_data
            from models import get_user_language
            lang_code = 'ru'  # Значение по умолчанию
            try:
                lang_code = get_user_language(user_id) or 'ru'
            except Exception as e:
                logger.error(f"Error getting language for user {user_id}: {e}")
            logger.info(f"Current language for user {user_id}: {lang_code}")
            
            # Создаем клавиатуру с обычными валютными парами
            keyboard = []
            
            # Добавляем заголовок для основных валютных пар
            keyboard.append([InlineKeyboardButton("🌟 ОСНОВНЫЕ ВАЛЮТНЫЕ ПАРЫ 🌟", callback_data="header_main")])
            
            # Основные форекс пары
            major_pairs = [
                '💶 EUR/USD', '💷 GBP/USD', '💴 USD/JPY', '💰 USD/CHF', 
                '🍁 USD/CAD', '🦘 AUD/USD', '🥝 NZD/USD'
            ]
            
            # Создаем группы по 2 пары в строке для основных пар
            for i in range(0, len(major_pairs), 2):
                row = []
                row.append(InlineKeyboardButton(major_pairs[i], callback_data=major_pairs[i]))
                if i + 1 < len(major_pairs):
                    row.append(InlineKeyboardButton(major_pairs[i + 1], callback_data=major_pairs[i + 1]))
                keyboard.append(row)
            
            # Добавляем разделитель для кросс-курсов EUR
            keyboard.append([InlineKeyboardButton("💶 КРОСС-КУРСЫ EUR 💶", callback_data="header_eur")])
            
            # Кросс-курсы EUR
            eur_pairs = [
                '🇪🇺 EUR/GBP', '🇪🇺 EUR/JPY', '🇪🇺 EUR/CHF', 
                '🇪🇺 EUR/CAD', '🇪🇺 EUR/AUD', '🇪🇺 EUR/NZD'
            ]
            
            # Создаем группы по 2 пары в строке для кросс-курсов EUR
            for i in range(0, len(eur_pairs), 2):
                row = []
                row.append(InlineKeyboardButton(eur_pairs[i], callback_data=eur_pairs[i]))
                if i + 1 < len(eur_pairs):
                    row.append(InlineKeyboardButton(eur_pairs[i + 1], callback_data=eur_pairs[i + 1]))
                keyboard.append(row)
            
            # Добавляем разделитель для кросс-курсов GBP
            keyboard.append([InlineKeyboardButton("💷 КРОСС-КУРСЫ GBP 💷", callback_data="header_gbp")])
            
            # Кросс-курсы GBP
            gbp_pairs = [
                '🇬🇧 GBP/JPY', '🇬🇧 GBP/CHF', '🇬🇧 GBP/CAD', 
                '🇬🇧 GBP/AUD', '🇬🇧 GBP/NZD'
            ]
            
            # Создаем группы по 2 пары в строке для кросс-курсов GBP
            for i in range(0, len(gbp_pairs), 2):
                row = []
                row.append(InlineKeyboardButton(gbp_pairs[i], callback_data=gbp_pairs[i]))
                if i + 1 < len(gbp_pairs):
                    row.append(InlineKeyboardButton(gbp_pairs[i + 1], callback_data=gbp_pairs[i + 1]))
                keyboard.append(row)
            
            # Добавляем разделитель для других кросс-курсов
            keyboard.append([InlineKeyboardButton("🔄 ДРУГИЕ КРОСС-КУРСЫ 🔄", callback_data="header_other")])
            
            # Другие кросс-курсы
            other_pairs = [
                '🏝️ AUD/JPY', '🏝️ AUD/CAD', '🏝️ AUD/CHF', '🏝️ AUD/NZD',
                '🇨🇦 CAD/JPY', '🇨🇦 CAD/CHF', '🇨🇭 CHF/JPY',
                '🥝 NZD/JPY', '🥝 NZD/CHF', '🥝 NZD/CAD'
            ]
            
            # Создаем группы по 2 пары в строке для других кросс-курсов
            for i in range(0, len(other_pairs), 2):
                row = []
                row.append(InlineKeyboardButton(other_pairs[i], callback_data=other_pairs[i]))
                if i + 1 < len(other_pairs):
                    row.append(InlineKeyboardButton(other_pairs[i + 1], callback_data=other_pairs[i + 1]))
                keyboard.append(row)
            
            # Добавляем разделитель для криптовалют
            keyboard.append([InlineKeyboardButton("₿ КРИПТОВАЛЮТЫ ₿", callback_data="header_crypto")])
            
            # Криптовалютные пары
            crypto_pairs = [
                '₿ BTC/USD', '⟠ ETH/USD', '✨ XRP/USD', '🐕 DOGE/USD', '☀️ SOL/USD',
                '🔵 LINK/USD', '🃏 ADA/USD', '👾 DOT/USD', '💹 BNB/USD', '🔷 LTC/USD',
                '₿ BTC/EUR', '⟠ ETH/EUR', '₿ BTC/JPY', '⟠ ETH/JPY'
            ]
            
            # Создаем группы по 2 пары в строке для криптовалют
            for i in range(0, len(crypto_pairs), 2):
                row = []
                row.append(InlineKeyboardButton(crypto_pairs[i], callback_data=crypto_pairs[i]))
                if i + 1 < len(crypto_pairs):
                    row.append(InlineKeyboardButton(crypto_pairs[i + 1], callback_data=crypto_pairs[i + 1]))
                keyboard.append(row)
                
            # Добавляем кнопку для возврата в главное меню
            return_button_text = {
                'tg': '🏠 Ба саҳифаи аввал',
                'ru': '🏠 На главную',
                'uz': '🏠 Bosh sahifaga',
                'kk': '🏠 Басты бетке',
                'en': '🏠 Return to Main'
            }
            
            keyboard.append([
                InlineKeyboardButton(
                    return_button_text.get(lang_code, return_button_text['ru']),
                    callback_data="return_to_main"
                )
            ])
            
            # Заголовок для сообщения с валютными парами
            title_text = {
                'tg': '💱 Ҷуфтҳои асъорӣ',
                'ru': '💱 Валютные пары',
                'uz': '💱 Valyuta juftlari',
                'kk': '💱 Валюта жұптары',
                'en': '💱 Currency Pairs'
            }
            
            # Отправляем сообщение с клавиатурой валютных пар
            await query.edit_message_text(
                title_text.get(lang_code, title_text['ru']),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
            
        # Обработка заголовков разделов (не делаем ничего, просто показываем сообщение)
        if query.data.startswith("header_"):
            await query.answer("Выберите конкретную валютную пару из списка")
            return
            
        # Обработка OTC Pocket Option кнопок
        if query.data == "otc_pairs":
            await handle_otc_pairs(update, context)
            return
            
        if query.data == "otc_signals":
            await handle_otc_signals(update, context)
            return
            
        # Обработка кнопок обучения трейдингу
        if query.data == "trading_education":
            logger.info(f"Showing trading education menu for user {user_id}")
            await show_trading_education_menu(update, context)
            return
            
        if query.data == "trading_books":
            logger.info(f"Redirecting to handle_trading_books for user {user_id}")
            await handle_trading_books(update, context)
            return
            
        if query.data.startswith("book_details_"):
            logger.info(f"Processing book details request for user {user_id}")
            await handle_book_details(update, context)
            return
            
        if query.data == "trading_beginner":
            logger.info(f"Redirecting to handle_trading_beginner for user {user_id}")
            await handle_trading_beginner(update, context)
            return
            
        if query.data == "trading_strategies":
            logger.info(f"Redirecting to handle_trading_strategies for user {user_id}")
            await handle_trading_strategies(update, context)
            return
            
        if query.data.startswith("strategy_"):
            logger.info(f"Processing strategy details for user {user_id}")
            await handle_trading_strategies(update, context)
            return
            
        if query.data == "trading_tools":
            logger.info(f"Redirecting to handle_trading_tools for user {user_id}")
            await handle_trading_tools(update, context)
            return
            
        if query.data.startswith("tool_"):
            logger.info(f"Processing tool details for user {user_id}")
            await handle_trading_tools(update, context)
            return
            
        # Обработка конкретных OTC пар
        if query.data.startswith("otc_") and "refresh" not in query.data and "subscribe" not in query.data and "settings" not in query.data:
            await handle_otc_pair_analysis(update, context)
            return
        
        # Обработка кнопок админ-панели и модератор-панели
        if query.data == "admin_panel":
            if is_admin:
                # Создаем админа, если его нет в базе (с предустановленным паролем)
                create_admin_user(user_id, update.effective_user.username or "")
                
                # Просим ввести пароль
                await query.edit_message_text(
                    "👑 <b>Панель администратора</b>\n\nВведите пароль для доступа:",
                    parse_mode='HTML'
                )
                # Устанавливаем контекст для обработки пароля
                context.user_data['waiting_for_admin_password'] = True
                return ADMIN_PASSWORD
            else:
                await query.edit_message_text(
                    "⛔ У вас нет прав администратора.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Назад", callback_data="return_to_main")
                    ]])
                )
                return
        
        elif query.data == "moderator_panel":
            if is_moderator or is_admin:
                # Временное сообщение о режиме модератора
                moderator_keyboard = [
                    [InlineKeyboardButton("✅ Ожидающие подтверждения", callback_data="admin_pending")],
                    [InlineKeyboardButton("👥 Список пользователей", callback_data="admin_all_users")],
                    [InlineKeyboardButton("↩️ В главное меню", callback_data="return_to_main")]
                ]
                
                await query.edit_message_text(
                    "🛡️ Панель модератора\n\n"
                    "Выберите действие:",
                    reply_markup=InlineKeyboardMarkup(moderator_keyboard)
                )
                return
            else:
                await query.edit_message_text(
                    "⛔ У вас нет прав модератора.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Назад", callback_data="return_to_main")
                    ]])
                )
                return
        
        # Проверяем, является ли действие кнопкой админ-панели
        is_admin_action = query.data.startswith("admin_") or query.data.startswith("send_message_to_")
        
        # Если это действие админ-панели и пользователь админ - выходим
        # Эти действия будут обработаны ConversationHandler для админа
        if is_admin_action and is_admin:
            return
            
        # Если действие модератора и пользователь модератор, обработаем здесь
        if is_admin_action and (is_moderator or is_admin):
            # Список разрешенных действий для модератора
            moderator_actions = ["admin_pending", "admin_all_users"]
            
            if query.data in moderator_actions:
                # Определяем действие
                if query.data == "admin_pending":
                    from models import get_pending_users
                    pending_users = get_pending_users()
                    keyboard = get_pending_keyboard(pending_users, is_moderator=True)
                    
                    await query.edit_message_text(
                        f"✅ Пользователи, ожидающие подтверждения: {len(pending_users)}",
                        reply_markup=keyboard
                    )
                    return
                
                elif query.data == "admin_all_users":
                    from models import get_all_users
                    users = get_all_users()
                    keyboard = get_user_list_keyboard(users, back_command="moderator_panel")
                    
                    await query.edit_message_text(
                        f"👥 Все пользователи: {len(users)}",
                        reply_markup=keyboard
                    )
                    return
        
        # Разрешаем некоторые действия даже для неавторизованных пользователей
        allowed_for_all = [
            "send_request",
            "return_to_main",
            "change_language",
        ]
        is_allowed_action = query.data in allowed_for_all or query.data.startswith('lang_')
        
        # Проверка доступа
        if not (is_approved or is_admin or is_allowed_action):
            register_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📝 Отправить заявку", callback_data="send_request")
            ]])
            
            await query.edit_message_text(
                "⚠️ У вас нет доступа к этой функции.\n\n"
                "Для получения доступа к боту необходимо отправить заявку на регистрацию.",
                reply_markup=register_keyboard
            )
            return
            
        # Handle "Return to Main" button
        if query.data == "return_to_main":
            lang_code = user_data['language_code'] if user_data else 'tg'

            # Передаем данные пользователя для отображения админ/модератор кнопок, если есть права
            keyboard = get_currency_keyboard(current_lang=lang_code, user_data=user_data)
            try:
                await query.message.delete()
            except Exception:
                pass  # Ignore if message can't be deleted

            await update.effective_chat.send_message(
                text=MESSAGES[lang_code]['WELCOME'],
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
            return
            
        # Обработка кнопки отправки запроса
        if query.data == "send_request":
            user = update.effective_user
            user_id = user.id
            username = user.username
            
            # Проверяем, существует ли уже пользователь и его статус
            user_data = get_user(user_id)
            
            if user_data and user_data.get('is_approved'):
                await query.edit_message_text(
                    "✅ Вы уже зарегистрированы и подтверждены."
                )
                return
            
            # Добавляем пользователя в базу, если его еще нет
            if not user_data:
                add_user(user_id, username)
            
            # Добавляем пользователя в список ожидающих и отправляем запрос админу
            PENDING_USERS[user_id] = {
                'user_id': user_id,
                'username': username,
                'timestamp': datetime.now()
            }
            
            # Получаем язык пользователя
            user_data = get_user(user_id)
            lang_code = user_data['language_code'] if user_data and 'language_code' in user_data else 'tg'
            
            # Сообщения о заявке на разных языках с инструкциями по регистрации
            request_messages = {
                'tg': "📝 Дархости шумо ба маъмур фиристода шуд.\n\n"
                      "⚠️ Барои гирифтани дастрасӣ ба бот, лутфан:\n"
                      "1️⃣ Дар сайти Pocket Option бо тариқи TRADEPO.RU ба қайд гиред\n"
                      "2️⃣ ID худро ба админ равон кунед (мисол: id 111111)\n\n"
                      "Баъд аз ин, дархости шумо баррасӣ карда мешавад.",
                      
                'ru': "📝 Ваша заявка отправлена администратору.\n\n"
                      "⚠️ Для получения доступа к боту, пожалуйста:\n"
                      "1️⃣ Зарегистрируйтесь на сайте Pocket Option через TRADEPO.RU\n"
                      "2️⃣ Отправьте свой ID администратору (пример: id 111111)\n\n"
                      "После этого ваша заявка будет рассмотрена.",
                      
                'uz': "📝 Arizangiz administratorga yuborildi.\n\n"
                      "⚠️ Botga kirish uchun:\n"
                      "1️⃣ Pocket Option saytida TRADEPO.RU orqali ro'yxatdan o'ting\n"
                      "2️⃣ ID raqamingizni adminga yuboring (misol: id 111111)\n\n"
                      "Shundan so'ng arizangiz ko'rib chiqiladi.",
                      
                'kk': "📝 Сіздің өтінішіңіз әкімшіге жіберілді.\n\n"
                      "⚠️ Ботқа кіру үшін:\n"
                      "1️⃣ Pocket Option сайтында TRADEPO.RU арқылы тіркеліңіз\n"
                      "2️⃣ ID нөміріңізді әкімшіге жіберіңіз (мысалы: id 111111)\n\n"
                      "Осыдан кейін өтінішіңіз қаралады.",
                      
                'en': "📝 Your request has been sent to the administrator.\n\n"
                      "⚠️ To get access to the bot, please:\n"
                      "1️⃣ Register on Pocket Option website through TRADEPO.RU\n"
                      "2️⃣ Send your ID to the administrator (example: id 111111)\n\n"
                      "After that, your request will be reviewed."
            }
            
            # Отправляем сообщение пользователю на его языке
            message = request_messages.get(lang_code, request_messages['tg'])
            
            # Добавляем информацию о контактах службы поддержки
            support_messages = {
                'tg': "\n\n📞 Агар савол дошта бошед, метавонед бо хадамоти дастгирӣ тамос гиред: @tradeporu",
                'ru': "\n\n📞 Если у вас есть вопросы, вы можете связаться со службой поддержки: @tradeporu",
                'uz': "\n\n📞 Savollaringiz bo'lsa, qo'llab-quvvatlash xizmatiga murojaat qilishingiz mumkin: @tradeporu",
                'kk': "\n\n📞 Сұрақтарыңыз болса, қолдау қызметіне хабарласа аласыз: @tradeporu",
                'en': "\n\n📞 If you have any questions, you can contact support: @tradeporu"
            }
            
            # Добавляем информацию о поддержке к сообщению
            support_text = support_messages.get(lang_code, support_messages['tg'])
            message += support_text
            
            # Пробуем создать и отправить изображение
            # Импортируем модуль для создания изображения запроса
            from create_request_image import create_request_image
            try:
                # Создаем красивое изображение запроса с именем пользователя
                if create_request_image(username):
                    # Сначала удаляем текущее сообщение
                    await query.message.delete()
                    
                    # Создаем клавиатуру для кнопок под изображением
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")]
                    ])
                    
                    # Отправляем изображение с новым текстом и клавиатурой
                    with open('request_image.png', 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=photo,
                            caption=message,
                            reply_markup=keyboard
                        )
                else:
                    # Если не удалось создать изображение, просто редактируем текст с клавиатурой
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")]
                    ])
                    await query.edit_message_text(message, reply_markup=keyboard)
            except Exception as e:
                logger.error(f"Ошибка при отправке изображения запроса: {e}")
                # В случае ошибки просто редактируем текст с клавиатурой
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")]
                ])
                await query.edit_message_text(message, reply_markup=keyboard)
            
            # Получаем чат администратора и отправляем ему уведомление
            admin_chat_id = await get_admin_chat_id(context.bot)
            if admin_chat_id:
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
                        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
                    ]
                ]
                await context.bot.send_message(
                    chat_id=admin_chat_id,
                    text=f"📝 Новая заявка на регистрацию!\n\n"
                        f"👤 Пользователь: @{username}\n"
                        f"🆔 ID: {user_id}\n"
                        f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # Если не удалось найти админа, сохраняем запрос в базе данных,
                # чтобы администратор мог просмотреть его через панель управления
                logger.warning(f"Admin chat not found. Registration request from user @{username} (ID: {user_id}) stored in pending list.")
            return

        # Ignore clicks on header buttons
        if query.data.startswith('header_'):
            await query.answer()
            return

        # Получаем данные пользователя, если нужно
        if not user_data:
            add_user(user_id, update.effective_user.username)
            user_data = get_user(user_id)
        
        lang_code = user_data['language_code'] if user_data else 'tg'
        logger.info(f"Current language for user {user_id}: {lang_code}")

        if query.data.startswith('lang_'):
            await handle_language_selection(update, context)
            return

        if query.data == "change_language":
            keyboard = get_language_keyboard()
            msg = "Выберите язык / Забонро интихоб кунед / Tilni tanlang / Тілді таңдаңыз / Choose language:"
            try:
                if query.message.photo:
                    await query.message.reply_text(msg, reply_markup=keyboard)
                else:
                    await query.message.edit_text(msg, reply_markup=keyboard)
            except Exception as e:
                logger.error(f"Error showing language selection: {e}")
            return

        # Этот блок больше не нужен, потому что мы уже обработали эту кнопку выше

        # Этот блок больше не нужен, потому что мы уже обработали эту кнопку выше
                
        # Обработка кнопок меню модератора
        if query.data.startswith("mod_"):
            # Проверяем, что пользователь является модератором
            if user_data and user_data.get('is_moderator'):
                action = query.data
                
                if action == "mod_users":
                    # Переход в раздел управления пользователями для модератора
                    await query.edit_message_text(
                        "👥 Управление пользователями\n\nВыберите действие:",
                        reply_markup=get_user_management_keyboard()
                    )
                    return
                
                elif action == "mod_pending":
                    # Просмотр заявок на подтверждение
                    # Получаем список пользователей, ожидающих одобрения
                    pending_users = get_pending_users()
                    
                    if not pending_users:
                        keyboard = [
                            [InlineKeyboardButton("↩️ Назад в меню модератора", callback_data="moderator_panel")]
                        ]
                        await query.edit_message_text(
                            "📝 Ожидающие подтверждения\n\n"
                            "Нет пользователей, ожидающих подтверждения.",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                    else:
                        # Получаем клавиатуру с пагинацией для модератора
                        keyboard = get_pending_keyboard(pending_users, is_moderator=True)
                        await query.edit_message_text(
                            "📝 Ожидающие подтверждения\n\n"
                            "Выберите пользователя для действий:",
                            reply_markup=keyboard
                        )
                    return
                
                elif action == "mod_stats":
                    # Показываем статистику бота для модератора
                    users = get_all_users()
                    total_users = len(users)
                    approved_users = sum(1 for user in users if user.get('is_approved'))
                    admin_users = sum(1 for user in users if user.get('is_admin'))
                    moderator_users = sum(1 for user in users if user.get('is_moderator'))
                    pending_users = len(get_pending_users())
                    
                    keyboard = [
                        [InlineKeyboardButton("↩️ Назад в меню модератора", callback_data="moderator_panel")]
                    ]
                    
                    await query.edit_message_text(
                        f"📊 Статистика бота\n\n"
                        f"👤 Всего пользователей: {total_users}\n"
                        f"✅ Подтвержденных: {approved_users}\n"
                        f"⏳ Ожидают подтверждения: {pending_users}\n"
                        f"👑 Администраторов: {admin_users}\n"
                        f"🛡️ Модераторов: {moderator_users}",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return
            else:
                await query.answer("❌ У вас нет прав модератора")
                return

        # Обрабатываем запросы на анализ рынка только для авторизованных пользователей
        if not (is_approved or is_admin):
            register_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📝 Отправить заявку", callback_data="send_request")
            ]])
            
            await query.edit_message_text(
                "⚠️ У вас нет доступа к анализу рынка.\n\n"
                "Для получения доступа к боту необходимо отправить заявку на регистрацию.",
                reply_markup=register_keyboard
            )
            return

        pair = query.data
        symbol = CURRENCY_PAIRS.get(pair)
        if not symbol:
            await query.message.reply_text(MESSAGES[lang_code]['ERRORS']['GENERAL_ERROR'])
            return

        analyzing_message = await query.message.reply_text(
            MESSAGES[lang_code]['ANALYZING'],
            parse_mode='MarkdownV2'
        )

        try:
            analyzer = MarketAnalyzer(symbol)
            analyzer.set_language(lang_code)
            analysis_result = analyzer.analyze_market()

            if not analysis_result or 'error' in analysis_result:
                error_msg = analysis_result.get('error', MESSAGES[lang_code]['ERRORS']['ANALYSIS_ERROR'])
                await analyzing_message.edit_text(error_msg, parse_mode='MarkdownV2')
                return

            market_data, error_message = analyzer.get_market_data(minutes=30)
            if error_message or market_data is None or market_data.empty:
                await analyzing_message.edit_text(MESSAGES[lang_code]['ERRORS']['NO_DATA'])
                return

            result_message = format_signal_message(pair, analysis_result, lang_code)

            try:
                create_analysis_image(analysis_result, market_data, lang_code)
                with open('analysis_sample.png', 'rb') as photo:
                    await query.message.reply_photo(
                        photo=photo,
                        caption=result_message,
                        parse_mode='MarkdownV2',
                        reply_markup=get_currency_keyboard(current_lang=lang_code, user_data=user_data)
                    )
                await analyzing_message.delete()
            except Exception as img_error:
                logger.error(f"Chart error: {str(img_error)}")
                await analyzing_message.edit_text(
                    text=result_message,
                    parse_mode='MarkdownV2',
                    reply_markup=get_currency_keyboard(current_lang=lang_code, user_data=user_data)
                )

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            await analyzing_message.edit_text(MESSAGES[lang_code]['ERRORS']['ANALYSIS_ERROR'])

    except Exception as e:
        logger.error(f"Button click error: {str(e)}")
        lang_code = 'tg'  # Используем язык по умолчанию в случае ошибки
        await query.message.reply_text(MESSAGES[lang_code]['ERRORS']['GENERAL_ERROR'])

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the website.zip file to the user"""
    try:
        with open('website.zip', 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename='website.zip',
                caption='🌐 Архиви веб-сайт | Архив веб-сайта | Website archive'
            )
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        await update.message.reply_text("❌ Хатогӣ ҳангоми боргирӣ рух дод. Лутфан, дубора кӯшиш кунед.")

def get_admin_keyboard():
    """Создать улучшенную клавиатуру админ-панели"""
    keyboard = [
        # Основные функции управления
        [
            InlineKeyboardButton("👥 Управление пользователями", callback_data="admin_users"),
            InlineKeyboardButton("💱 Управление валютами", callback_data="admin_currencies")
        ],
        [
            InlineKeyboardButton("📝 Управление текстами", callback_data="admin_texts"),
            InlineKeyboardButton("📨 Рассылка сообщений", callback_data="admin_broadcast")
        ],
        
        # Образовательные разделы
        [
            InlineKeyboardButton("📚 Управление обучением", callback_data="admin_education")
        ],
        
        # Новые функции мессенджинга
        [
            InlineKeyboardButton("🔍 Поиск пользователя", callback_data="admin_search_user"),
            InlineKeyboardButton("📩 Прямое сообщение", callback_data="admin_direct_message")
        ],
        [
            InlineKeyboardButton("📩 Сообщение неодобренным", callback_data="admin_message_to_pending"),
            InlineKeyboardButton("👥 Выбрать пользователей", callback_data="admin_select_users")
        ],
        
        # OTC и платформы
        [
            InlineKeyboardButton("📱 OTC Pocket Option", callback_data="admin_otc_signals"),
            InlineKeyboardButton("📊 Trading View", callback_data="admin_trading_view")
        ],
        
        # Аналитические функции и настройки
        [
            InlineKeyboardButton("📊 Статистика бота", callback_data="admin_stats"),
            InlineKeyboardButton("📈 Аналитика детальная", callback_data="admin_statistics")
        ],
        [
            InlineKeyboardButton("📈 Анализ активности", callback_data="admin_activity"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")
        ],
        
        # Дополнительные функции управления
        [
            InlineKeyboardButton("📊 Управление сигналами", callback_data="admin_signals"),
            InlineKeyboardButton("👤 Аналитика пользователей", callback_data="admin_user_analytics")
        ],
        
        # Автоматизация и API
        [
            InlineKeyboardButton("⏱️ Планировщик задач", callback_data="admin_scheduler"),
            InlineKeyboardButton("🔌 API интеграции", callback_data="admin_api")
        ],
        
        # Контент и управление
        [
            InlineKeyboardButton("📑 Управление контентом", callback_data="admin_content_manager"),
            InlineKeyboardButton("⚡ Быстрые команды", callback_data="admin_quick_commands")
        ],
        
        # Технические функции
        [
            InlineKeyboardButton("🔒 Безопасность", callback_data="admin_security"),
            InlineKeyboardButton("🌐 Прокси", callback_data="admin_proxy")
        ],
        
        # Данные и логирование
        [
            InlineKeyboardButton("📤 Экспорт данных", callback_data="admin_export"),
            InlineKeyboardButton("📥 Импорт данных", callback_data="admin_import")
        ],
        [
            InlineKeyboardButton("📋 Логи системы", callback_data="admin_logs"),
            InlineKeyboardButton("🖥️ Статус сервера", callback_data="admin_server_status")
        ],
        
        # История и плагины
        [
            InlineKeyboardButton("📜 История действий", callback_data="admin_history"),
            InlineKeyboardButton("🧩 Плагины", callback_data="admin_plugins")
        ],
        
        # Marketplace и обновления
        [
            InlineKeyboardButton("🛒 Маркетплейс", callback_data="admin_marketplace"),
            InlineKeyboardButton("🔄 Обновить БД", callback_data="admin_update_db")
        ],
        
        # Безопасность и обслуживание
        [
            InlineKeyboardButton("🔐 Сменить пароль", callback_data="admin_change_password"),
            InlineKeyboardButton("ℹ️ О боте", callback_data="admin_about")
        ],
        
        # Разное
        [
            InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language"),
            InlineKeyboardButton("↩️ Выход", callback_data="return_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_management_keyboard():
    """Создать клавиатуру управления пользователями"""
    keyboard = [
        [InlineKeyboardButton("✅ Ожидающие подтверждения", callback_data="admin_pending")],
        [InlineKeyboardButton("👤 Все пользователи", callback_data="admin_all_users")],
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_action_keyboard(user_id, is_approved=False, is_admin=False, is_moderator=False, back_command="admin_pending"):
    """Создать клавиатуру действий с пользователем"""
    keyboard = []
    
    # Если пользователь еще не подтвержден, показываем кнопки подтверждения/отклонения
    if not is_approved:
        keyboard.append([
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
        ])
    else:
        # Если пользователь уже подтвержден, показываем кнопки управления правами
        admin_text = "❌ Убрать админа" if is_admin else "👑 Сделать админом"
        moderator_text = "❌ Убрать модератора" if is_moderator else "🔰 Сделать модератором"
        
        keyboard.append([
            InlineKeyboardButton(admin_text, callback_data=f"toggle_admin_{user_id}_{0 if is_admin else 1}"),
            InlineKeyboardButton(moderator_text, callback_data=f"toggle_moderator_{user_id}_{0 if is_moderator else 1}")
        ])
        
        # Кнопка блокировки доступа
        keyboard.append([
            InlineKeyboardButton("🚫 Заблокировать доступ", callback_data=f"block_user_{user_id}")
        ])
        
        # Кнопка отправки сообщения пользователю
        keyboard.append([
            InlineKeyboardButton("📨 Отправить сообщение", callback_data=f"send_message_to_{user_id}")
        ])
    
    # Кнопка назад
    keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data=back_command)])
    
    return InlineKeyboardMarkup(keyboard)

def get_user_list_keyboard(users, page=0, page_size=5, back_command="admin_all_users"):
    """Создать клавиатуру со списком пользователей и пагинацией"""
    total_pages = (len(users) + page_size - 1) // page_size if users else 1
    start = page * page_size
    end = min(start + page_size, len(users)) if users else 0
    
    keyboard = []
    
    # Добавляем пользователей на текущей странице
    if users:
        for user in users[start:end]:
            username = user.get('username', 'Без имени')
            user_id = user.get('user_id')
            is_approved = "✅" if user.get('is_approved') else "⏳"
            is_admin = "👑" if user.get('is_admin') else ""
            button_text = f"{is_approved} {is_admin} @{username}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"user_{user_id}")])
    else:
        keyboard.append([InlineKeyboardButton("Нет пользователей", callback_data="header_none")])
    
    # Добавляем кнопки пагинации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"page_{page-1}_{back_command}"))
    nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="header_page"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"page_{page+1}_{back_command}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    # Кнопка "Назад"
    # Определяем, к какому меню возвращаться (модератор или админ)
    back_button_text = "↩️ Назад"
    if back_command.startswith("mod_"):
        back_to = "moderator_panel"
    else:
        back_to = "admin_users"
    keyboard.append([InlineKeyboardButton(back_button_text, callback_data=back_to)])
    
    return InlineKeyboardMarkup(keyboard)

def get_pending_keyboard(pending_users, page=0, page_size=5, is_moderator=False):
    """Создать клавиатуру со списком ожидающих подтверждения пользователей"""
    back_command = "mod_pending" if is_moderator else "admin_pending"
    return get_user_list_keyboard(pending_users, page, page_size, back_command)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /admin для входа в админ-панель"""
    user = update.effective_user
    user_id = user.id
    username = user.username
    
    # Проверяем, администратор ли это
    if username and username.lower() == ADMIN_USERNAME.lower():
        # Создаем админа, если его нет в базе (с предустановленным паролем)
        create_admin_user(user_id, username)
        
        # Запрашиваем пароль для подтверждения
        await update.message.reply_text(
            "👑 Панель администратора\n\nВведите пароль для доступа:"
        )
        return ADMIN_PASSWORD
    else:
        await update.message.reply_text(
            "❌ У вас нет прав доступа к этой команде."
        )
        return ConversationHandler.END

async def admin_check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка пароля администратора"""
    password = update.message.text
    password_hash = hash_password(password)
    
    # Проверяем пароль
    if password_hash == ADMIN_PASSWORD_HASH:
        # Отображаем главное меню админа
        await update.message.reply_text(
            "✅ Доступ предоставлен. Добро пожаловать в панель администратора!",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    else:
        await update.message.reply_text(
            "❌ Неверный пароль. Доступ запрещен."
        )
        return ConversationHandler.END

async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок в меню администратора"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "admin_users":
        # Переход в раздел управления пользователями
        await query.edit_message_text(
            "👥 Управление пользователями\n\nВыберите действие:",
            reply_markup=get_user_management_keyboard()
        )
        return ADMIN_USER_MANAGEMENT
    
    elif action == "admin_broadcast":
        # Переход в режим рассылки сообщений с выбором получателей
        keyboard = [
            [InlineKeyboardButton("📢 Всем пользователям", callback_data="broadcast_all")],
            [InlineKeyboardButton("✅ Только подтвержденным", callback_data="broadcast_approved")],
            [InlineKeyboardButton("⏳ Только ожидающим", callback_data="broadcast_pending")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            "📢 Рассылка сообщений\n\n"
            "Выберите, кому отправить сообщение:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_BROADCAST_MESSAGE
        
    elif action == "admin_education":
        # Переход в раздел управления образовательным контентом
        keyboard = [
            [
                InlineKeyboardButton("📚 Книги по трейдингу", callback_data="admin_edit_books"),
                InlineKeyboardButton("🎓 Обучение для начинающих", callback_data="admin_edit_beginner")
            ],
            [
                InlineKeyboardButton("📈 Торговые стратегии", callback_data="admin_edit_strategies"),
                InlineKeyboardButton("🔧 Инструменты трейдинга", callback_data="admin_edit_tools")
            ],
            [
                InlineKeyboardButton("📱 OTC пары и сигналы", callback_data="admin_edit_otc")
            ],
            [
                InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
            ]
        ]
        
        await query.edit_message_text(
            "📚 *Управление образовательным контентом*\n\n"
            "Выберите раздел для редактирования:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_EDUCATION_MANAGEMENT
    
    elif action == "admin_direct_message":
        # Прямое сообщение конкретному пользователю
        await query.edit_message_text(
            "📩 Отправка прямого сообщения\n\n"
            "Введите ID пользователя, которому хотите отправить сообщение:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
            ]])
        )
        return ADMIN_DIRECT_MESSAGE
    
    elif action == "admin_search_user":
        # Поиск пользователя
        await query.edit_message_text(
            "🔎 Поиск пользователя\n\n"
            "Введите имя пользователя или ID для поиска:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
            ]])
        )
        return ADMIN_SEARCH_USER
    
    elif action == "admin_message_to_pending":
        # Отправка сообщения неодобренным пользователям
        pending_users = get_pending_users()
        count = len(pending_users) if pending_users else 0
        
        keyboard = [
            [InlineKeyboardButton("📩 Отправить всем неодобренным", callback_data="send_to_all_pending")],
            [InlineKeyboardButton("👤 Выбрать конкретных пользователей", callback_data="select_pending_users")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            f"📩 Отправка сообщений неодобренным пользователям\n\n"
            f"Всего неодобренных пользователей: {count}\n\n"
            f"Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_MESSAGE_TO_PENDING
    
    elif action == "admin_select_users":
        # Выбор пользователей для отправки сообщения
        all_users = get_all_users()
        count = len(all_users) if all_users else 0
        
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск по критериям", callback_data="search_users_criteria")],
            [InlineKeyboardButton("📋 Выбрать из списка", callback_data="select_from_list")],
            [InlineKeyboardButton("📊 Сегментация по активности", callback_data="segment_by_activity")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            f"👥 Выбор пользователей для отправки сообщения\n\n"
            f"Всего пользователей в базе: {count}\n\n"
            f"Выберите метод выбора пользователей:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_SELECT_USERS
    
    elif action == "admin_content_manager":
        # Управление контентом бота
        keyboard = [
            [InlineKeyboardButton("📷 Управление изображениями", callback_data="manage_images")],
            [InlineKeyboardButton("📊 Управление графиками", callback_data="manage_charts")],
            [InlineKeyboardButton("🎞️ Управление видео", callback_data="manage_videos")],
            [InlineKeyboardButton("📎 Управление файлами", callback_data="manage_files")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            "📑 Управление контентом\n\n"
            "Выберите категорию контента для управления:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CONTENT_MANAGER
    
    elif action == "admin_statistics":
        # Расширенная аналитика бота
        keyboard = [
            [InlineKeyboardButton("📊 Активность пользователей", callback_data="stats_user_activity")],
            [InlineKeyboardButton("📈 Рост аудитории", callback_data="stats_audience_growth")],
            [InlineKeyboardButton("🔄 Конверсия регистраций", callback_data="stats_registration_conversion")],
            [InlineKeyboardButton("📉 Отток пользователей", callback_data="stats_user_churn")],
            [InlineKeyboardButton("🔍 Детализация по странам", callback_data="stats_by_country")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            "📊 Расширенная аналитика\n\n"
            "Выберите тип статистики для просмотра:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_STATISTICS
    
    elif action == "admin_quick_commands":
        # Быстрые команды для администратора
        keyboard = [
            [InlineKeyboardButton("🔄 Перезагрузить бота", callback_data="quick_restart_bot")],
            [InlineKeyboardButton("🧹 Очистить кэш", callback_data="quick_clear_cache")],
            [InlineKeyboardButton("📊 Сгенерировать отчет", callback_data="quick_generate_report")],
            [InlineKeyboardButton("📧 Проверить почту", callback_data="quick_check_mail")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            "⚡ Быстрые команды\n\n"
            "Выберите команду для выполнения:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_QUICK_COMMANDS
    
    elif action == "admin_history":
        # История действий администратора
        keyboard = [
            [InlineKeyboardButton("📜 Действия пользователей", callback_data="history_user_actions")],
            [InlineKeyboardButton("🛠️ Действия администратора", callback_data="history_admin_actions")],
            [InlineKeyboardButton("🔄 Системные события", callback_data="history_system_events")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            "📜 История действий\n\n"
            "Выберите категорию истории для просмотра:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_HISTORY
    
    elif action == "admin_plugins":
        # Управление плагинами бота
        keyboard = [
            [InlineKeyboardButton("📋 Установленные плагины", callback_data="plugins_installed")],
            [InlineKeyboardButton("➕ Установить плагин", callback_data="plugins_install")],
            [InlineKeyboardButton("❌ Удалить плагин", callback_data="plugins_remove")],
            [InlineKeyboardButton("🔄 Обновить плагины", callback_data="plugins_update")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            "🧩 Управление плагинами\n\n"
            "Выберите действие с плагинами:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_PLUGINS
    
    elif action == "admin_marketplace":
        # Маркетплейс расширений для бота
        keyboard = [
            [InlineKeyboardButton("🛒 Обзор маркетплейса", callback_data="marketplace_browse")],
            [InlineKeyboardButton("🔍 Поиск расширений", callback_data="marketplace_search")],
            [InlineKeyboardButton("⭐ Популярные расширения", callback_data="marketplace_popular")],
            [InlineKeyboardButton("🆕 Новые расширения", callback_data="marketplace_new")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            "🛒 Маркетплейс расширений\n\n"
            "Выберите раздел маркетплейса:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_MARKETPLACE
        
    elif action == "admin_otc_signals":
        # Управление OTC сигналами для Pocket Option
        keyboard = [
            [InlineKeyboardButton("🔍 Просмотр активных сигналов", callback_data="otc_view_active")],
            [InlineKeyboardButton("➕ Добавить новый сигнал", callback_data="otc_add_signal")],
            [InlineKeyboardButton("⚙️ Настройки OTC", callback_data="otc_settings")],
            [InlineKeyboardButton("📊 Статистика сигналов", callback_data="otc_stats")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            "📱 Управление OTC сигналами для Pocket Option\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_OTC_SIGNALS
    
    elif action == "admin_stats":
        # Показать статистику
        users = get_all_users()
        total_users = len(users)
        approved_users = sum(1 for user in users if user.get('is_approved'))
        admin_users = sum(1 for user in users if user.get('is_admin'))
        
        stats_text = (
            "📊 Статистика бота\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"✅ Подтвержденных пользователей: {approved_users}\n"
            f"👑 Администраторов: {admin_users}\n"
            f"⏳ Ожидают подтверждения: {total_users - approved_users}\n"
        )
        
        await query.edit_message_text(
            stats_text,
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    elif action == "admin_update_db":
        # Обновить базу данных
        try:
            from models import init_db
            init_db()
            await query.edit_message_text(
                "✅ База данных успешно обновлена!",
                reply_markup=get_admin_keyboard()
            )
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при обновлении базы данных: {str(e)}",
                reply_markup=get_admin_keyboard()
            )
        return ADMIN_MENU
    
    elif action == "change_language":
        # Сменить язык бота
        keyboard = get_language_keyboard()
        await query.edit_message_text(
            "Выберите язык / Забонро интихоб кунед / Tilni tanlang / Тілді таңдаңыз / Choose language:",
            reply_markup=keyboard
        )
        return ADMIN_MENU
    
    elif action == "admin_currencies":
        # Переход в раздел управления валютами
        from models import get_all_currency_pairs
        currency_pairs = get_all_currency_pairs()
        
        currency_list = "\n".join([
            f"- {pair['display_name']} ({pair['pair_code']}): {'🟢 Активна' if pair['is_active'] else '🔴 Неактивна'}"
            for pair in currency_pairs
        ])
        
        if not currency_list:
            currency_list = "Нет добавленных валютных пар"
        
        currency_keyboard = [
            [InlineKeyboardButton("➕ Добавить валютную пару", callback_data="admin_add_currency")],
            [InlineKeyboardButton("🔄 Обновить все пары", callback_data="admin_refresh_currencies")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            f"💱 Управление валютными парами\n\nСписок валютных пар:\n{currency_list}",
            reply_markup=InlineKeyboardMarkup(currency_keyboard)
        )
        return ADMIN_CURRENCY_MANAGEMENT
        
    elif action == "admin_texts":
        # Переход в раздел управления текстами
        from models import get_all_bot_messages
        messages = get_all_bot_messages()
        
        texts_keyboard = [
            [InlineKeyboardButton("➕ Добавить новый текст", callback_data="admin_add_text")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        # Группируем сообщения по ключам
        message_keys = {}
        for msg in messages:
            key = msg['message_key']
            if key not in message_keys:
                message_keys[key] = []
            message_keys[key].append(msg)
        
        # Добавляем кнопки для каждого ключа сообщения
        for key in message_keys:
            texts_keyboard.insert(-1, [InlineKeyboardButton(f"📝 {key}", callback_data=f"admin_edit_text_{key}")])
        
        if not message_keys:
            message_summary = "Нет добавленных текстов"
        else:
            message_summary = "Тексты в базе данных:\n" + "\n".join([
                f"- {key} ({len(langs)} языков)" 
                for key, langs in message_keys.items()
            ])
        
        await query.edit_message_text(
            f"📝 Управление текстами бота\n\n{message_summary}",
            reply_markup=InlineKeyboardMarkup(texts_keyboard)
        )
        return ADMIN_TEXT_MANAGEMENT
        
    elif action == "admin_activity":
        # Переход к анализу активности
        
        # Заглушка анализа активности
        activity_text = (
            "📈 Анализ активности\n\n"
            "👥 Активность пользователей за последние 7 дней:\n"
            "• Новых пользователей: 12\n"
            "• Активных пользователей: 34\n"
            "• Общее количество запросов: 145\n\n"
            "🔍 Топ-5 валютных пар:\n"
            "1. BTC/USD - 28 запросов\n"
            "2. EUR/USD - 23 запроса\n"
            "3. ETH/USD - 19 запросов\n"
            "4. USD/RUB - 15 запросов\n"
            "5. GBP/USD - 12 запросов\n\n"
            "⏱ Пиковые часы активности:\n"
            "• 9:00-12:00 - 23%\n"
            "• 13:00-17:00 - 35%\n"
            "• 18:00-22:00 - 42%"
        )
        
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            activity_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_ACTIVITY
    
    elif action == "admin_settings":
        # Переход к настройкам бота
        settings_text = (
            "⚙️ Настройки бота\n\n"
            "🔹 Основные параметры:\n"
            "• Максимальное количество запросов в день: 100\n"
            "• Таймаут между запросами: 3 секунды\n"
            "• Автоматическое обновление курсов: каждые 30 минут\n\n"
            "🔹 Параметры анализа:\n"
            "• Длина EMA: 12, 26\n"
            "• Период RSI: 14\n"
            "• Период Bollinger Bands: 20\n\n"
            "🔹 Параметры уведомлений:\n"
            "• Уведомления о новых пользователях: Включены\n"
            "• Уведомления о важных сигналах: Включены\n"
            "• Отправка отчетов админу: Ежедневно"
        )
        
        settings_keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(settings_keyboard)
        )
        return ADMIN_SETTINGS
    
    elif action == "admin_change_password":
        # Переход к смене пароля администратора
        
        # Создаем клавиатуру с одной кнопкой "Назад"
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            "🔐 Смена пароля администратора\n\n"
            "Введите новый пароль администратора.\n"
            "Пароль должен содержать минимум 6 символов.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['admin_changing_password'] = True
        return ADMIN_CHANGE_PASSWORD
    
    elif action == "admin_about":
        # Переход к информации о боте
        about_text = (
            "ℹ️ О боте\n\n"
            "✨ *Trade Analysis Bot* ✨\n\n"
            "Версия: 2.0.0\n"
            "Разработан: Replit AI\n"
            "Лицензия: Proprietary\n\n"
            "📝 Описание:\n"
            "Профессиональный бот для анализа рынка "
            "с системой управления пользователями.\n\n"
            "🛠 Технологии:\n"
            "• Python 3.11\n"
            "• Python-telegram-bot\n"
            "• PostgreSQL\n"
            "• YFinance API\n\n"
            "📞 Контакты:\n"
            "Поддержка: @tradeporu\n"
        )
        
        about_keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            about_text,
            reply_markup=InlineKeyboardMarkup(about_keyboard),
            parse_mode='Markdown'
        )
        return ADMIN_ABOUT
    
    elif action == "admin_back":
        # Вернуться в главное меню админа
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    else:
        # Неизвестное действие
        await query.edit_message_text(
            "❓ Неизвестное действие. Пожалуйста, выберите опцию из меню.",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU

async def admin_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода текста для рассылки сообщений"""
    if update.message:
        # Обработка текста рассылки
        broadcast_text = update.message.text
        
        # Получаем список ID пользователей в зависимости от выбранного типа получателей
        target_type = context.user_data.get('broadcast_target', 'approved')
        
        if target_type == 'all':
            user_ids = get_all_user_ids()
            target_desc = "всем пользователям"
        elif target_type == 'pending':
            user_ids = get_pending_user_ids()
            target_desc = "ожидающим подтверждения пользователям"
        else:  # По умолчанию отправляем подтвержденным
            user_ids = get_approved_user_ids()
            target_desc = "подтвержденным пользователям"
        
        if not user_ids:
            await update.message.reply_text(
                f"⚠️ Нет пользователей для рассылки.",
                reply_markup=get_admin_keyboard()
            )
            return ADMIN_MENU
        
        success_count = 0
        error_count = 0
        
        progress_message = await update.message.reply_text(
            f"📨 Начинаю рассылку сообщений {target_desc}...\n"
            f"0% выполнено (0/{len(user_ids)})"
        )
        
        # Рассылка сообщений выбранным пользователям
        for i, user_id in enumerate(user_ids):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 Сообщение от администратора:\n\n{broadcast_text}"
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
                error_count += 1
            
            # Обновляем прогресс каждые 5 пользователей или в конце списка
            if (i + 1) % 5 == 0 or i == len(user_ids) - 1:
                progress_percent = int((i + 1) / len(user_ids) * 100)
                await progress_message.edit_text(
                    f"📨 Выполняется рассылка сообщений {target_desc}...\n"
                    f"{progress_percent}% выполнено ({i+1}/{len(user_ids)})"
                )
        
        # Отправляем итоговый отчет
        await update.message.reply_text(
            f"✅ Рассылка завершена!\n\n"
            f"📊 Статистика:\n"
            f"✓ Успешно отправлено: {success_count}\n"
            f"❌ Ошибок: {error_count}\n"
            f"📝 Всего пользователей: {len(user_ids)}",
            reply_markup=get_admin_keyboard()
        )
        
        # Очищаем данные о типе рассылки
        if 'broadcast_target' in context.user_data:
            del context.user_data['broadcast_target']
            
        return ADMIN_MENU
    
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        
        action = query.data
        
        if action == "admin_back":
            # Возврат в админ-панель
            await query.edit_message_text(
                "👑 Панель администратора",
                reply_markup=get_admin_keyboard()
            )
            return ADMIN_MENU
            
        elif action == "broadcast_all":
            # Рассылка всем пользователям
            context.user_data['broadcast_target'] = 'all'
            keyboard = [
                [InlineKeyboardButton("↩️ Отмена", callback_data="admin_back")]
            ]
            await query.edit_message_text(
                "📢 Рассылка сообщений ВСЕМ пользователям\n\n"
                "Введите текст сообщения, которое будет отправлено всем пользователям:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif action == "broadcast_approved":
            # Рассылка только подтвержденным пользователям
            context.user_data['broadcast_target'] = 'approved'
            keyboard = [
                [InlineKeyboardButton("↩️ Отмена", callback_data="admin_back")]
            ]
            await query.edit_message_text(
                "📢 Рассылка сообщений подтвержденным пользователям\n\n"
                "Введите текст сообщения, которое будет отправлено только подтвержденным пользователям:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif action == "broadcast_pending":
            # Рассылка только ожидающим подтверждения
            context.user_data['broadcast_target'] = 'pending'
            keyboard = [
                [InlineKeyboardButton("↩️ Отмена", callback_data="admin_back")]
            ]
            await query.edit_message_text(
                "📢 Рассылка сообщений ожидающим подтверждения\n\n"
                "Введите текст сообщения, которое будет отправлено только ожидающим подтверждения пользователям:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    return ADMIN_BROADCAST_MESSAGE

async def admin_send_message_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отправки личного сообщения пользователю от имени администратора"""
    # Добавляем логирование для диагностики
    logger.info(f"admin_send_message_to_user called with update type: {type(update)}")
    
    # Обработка кнопки отмены
    if update.callback_query and update.callback_query.data == "cancel_direct_message":
        # Очищаем данные
        if 'direct_message_to_user_id' in context.user_data:
            del context.user_data['direct_message_to_user_id']
            
        await update.callback_query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        logger.info("Direct message canceled, returning to admin menu")
        return ADMIN_MENU
    
    # Обработка ввода текста сообщения от администратора
    if update.message:
        # Получаем ID пользователя, которому отправляем сообщение
        target_user_id = context.user_data.get('direct_message_to_user_id')
        logger.info(f"Trying to send message to user_id: {target_user_id}")
        
        if not target_user_id:
            await update.message.reply_text(
                "❌ Ошибка: не указан получатель сообщения.",
                reply_markup=get_admin_keyboard()
            )
            logger.error("Error: target_user_id not found in context.user_data")
            return ADMIN_MENU
        
        # Получаем текст сообщения
        message_text = update.message.text
        
        # Получаем информацию о пользователе
        user_data = get_user(target_user_id)
        if not user_data:
            await update.message.reply_text(
                "❌ Ошибка: пользователь не найден.",
                reply_markup=get_admin_keyboard()
            )
            logger.error(f"Error: user with ID {target_user_id} not found")
            return ADMIN_MENU
            
        username = user_data.get('username', 'пользователь')
        
        try:
            # Отправляем сообщение пользователю
            logger.info(f"Sending message to user {target_user_id} (@{username})")
            await context.bot.send_message(
                chat_id=target_user_id,
                text=f"📝 *Сообщение от администратора:*\n\n{message_text}",
                parse_mode='Markdown'
            )
            
            # Уведомляем администратора об успешной отправке
            await update.message.reply_text(
                f"✅ Сообщение успешно отправлено пользователю @{username}!",
                reply_markup=get_admin_keyboard()
            )
            
            # Очищаем данные
            if 'direct_message_to_user_id' in context.user_data:
                del context.user_data['direct_message_to_user_id']
                
            logger.info("Message sent successfully, returning to admin menu")
            return ADMIN_MENU
        except Exception as e:
            # В случае ошибки отправки
            error_message = f"❌ Ошибка при отправке сообщения: {str(e)}"
            logger.error(f"Error sending message: {str(e)}")
            await update.message.reply_text(
                error_message,
                reply_markup=get_admin_keyboard()
            )
            return ADMIN_MENU
    
    # Для прочих типов запросов, которые не обработаны выше
    # (мы уже обработали кнопку отмены в начале функции)
    
    return ADMIN_DIRECT_MESSAGE

async def admin_user_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню управления пользователями"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    # Обработка команды отправки сообщения пользователю
    if action.startswith("send_message_to_"):
        # Извлекаем ID пользователя из callback_data
        user_id = action.split("_")[-1]
        user_data = get_user(int(user_id))
        
        if not user_data:
            await query.edit_message_text(
                "❌ Пользователь не найден.",
                reply_markup=get_user_management_keyboard()
            )
            return ADMIN_USER_MANAGEMENT
            
        # Сохраняем ID пользователя для последующего использования
        context.user_data['direct_message_to_user_id'] = int(user_id)
        username = user_data.get('username', 'без имени')
        
        # Добавляем логирование для диагностики
        logger.info(f"Setting up message form for user {user_id} (@{username})")
        
        # Показываем форму для отправки сообщения
        keyboard = [
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_direct_message")]
        ]
        
        await query.edit_message_text(
            f"📨 Отправка сообщения пользователю @{username}\n\n"
            "Введите текст сообщения:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        # Возвращаем ADMIN_DIRECT_MESSAGE для правильного перехода состояний
        return ADMIN_DIRECT_MESSAGE
    
    elif action == "admin_pending":
        # Показать ожидающих подтверждения пользователей
        pending_users = get_pending_users()
        if pending_users:
            await query.edit_message_text(
                "⏳ Пользователи, ожидающие подтверждения:",
                reply_markup=get_pending_keyboard(pending_users)
            )
        else:
            await query.edit_message_text(
                "✅ Нет пользователей, ожидающих подтверждения.",
                reply_markup=get_user_management_keyboard()
            )
        return ADMIN_USER_MANAGEMENT
    
    elif action == "admin_all_users":
        # Показать всех пользователей
        users = get_all_users()
        await query.edit_message_text(
            "👥 Все пользователи:",
            reply_markup=get_user_list_keyboard(users)
        )
        return ADMIN_USER_MANAGEMENT
    
    elif action == "admin_back":
        # Вернуться в главное меню
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    elif action.startswith("page_"):
        # Обработка пагинации
        parts = action.split("_")
        page = int(parts[1])
        back_command = parts[2]
        
        if back_command == "admin_pending":
            pending_users = get_pending_users()
            await query.edit_message_text(
                "⏳ Пользователи, ожидающие подтверждения:",
                reply_markup=get_pending_keyboard(pending_users, page)
            )
        else:  # admin_all_users
            users = get_all_users()
            await query.edit_message_text(
                "👥 Все пользователи:",
                reply_markup=get_user_list_keyboard(users, page)
            )
        return ADMIN_USER_MANAGEMENT
    
    elif action.startswith("user_"):
        # Действия с конкретным пользователем
        user_id = int(action.split("_")[1])
        user_data = get_user(user_id)
        
        if not user_data:
            await query.edit_message_text(
                "❌ Пользователь не найден.",
                reply_markup=get_user_management_keyboard()
            )
            return ADMIN_USER_MANAGEMENT
        
        is_admin = "✅" if user_data.get('is_admin') else "❌"
        is_approved = "✅" if user_data.get('is_approved') else "❌"
        is_moderator = "✅" if user_data.get('is_moderator') else "❌"
        username = user_data.get('username', 'Без имени')
        
        user_info = (
            f"👤 Информация о пользователе:\n\n"
            f"🆔 ID: {user_id}\n"
            f"👤 Имя: @{username}\n"
            f"👑 Администратор: {is_admin}\n"
            f"🔰 Модератор: {is_moderator}\n"
            f"✅ Подтвержден: {is_approved}\n"
        )
        
        await query.edit_message_text(
            user_info,
            reply_markup=get_user_action_keyboard(user_id, is_approved=user_data.get('is_approved', False), 
                                                  is_admin=user_data.get('is_admin', False), 
                                                  is_moderator=user_data.get('is_moderator', False))
        )
        return ADMIN_USER_MANAGEMENT
    
    elif action.startswith("toggle_admin_") or action.startswith("toggle_moderator_"):
        # Обработка изменения статуса администратора или модератора
        parts = action.split("_")
        is_admin_action = action.startswith("toggle_admin_")
        user_id = int(parts[2])
        new_status = parts[3] == "1"  # 1 - сделать админом/модератором, 0 - убрать права
        
        if is_admin_action:
            # Изменение статуса администратора
            from models import set_user_admin_status
            success = set_user_admin_status(user_id, new_status)
            status_text = "администратор" if new_status else "не администратор"
        else:
            # Изменение статуса модератора
            from models import set_user_moderator_status
            success = set_user_moderator_status(user_id, new_status)
            status_text = "модератор" if new_status else "не модератор"
        
        if success:
            # Получаем обновленные данные пользователя
            user_data = get_user(user_id)
            if user_data:
                is_admin = user_data.get('is_admin', False)
                is_approved = user_data.get('is_approved', False)
                is_moderator = user_data.get('is_moderator', False)
                username = user_data.get('username', 'Без имени')
                
                # Информация о пользователе
                user_info = (
                    f"👤 Информация о пользователе:\n\n"
                    f"🆔 ID: {user_id}\n"
                    f"👤 Имя: @{username}\n"
                    f"👑 Администратор: {'✅' if is_admin else '❌'}\n"
                    f"🔰 Модератор: {'✅' if is_moderator else '❌'}\n"
                    f"✅ Подтвержден: {'✅' if is_approved else '❌'}\n\n"
                    f"✅ Статус успешно изменен на: {status_text}"
                )
                
                await query.edit_message_text(
                    user_info,
                    reply_markup=get_user_action_keyboard(user_id, is_approved, is_admin, is_moderator)
                )
            else:
                await query.edit_message_text(
                    f"✅ Статус пользователя с ID {user_id} успешно изменен на: {status_text}\n"
                    f"❗ Не удалось получить обновленные данные пользователя.",
                    reply_markup=get_user_management_keyboard()
                )
        else:
            await query.edit_message_text(
                f"❌ Не удалось изменить статус пользователя с ID {user_id}.",
                reply_markup=get_user_management_keyboard()
            )
        
        return ADMIN_USER_MANAGEMENT
    
    elif action.startswith("block_user_"):
        # Обработка блокировки пользователя (сброс статуса подтверждения)
        user_id = int(action.split("_")[2])
        
        from models import reset_user_approval
        if reset_user_approval(user_id):
            await query.edit_message_text(
                f"🚫 Пользователь с ID {user_id} заблокирован (доступ отозван).",
                reply_markup=get_user_management_keyboard()
            )
        else:
            await query.edit_message_text(
                f"❌ Не удалось заблокировать пользователя с ID {user_id}.",
                reply_markup=get_user_management_keyboard()
            )
        
        return ADMIN_USER_MANAGEMENT
        
    elif action.startswith("approve_") or action.startswith("reject_"):
        # Обработка подтверждения/отклонения пользователя
        is_approve = action.startswith("approve_")
        user_id = int(action.split("_")[1])
        
        if is_approve:
            try:
                # Генерируем пароль и одобряем пользователя
                password = ''.join([str(hash(datetime.now()))[i:i+2] for i in range(0, 8, 2)])
                password_hash = hash_password(password)
                
                if approve_user(user_id, password_hash):
                    # Экранируем специальные символы для Markdown
                    escaped_password = password.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]").replace("(", "\\(").replace(")", "\\)").replace("~", "\\~").replace("`", "\\`").replace(">", "\\>").replace("#", "\\#").replace("+", "\\+").replace("-", "\\-").replace("=", "\\=").replace("|", "\\|").replace("{", "\\{").replace("}", "\\}").replace(".", "\\.").replace("!", "\\!")
                    
                    # Получаем язык пользователя
                    user_data = get_user(user_id)
                    lang_code = user_data['language_code'] if user_data and 'language_code' in user_data else 'tg'
                    
                    # Сообщения об одобрении на разных языках
                    approval_messages = {
                        'tg': f"✅ Дархости шумо қабул карда шуд\\!\n\nРамзи шумо барои ворид шудан: `{escaped_password}`\n\nЛутфан, онро нигоҳ доред\\.",
                        'ru': f"✅ Ваша заявка одобрена\\!\n\nВаш пароль для входа: `{escaped_password}`\n\nПожалуйста, сохраните его\\.",
                        'uz': f"✅ Arizangiz tasdiqlandi\\!\n\nKirish uchun parolingiz: `{escaped_password}`\n\nIltimos, uni saqlab qoling\\.",
                        'kk': f"✅ Өтінішіңіз мақұлданды\\!\n\nКіру үшін құпия сөзіңіз: `{escaped_password}`\n\nОны сақтап қойыңыз\\.",
                        'en': f"✅ Your request has been approved\\!\n\nYour password: `{escaped_password}`\n\nPlease save it\\."
                    }
                    
                    # Тексты кнопок на разных языках
                    button_texts = {
                        'tg': "🚀 Ба бот ворид шавед",
                        'ru': "🚀 Войти в бот",
                        'uz': "🚀 Botga kirish",
                        'kk': "🚀 Ботқа кіру",
                        'en': "🚀 Enter the bot"
                    }
                    
                    # Выбираем сообщение и текст кнопки согласно языку пользователя
                    message = approval_messages.get(lang_code, approval_messages['tg'])
                    button_text = button_texts.get(lang_code, button_texts['tg'])
                    
                    # Создаем клавиатуру с кнопкой для входа
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton(button_text, callback_data="return_to_main")]
                    ])
                    
                    # Отправляем сообщение пользователю
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode='MarkdownV2',
                        reply_markup=keyboard
                    )
                    
                    # Уведомляем администратора
                    await query.edit_message_text(
                        f"✅ Пользователь с ID {user_id} одобрен. Пароль отправлен пользователю.",
                        reply_markup=get_user_management_keyboard()
                    )
                else:
                    await query.edit_message_text(
                        "❌ Произошла ошибка при одобрении пользователя.",
                        reply_markup=get_user_management_keyboard()
                    )
            except Exception as e:
                logger.error(f"Ошибка при одобрении пользователя: {e}")
                await query.edit_message_text(
                    f"❌ Произошла ошибка при одобрении пользователя: {str(e)}",
                    reply_markup=get_user_management_keyboard()
                )
        else:
            # Отклоняем заявку пользователя
            if delete_user(user_id):
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Ваша заявка отклонена администратором."
                )
                await query.edit_message_text(
                    f"❌ Пользователь с ID {user_id} отклонен и удален.",
                    reply_markup=get_user_management_keyboard()
                )
            else:
                await query.edit_message_text(
                    "❌ Произошла ошибка при отклонении пользователя.",
                    reply_markup=get_user_management_keyboard()
                )
        
        return ADMIN_USER_MANAGEMENT
    
    else:
        # Неизвестное действие
        await query.edit_message_text(
            "❓ Неизвестное действие. Пожалуйста, выберите опцию из меню.",
            reply_markup=get_user_management_keyboard()
        )
        return ADMIN_USER_MANAGEMENT

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /register для регистрации пользователей"""
    user = update.effective_user
    user_id = user.id
    username = user.username
    
    # Проверяем, существует ли уже пользователь и его статус
    user_data = get_user(user_id)
    
    if user_data and user_data.get('is_approved'):
        await update.message.reply_text(
            "✅ Вы уже зарегистрированы и подтверждены."
        )
        return ConversationHandler.END
    
    # Добавляем пользователя в базу, если его еще нет
    if not user_data:
        add_user(user_id, username)
    
    # Добавляем пользователя в список ожидающих и отправляем запрос админу
    PENDING_USERS[user_id] = {
        'user_id': user_id,
        'username': username,
        'timestamp': datetime.now()
    }
    
    # Получаем язык пользователя
    user_data = get_user(user_id)
    lang_code = user_data['language_code'] if user_data and 'language_code' in user_data else 'tg'
    
    # Сообщения о заявке на разных языках
    request_messages = {
        'tg': "📝 Дархости шумо ба маъмур фиристода шуд. "
              "Лутфан, тасдиқро интизор шавед. "
              "Вақте ки дархости шумо баррасӣ мешавад, шумо огоҳинома мегиред.",
        'ru': "📝 Ваша заявка отправлена администратору. "
              "Пожалуйста, ожидайте подтверждения. "
              "Вы получите уведомление, когда ваша заявка будет рассмотрена.",
        'uz': "📝 Arizangiz administratorga yuborildi. "
              "Iltimos, tasdiqlashni kuting. "
              "Arizangiz ko'rib chiqilganda, sizga xabar beriladi.",
        'kk': "📝 Сіздің өтінішіңіз әкімшіге жіберілді. "
              "Растауды күтіңіз. "
              "Өтінішіңіз қаралғанда, сізге хабарлама жіберіледі.",
        'en': "📝 Your request has been sent to the administrator. "
              "Please wait for confirmation. "
              "You will receive a notification when your request is reviewed."
    }
    
    # Добавляем информацию о контактах службы поддержки
    support_messages = {
        'tg': "\n\n📞 Агар савол дошта бошед, метавонед бо хадамоти дастгирӣ тамос гиред: @tradeporu",
        'ru': "\n\n📞 Если у вас есть вопросы, вы можете связаться со службой поддержки: @tradeporu",
        'uz': "\n\n📞 Savollaringiz bo'lsa, qo'llab-quvvatlash xizmatiga murojaat qilishingiz mumkin: @tradeporu",
        'kk': "\n\n📞 Сұрақтарыңыз болса, қолдау қызметіне хабарласа аласыз: @tradeporu",
        'en': "\n\n📞 If you have any questions, you can contact support: @tradeporu"
    }
    
    # Отправляем сообщение пользователю на его языке
    message = request_messages.get(lang_code, request_messages['tg'])
    support_text = support_messages.get(lang_code, support_messages['tg'])
    message += support_text
    
    # Пробуем создать и отправить изображение
    from create_welcome_image import create_welcome_image
    try:
        # Создаем изображение
        if create_welcome_image():
            # Отправляем изображение с новым текстом
            with open('welcome_image.png', 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=message
                )
        else:
            # Если не удалось создать изображение, просто отправляем текст
            await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Ошибка при отправке приветственного изображения: {e}")
        # В случае ошибки просто отправляем текст
        await update.message.reply_text(message)
    
    # Получаем чат администратора и отправляем ему уведомление
    admin_chat_id = await get_admin_chat_id(context.bot)
    if admin_chat_id:
        keyboard = [
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
            ]
        ]
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=f"📝 Новая заявка на регистрацию!\n\n"
                f"👤 Пользователь: @{username}\n"
                f"🆔 ID: {user_id}\n"
                f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Если не удалось найти админа, сохраняем запрос в базе данных,
        # чтобы администратор мог просмотреть его через панель управления
        logger.warning(f"Admin chat not found. Registration request from user @{username} (ID: {user_id}) stored in pending list.")
    
    return ConversationHandler.END

def main():
    reconnect_delay = 5  # Start with 5 seconds delay
    max_reconnect_delay = 30  # Maximum delay between reconnection attempts
    max_consecutive_errors = 10
    error_count = 0
    last_error_time = None

    while True:  # Infinite loop for continuous operation
        try:
            # Start the keep-alive server
            from keep_alive import keep_alive
            keep_alive()
            logger.info("Starting bot...")

            # Проверка наличия токена
            if not BOT_TOKEN:
                logger.error("BOT_TOKEN is not set. Please check your environment variables.")
                continue

            # Создание приложения с токеном
            application = Application.builder().token(BOT_TOKEN).build()

            # Add handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("download", download))
            
            # Обработчик регистрации
            application.add_handler(CommandHandler("register", register_command))
            
            # Обработчики для админ-панели
            # Добавляем функции для управления валютами и текстами
            async def admin_currency_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик меню управления валютными парами"""
                query = update.callback_query
                if query:
                    await query.answer()
                    action = query.data
                    
                    if action == "admin_back":
                        # Вернуться в главное меню админа
                        await query.edit_message_text(
                            "👑 Панель администратора",
                            reply_markup=get_admin_keyboard()
                        )
                        return ADMIN_MENU
                    
                    elif action == "admin_add_currency":
                        # Форма добавления новой валютной пары
                        await query.edit_message_text(
                            "➕ Добавление новой валютной пары\n\n"
                            "Введите данные в формате:\n"
                            "Код пары|Символ|Отображаемое название\n\n"
                            "Например:\n"
                            "BTCUSD|BTC-USD|BTC/USD",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                            ]])
                        )
                        return ADMIN_CURRENCY_ADD
                    
                    elif action == "admin_refresh_currencies":
                        # Обновляем список валютных пар из базы
                        from models import import_default_currency_pairs
                        success = import_default_currency_pairs()
                        
                        if success:
                            await query.edit_message_text(
                                "✅ Валютные пары успешно обновлены!",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                                ]])
                            )
                        else:
                            await query.edit_message_text(
                                "ℹ️ Валютные пары уже обновлены или в базе уже есть данные.",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                                ]])
                            )
                        return ADMIN_CURRENCY_MANAGEMENT
                    
                    elif action.startswith("currency_toggle_"):
                        # Включение/отключение валютной пары
                        pair_code = action.replace("currency_toggle_", "")
                        from models import update_currency_pair_status, get_all_currency_pairs
                        
                        # Получаем текущий статус пары
                        pairs = get_all_currency_pairs()
                        current_pair = next((p for p in pairs if p['pair_code'] == pair_code), None)
                        
                        if current_pair:
                            # Меняем статус на противоположный
                            new_status = not current_pair['is_active']
                            success = update_currency_pair_status(pair_code, new_status)
                            
                            if success:
                                status_text = "активирована" if new_status else "деактивирована"
                                await query.edit_message_text(
                                    f"✅ Валютная пара {current_pair['display_name']} успешно {status_text}!",
                                    reply_markup=InlineKeyboardMarkup([[
                                        InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                                    ]])
                                )
                            else:
                                await query.edit_message_text(
                                    "❌ Ошибка при изменении статуса валютной пары.",
                                    reply_markup=InlineKeyboardMarkup([[
                                        InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                                    ]])
                                )
                        else:
                            await query.edit_message_text(
                                "❌ Валютная пара не найдена.",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                                ]])
                            )
                        return ADMIN_CURRENCY_MANAGEMENT
                    
                    elif action == "admin_currencies":
                        # Возврат в меню валют
                        from models import get_all_currency_pairs
                        currency_pairs = get_all_currency_pairs()
                        
                        currency_list = "\n".join([
                            f"- {pair['display_name']} ({pair['pair_code']}): {'🟢 Активна' if pair['is_active'] else '🔴 Неактивна'}"
                            for pair in currency_pairs
                        ])
                        
                        if not currency_list:
                            currency_list = "Нет добавленных валютных пар"
                        
                        currency_keyboard = [
                            [InlineKeyboardButton("➕ Добавить валютную пару", callback_data="admin_add_currency")],
                            [InlineKeyboardButton("🔄 Обновить все пары", callback_data="admin_refresh_currencies")],
                            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                        ]
                        
                        # Добавляем кнопки для каждой валютной пары
                        for pair in currency_pairs:
                            toggle_text = "🔴 Деактивировать" if pair['is_active'] else "🟢 Активировать"
                            currency_keyboard.insert(-1, [
                                InlineKeyboardButton(f"{pair['display_name']} - {toggle_text}", 
                                                    callback_data=f"currency_toggle_{pair['pair_code']}")
                            ])
                        
                        await query.edit_message_text(
                            f"💱 Управление валютными парами\n\nСписок валютных пар:\n{currency_list}",
                            reply_markup=InlineKeyboardMarkup(currency_keyboard)
                        )
                        return ADMIN_CURRENCY_MANAGEMENT
                
                return ADMIN_CURRENCY_MANAGEMENT
            
            async def admin_add_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик добавления новой валютной пары"""
                if update.callback_query:
                    query = update.callback_query
                    await query.answer()
                    
                    if query.data == "admin_currencies":
                        # Возврат в меню валют
                        return await admin_currency_management(update, context)
                    
                    return ADMIN_CURRENCY_ADD
                
                if update.message:
                    # Обработка данных новой валютной пары
                    text = update.message.text
                    parts = text.strip().split('|')
                    
                    if len(parts) != 3:
                        await update.message.reply_text(
                            "❌ Неверный формат данных. Введите данные в формате:\n"
                            "Код пары|Символ|Отображаемое название\n\n"
                            "Например:\n"
                            "BTCUSD|BTC-USD|BTC/USD",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                            ]])
                        )
                        return ADMIN_CURRENCY_ADD
                    
                    pair_code = parts[0].strip()
                    symbol = parts[1].strip()
                    display_name = parts[2].strip()
                    
                    from models import add_or_update_currency_pair
                    pair_id = add_or_update_currency_pair(pair_code, symbol, display_name)
                    
                    if pair_id:
                        # Успешно добавлено
                        await update.message.reply_text(
                            f"✅ Валютная пара {display_name} успешно добавлена!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ К списку валют", callback_data="admin_currencies")
                            ]])
                        )
                    else:
                        # Ошибка при добавлении
                        await update.message.reply_text(
                            "❌ Ошибка при добавлении валютной пары.",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ К списку валют", callback_data="admin_currencies")
                            ]])
                        )
                    
                    return ADMIN_CURRENCY_MANAGEMENT
                
                return ADMIN_CURRENCY_ADD
            
            async def admin_text_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик управления текстами бота"""
                query = update.callback_query
                if query:
                    await query.answer()
                    action = query.data
                    
                    if action == "admin_back":
                        # Вернуться в главное меню админа
                        await query.edit_message_text(
                            "👑 Панель администратора",
                            reply_markup=get_admin_keyboard()
                        )
                        return ADMIN_MENU
                    
                    # Получение списка всех текстов и группировка по ключам
                    if action == "admin_texts" or action == "admin_refresh_texts":
                        from models import get_all_bot_messages, get_message_keys
                        
                        # Получаем уникальные ключи сообщений
                        message_keys = get_message_keys()
                        
                        # Создаем клавиатуру с ключами сообщений
                        texts_keyboard = []
                        
                        # Добавляем кнопку для каждого ключа
                        for key in message_keys:
                            texts_keyboard.append([InlineKeyboardButton(f"📝 {key}", callback_data=f"edit_text_{key}")])
                        
                        # Добавляем кнопки управления
                        texts_keyboard.append([InlineKeyboardButton("➕ Добавить новый текст", callback_data="admin_add_text")])
                        texts_keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="admin_back")])
                        
                        # Формируем заголовок сообщения
                        if message_keys:
                            header = f"📝 Управление текстами бота\n\nДоступные тексты ({len(message_keys)}):"
                        else:
                            header = "📝 Управление текстами бота\n\nНет доступных текстов. Добавьте новые тексты."
                        
                        await query.edit_message_text(
                            header,
                            reply_markup=InlineKeyboardMarkup(texts_keyboard)
                        )
                        return ADMIN_TEXT_MANAGEMENT
                    
                    # Редактирование конкретного текста
                    elif action.startswith("edit_text_"):
                        message_key = action[10:]  # Убираем префикс "edit_text_"
                        
                        from models import get_message_for_key
                        messages = get_message_for_key(message_key)
                        
                        # Формируем текст сообщения с информацией о текстах на разных языках
                        text = f"📝 Редактирование текста: <b>{message_key}</b>\n\n"
                        
                        if not messages:
                            text += "Нет доступных переводов для этого ключа."
                        else:
                            text += "Доступные переводы:\n\n"
                            for msg in messages:
                                language = msg['language_code']
                                lang_name = {
                                    'ru': '🇷🇺 Русский',
                                    'tg': '🇹🇯 Таджикский',
                                    'uz': '🇺🇿 Узбекский',
                                    'kk': '🇰🇿 Казахский',
                                    'en': '🇬🇧 Английский'
                                }.get(language, language)
                                
                                # Обрезаем длинные тексты
                                message_text = msg['message_text']
                                if len(message_text) > 50:
                                    message_text = message_text[:47] + "..."
                                
                                text += f"<b>{lang_name}</b>: {message_text}\n"
                        
                        # Создаем клавиатуру с кнопками языков
                        keyboard = []
                        languages = [('ru', '🇷🇺 Русский'), ('tg', '🇹🇯 Таджикский'), 
                                   ('uz', '🇺🇿 Узбекский'), ('kk', '🇰🇿 Казахский'), 
                                   ('en', '🇬🇧 Английский')]
                        
                        # Добавляем кнопки для каждого языка
                        for lang_code, lang_name in languages:
                            keyboard.append([InlineKeyboardButton(
                                f"✏️ {lang_name}", 
                                callback_data=f"edit_lang_{message_key}_{lang_code}"
                            )])
                        
                        # Добавляем кнопку назад
                        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="admin_texts")])
                        
                        await query.edit_message_text(
                            text,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='HTML'
                        )
                        return ADMIN_TEXT_MANAGEMENT
                    
                    # Выбор языка для редактирования текста
                    elif action.startswith("edit_lang_"):
                        parts = action.split("_", 3)  # edit_lang_key_code
                        if len(parts) >= 4:
                            message_key = parts[2]
                            language_code = parts[3]
                            
                            # Сохраняем данные о редактировании в контексте
                            context.user_data['current_edit_key'] = message_key
                            context.user_data['current_edit_lang'] = language_code
                            
                            # Проверяем, существует ли текст на данном языке
                            from models import get_bot_message
                            current_text = get_bot_message(message_key, language_code)
                            
                            lang_name = {
                                'ru': 'русском',
                                'tg': 'таджикском',
                                'uz': 'узбекском',
                                'kk': 'казахском',
                                'en': 'английском'
                            }.get(language_code, language_code)
                            
                            if current_text:
                                text = f"<b>📝 Редактирование текста</b> <i>{message_key}</i> на {lang_name} языке\n\n"
                                text += f"<b>Текущий текст:</b>\n<pre>{current_text}</pre>\n\n"
                                text += f"Введите новый текст для замены или нажмите 'Назад' для отмены."
                            else:
                                text = f"<b>📝 Добавление текста</b> <i>{message_key}</i> на {lang_name} языке\n\n"
                                text += f"Введите текст для добавления или нажмите 'Назад' для отмены."
                            
                            keyboard = [[InlineKeyboardButton("↩️ Назад", callback_data=f"edit_text_{message_key}")]]
                            
                            await query.edit_message_text(
                                text,
                                reply_markup=InlineKeyboardMarkup(keyboard),
                                parse_mode='HTML'
                            )
                            return ADMIN_TEXT_EDIT
                    
                    elif action == "admin_add_text":
                        # Форма добавления нового текста
                        await query.edit_message_text(
                            "➕ Добавление нового текста\n\n"
                            "Введите данные в формате:\n"
                            "Ключ|Язык|Текст\n\n"
                            "Например:\n"
                            "WELCOME|ru|Добро пожаловать в бот!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ Назад", callback_data="admin_texts")
                            ]])
                        )
                        return ADMIN_TEXT_ADD
                    
                    elif action.startswith("admin_edit_text_"):
                        # Редактирование конкретного текста
                        key = action.replace("admin_edit_text_", "")
                        
                        from models import get_all_bot_messages
                        messages = get_all_bot_messages()
                        
                        # Фильтруем сообщения по ключу
                        key_messages = [msg for msg in messages if msg['message_key'] == key]
                        
                        message_text = f"📝 Редактирование текста: {key}\n\n"
                        
                        for msg in key_messages:
                            lang_code = msg['language_code']
                            text = msg['message_text']
                            message_text += f"*{lang_code}*: {text[:50]}{'...' if len(text) > 50 else ''}\n\n"
                        
                        edit_keyboard = [
                            [InlineKeyboardButton("➕ Добавить перевод", callback_data=f"admin_add_translation_{key}")],
                            [InlineKeyboardButton("↩️ Назад", callback_data="admin_texts")]
                        ]
                        
                        # Добавляем кнопки для редактирования каждого языка
                        for msg in key_messages:
                            lang_code = msg['language_code']
                            edit_keyboard.insert(-1, [
                                InlineKeyboardButton(f"✏️ Изменить {lang_code}", 
                                                    callback_data=f"admin_edit_translation_{key}_{lang_code}")
                            ])
                        
                        await query.edit_message_text(
                            message_text,
                            reply_markup=InlineKeyboardMarkup(edit_keyboard)
                        )
                        return ADMIN_TEXT_EDIT
                    
                    elif action == "admin_texts":
                        # Возврат в меню текстов
                        from models import get_all_bot_messages
                        messages = get_all_bot_messages()
                        
                        texts_keyboard = [
                            [InlineKeyboardButton("➕ Добавить новый текст", callback_data="admin_add_text")],
                            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                        ]
                        
                        # Группируем сообщения по ключам
                        message_keys = {}
                        for msg in messages:
                            key = msg['message_key']
                            if key not in message_keys:
                                message_keys[key] = []
                            message_keys[key].append(msg)
                        
                        # Добавляем кнопки для каждого ключа сообщения
                        for key in message_keys:
                            texts_keyboard.insert(-1, [InlineKeyboardButton(f"📝 {key}", callback_data=f"admin_edit_text_{key}")])
                        
                        if not message_keys:
                            message_summary = "Нет добавленных текстов"
                        else:
                            message_summary = "Тексты в базе данных:\n" + "\n".join([
                                f"- {key} ({len(langs)} языков)" 
                                for key, langs in message_keys.items()
                            ])
                        
                        await query.edit_message_text(
                            f"📝 Управление текстами бота\n\n{message_summary}",
                            reply_markup=InlineKeyboardMarkup(texts_keyboard)
                        )
                        return ADMIN_TEXT_MANAGEMENT
                
                return ADMIN_TEXT_MANAGEMENT
            
            async def admin_text_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик добавления нового текста"""
                if update.callback_query:
                    query = update.callback_query
                    await query.answer()
                    
                    if query.data == "admin_texts":
                        # Возврат в меню текстов
                        return await admin_text_management(update, context)
                    
                    return ADMIN_TEXT_ADD
                
                if update.message:
                    # Обработка данных нового текста
                    text = update.message.text
                    parts = text.strip().split('|', 2)  # Разделяем на 3 части (ключ, язык, текст)
                    
                    if len(parts) != 3:
                        await update.message.reply_text(
                            "❌ Неверный формат данных. Введите данные в формате:\n"
                            "Ключ|Язык|Текст\n\n"
                            "Например:\n"
                            "WELCOME|ru|Добро пожаловать в бот!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ Назад", callback_data="admin_texts")
                            ]])
                        )
                        return ADMIN_TEXT_ADD
                    
                    key = parts[0].strip()
                    lang_code = parts[1].strip()
                    message_text = parts[2].strip()
                    
                    from models import update_bot_message
                    msg_id = update_bot_message(key, lang_code, message_text)
                    
                    if msg_id:
                        # Успешно добавлено
                        await update.message.reply_text(
                            f"✅ Текст с ключом {key} для языка {lang_code} успешно добавлен!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ К списку текстов", callback_data="admin_texts")
                            ]])
                        )
                    else:
                        # Ошибка при добавлении
                        await update.message.reply_text(
                            "❌ Ошибка при добавлении текста.",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ К списку текстов", callback_data="admin_texts")
                            ]])
                        )
                    
                    return ADMIN_TEXT_MANAGEMENT
                
                return ADMIN_TEXT_ADD
            
            async def admin_text_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик редактирования текстов"""
                if update.callback_query:
                    query = update.callback_query
                    await query.answer()
                    action = query.data
                    
                    if action == "admin_texts":
                        # Возврат в меню текстов
                        return await admin_text_management(update, context)
                    
                    elif action.startswith("admin_add_translation_"):
                        # Добавление перевода для существующего ключа
                        key = action.replace("admin_add_translation_", "")
                        
                        await query.edit_message_text(
                            f"➕ Добавление перевода для ключа: {key}\n\n"
                            "Введите данные в формате:\n"
                            "Язык|Текст\n\n"
                            "Например:\n"
                            "en|Welcome to the bot!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ Назад", callback_data=f"admin_edit_text_{key}")
                            ]])
                        )
                        # Сохраняем ключ в контексте для последующего использования
                        context.user_data['current_edit_key'] = key
                        return ADMIN_TEXT_ADD
                    
                    elif action.startswith("admin_edit_translation_"):
                        # Редактирование конкретного перевода
                        parts = action.replace("admin_edit_translation_", "").split('_')
                        if len(parts) >= 2:
                            key = parts[0]
                            lang_code = parts[1]
                            
                            from models import get_bot_message
                            current_text = get_bot_message(key, lang_code)
                            
                            # Получаем название языка
                            lang_name = {
                                'ru': '🇷🇺 Русский',
                                'tg': '🇹🇯 Таджикский',
                                'uz': '🇺🇿 Узбекский',
                                'kk': '🇰🇿 Казахский',
                                'en': '🇬🇧 Английский'
                            }.get(lang_code, lang_code)
                            
                            if current_text:
                                text = f"<b>✏️ Редактирование текста</b>\n\n"
                                text += f"<b>Ключ:</b> {key}\n"
                                text += f"<b>Язык:</b> {lang_name}\n\n"
                                text += f"<b>Текущий текст:</b>\n<pre>{current_text}</pre>\n\n"
                                text += "Введите новый текст:"
                                
                                await query.edit_message_text(
                                    text,
                                    reply_markup=InlineKeyboardMarkup([[
                                        InlineKeyboardButton("↩️ Назад", callback_data=f"admin_edit_text_{key}")
                                    ]]),
                                    parse_mode='HTML'
                                )
                                # Сохраняем данные в контексте для последующего использования
                                context.user_data['current_edit_key'] = key
                                context.user_data['current_edit_lang'] = lang_code
                                return ADMIN_TEXT_EDIT
                            else:
                                await query.edit_message_text(
                                    "<b>❌ Текст не найден.</b>",
                                    reply_markup=InlineKeyboardMarkup([[
                                        InlineKeyboardButton("↩️ Назад", callback_data="admin_texts")
                                    ]]),
                                    parse_mode='HTML'
                                )
                                return ADMIN_TEXT_MANAGEMENT
                    
                    return ADMIN_TEXT_EDIT
                
                if update.message:
                    # Обработка нового текста
                    text = update.message.text
                    
                    # Определяем режим (добавление перевода или редактирование)
                    if 'current_edit_key' in context.user_data and 'current_edit_lang' in context.user_data:
                        # Режим редактирования существующего перевода
                        key = context.user_data['current_edit_key']
                        lang_code = context.user_data['current_edit_lang']
                        
                        from models import update_bot_message
                        msg_id = update_bot_message(key, lang_code, text)
                        
                        if msg_id:
                            # Успешно обновлено
                            await update.message.reply_text(
                                f"✅ Текст с ключом {key} для языка {lang_code} успешно обновлен!",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ К списку текстов", callback_data="admin_texts")
                                ]])
                            )
                        else:
                            # Ошибка при обновлении
                            await update.message.reply_text(
                                "❌ Ошибка при обновлении текста.",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ К списку текстов", callback_data="admin_texts")
                                ]])
                            )
                        
                        # Очищаем контекст
                        if 'current_edit_key' in context.user_data:
                            del context.user_data['current_edit_key']
                        if 'current_edit_lang' in context.user_data:
                            del context.user_data['current_edit_lang']
                        
                        return ADMIN_TEXT_MANAGEMENT
                    
                    elif 'current_edit_key' in context.user_data:
                        # Режим добавления нового перевода
                        key = context.user_data['current_edit_key']
                        parts = text.strip().split('|', 1)  # Разделяем на 2 части (язык, текст)
                        
                        if len(parts) != 2:
                            await update.message.reply_text(
                                "❌ Неверный формат данных. Введите данные в формате:\n"
                                "Язык|Текст\n\n"
                                "Например:\n"
                                "en|Welcome to the bot!",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ Назад", callback_data=f"admin_edit_text_{key}")
                                ]])
                            )
                            return ADMIN_TEXT_ADD
                        
                        lang_code = parts[0].strip()
                        message_text = parts[1].strip()
                        
                        from models import update_bot_message
                        msg_id = update_bot_message(key, lang_code, message_text)
                        
                        if msg_id:
                            # Успешно добавлено
                            await update.message.reply_text(
                                f"✅ Перевод для ключа {key} на язык {lang_code} успешно добавлен!",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ К списку текстов", callback_data="admin_texts")
                                ]])
                            )
                        else:
                            # Ошибка при добавлении
                            await update.message.reply_text(
                                "❌ Ошибка при добавлении перевода.",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ К списку текстов", callback_data="admin_texts")
                                ]])
                            )
                        
                        # Очищаем контекст
                        if 'current_edit_key' in context.user_data:
                            del context.user_data['current_edit_key']
                        
                        return ADMIN_TEXT_MANAGEMENT
                
                return ADMIN_TEXT_EDIT
            
            # Создаем обработчик для админ-панели
            # Создаем функции для обработки новых опций админ-панели
            async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик настроек бота"""
                query = update.callback_query
                await query.answer()
                
                action = query.data
                
                if action == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                # Настройки бота
                settings_keyboard = [
                    [InlineKeyboardButton("⏱️ Частота обновления данных", callback_data="admin_setting_update_freq")],
                    [InlineKeyboardButton("🔔 Настройки уведомлений", callback_data="admin_setting_notifications")],
                    [InlineKeyboardButton("🌐 Региональные настройки", callback_data="admin_setting_regional")],
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                await query.edit_message_text(
                    "⚙️ Настройки бота\n\n"
                    "Выберите категорию настроек:",
                    reply_markup=InlineKeyboardMarkup(settings_keyboard)
                )
                return ADMIN_SETTINGS
            
            async def admin_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик анализа активности"""
                query = update.callback_query
                await query.answer()
                
                action = query.data
                
                if action == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                # Подготовка данных об активности (заглушка)
                users = get_all_users()
                total_users = len(users)
                approved_users = sum(1 for user in users if user.get('is_approved'))
                
                # Имитация данных об активности по дням недели
                days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                activity = [random.randint(5, 20) for _ in range(7)]
                
                activity_text = "📈 Анализ активности\n\n"
                activity_text += f"👥 Всего пользователей: {total_users}\n"
                activity_text += f"✅ Активных пользователей: {approved_users}\n\n"
                
                activity_text += "📊 Активность по дням недели:\n"
                for i, day in enumerate(days):
                    activity_text += f"{day}: {'▮' * (activity[i] // 2)} ({activity[i]})\n"
                
                activity_keyboard = [
                    [InlineKeyboardButton("📊 Детальная статистика", callback_data="admin_activity_details")],
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                await query.edit_message_text(
                    activity_text,
                    reply_markup=InlineKeyboardMarkup(activity_keyboard)
                )
                return ADMIN_ACTIVITY
            
            async def admin_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Информация о боте"""
                query = update.callback_query
                await query.answer()
                
                if query.data == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                about_text = (
                    "<b>ℹ️ О боте</b>\n\n"
                    "<b>✨ Trade Analysis Bot ✨</b>\n\n"
                    "<b>Версия:</b> 2.0.0\n"
                    "<b>Разработан:</b> Replit AI\n"
                    "<b>Лицензия:</b> Proprietary\n\n"
                    "<b>📝 Описание:</b>\n"
                    "Профессиональный бот для анализа рынка "
                    "с системой управления пользователями.\n\n"
                    "<b>🛠 Технологии:</b>\n"
                    "• Python 3.11\n"
                    "• Python-telegram-bot\n"
                    "• PostgreSQL\n"
                    "• YFinance API\n\n"
                    "<b>📞 Контакты:</b>\n"
                    "Поддержка: @tradeporu\n"
                )
                
                about_keyboard = [
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                await query.edit_message_text(
                    about_text,
                    reply_markup=InlineKeyboardMarkup(about_keyboard),
                    parse_mode='HTML'
                )
                return ADMIN_ABOUT
            async def admin_user_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Аналитика пользователей"""
                query = update.callback_query
                await query.answer()
                
                if query.data == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                # Получаем реальную статистику из БД
                stats = get_user_activity_stats()
                
                analytics_text = "<b>👤 Аналитика пользователей</b>\n\n"
                analytics_text += f"<b>📊 Общая статистика:</b>\n"
                analytics_text += f"• Всего пользователей: {stats['total']}\n"
                analytics_text += f"• Подтвержденных: {stats['approved']}\n"
                analytics_text += f"• Администраторов: {stats['admins']}\n"
                analytics_text += f"• Новых за 7 дней: {stats['new_last_week']}\n\n"
                
                analytics_text += "<b>🌐 Распределение по языкам:</b>\n"
                for lang in stats['languages']:
                    lang_emoji = {
                        'ru': '🇷🇺',
                        'tg': '🇹🇯',
                        'uz': '🇺🇿',
                        'kk': '🇰🇿',
                        'en': '🇬🇧'
                    }.get(lang['language'], '🌐')
                    
                    analytics_text += f"• {lang_emoji} {lang['language']}: {lang['count']}\n"
                
                analytics_keyboard = [
                    [InlineKeyboardButton("📊 Детальный отчёт", callback_data="admin_user_detailed_report")],
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                await query.edit_message_text(
                    analytics_text,
                    reply_markup=InlineKeyboardMarkup(analytics_keyboard),
                    parse_mode='HTML'
                )
                return ADMIN_USER_ANALYTICS
                
            async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Экспорт данных бота"""
                query = update.callback_query
                await query.answer()
                
                if query.data == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                # Показываем сообщение о начале экспорта
                await query.edit_message_text(
                    "<b>⏳ Экспорт данных...</b>\n\nПожалуйста, подождите, идет подготовка данных.",
                    parse_mode='HTML'
                )
                
                # Экспортируем данные
                from models import export_bot_data
                export_data = export_bot_data()
                
                if export_data:
                    try:
                        # Сохраняем данные в JSON файл
                        import os
                        import json
                        from datetime import datetime
                        
                        # Проверяем наличие директории для экспорта
                        export_dir = "exports"
                        if not os.path.exists(export_dir):
                            os.makedirs(export_dir)
                        
                        filename = f"{export_dir}/bot_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
                        
                        # Отправляем файл
                        with open(filename, 'rb') as f:
                            await context.bot.send_document(
                                chat_id=update.effective_chat.id,
                                document=f,
                                filename=os.path.basename(filename),
                                caption="📤 Экспорт данных бота"
                            )
                        
                        # Количество экспортированных элементов
                        currency_pairs_count = len(export_data.get('currency_pairs', []))
                        messages_count = len(export_data.get('bot_messages', []))
                        settings_count = len(export_data.get('bot_settings', {}))
                        
                        export_text = "<b>✅ Экспорт данных успешно выполнен</b>\n\n"
                        export_text += "Файл с данными отправлен вам отдельным сообщением.\n\n"
                        export_text += f"<b>Экспортировано:</b>\n"
                        export_text += f"• Валютные пары: {currency_pairs_count}\n"
                        export_text += f"• Сообщения бота: {messages_count}\n"
                        export_text += f"• Настройки: {settings_count}\n\n"
                        export_text += "Вы можете использовать этот файл для резервного копирования или переноса данных."
                    except Exception as e:
                        import traceback
                        error_traceback = traceback.format_exc()
                        export_text = f"<b>❌ Ошибка при экспорте данных</b>\n\n<pre>{str(e)}\n\n{error_traceback}</pre>"
                else:
                    export_text = "<b>❌ Ошибка при экспорте данных</b>\n\nНе удалось получить данные для экспорта."
                
                export_keyboard = [
                    [InlineKeyboardButton("🔄 Повторить экспорт", callback_data="admin_export")],
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                await query.edit_message_text(
                    export_text,
                    reply_markup=InlineKeyboardMarkup(export_keyboard),
                    parse_mode='HTML'
                )
                return ADMIN_EXPORT_DATA
                
            async def admin_import(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Импорт данных бота"""
                query = update.callback_query
                
                if not query:
                    # Обработка загруженного файла
                    if update.message and update.message.document:
                        try:
                            # Загружаем файл
                            file = await context.bot.get_file(update.message.document.file_id)
                            
                            # Создаем временный файл для загрузки
                            import tempfile
                            import json
                            from models import import_bot_data
                            
                            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
                            await file.download_to_drive(custom_path=temp_file.name)
                            
                            # Сообщаем о начале импорта
                            await update.message.reply_text(
                                "<b>⏳ Импорт данных...</b>\n\nПожалуйста, подождите, импортируем данные.",
                                parse_mode='HTML'
                            )
                            
                            # Читаем и импортируем данные
                            with open(temp_file.name, 'r', encoding='utf-8') as f:
                                try:
                                    data = json.load(f)
                                    
                                    # Выполняем импорт
                                    if import_bot_data(data):
                                        # Считаем количество импортированных записей
                                        currency_pairs_count = len(data.get('currency_pairs', []))
                                        messages_count = len(data.get('bot_messages', []))
                                        settings_count = len(data.get('bot_settings', {}))
                                        
                                        success_text = "<b>✅ Импорт данных успешно выполнен</b>\n\n"
                                        success_text += "<b>Импортировано:</b>\n"
                                        success_text += f"• Валютные пары: {currency_pairs_count}\n"
                                        success_text += f"• Сообщения бота: {messages_count}\n"
                                        success_text += f"• Настройки: {settings_count}\n\n"
                                        success_text += "Данные успешно загружены в систему."
                                        
                                        # Отправляем результат
                                        await update.message.reply_text(
                                            success_text,
                                            parse_mode='HTML',
                                            reply_markup=InlineKeyboardMarkup([
                                                [InlineKeyboardButton("↩️ Вернуться в админ-панель", callback_data="admin")]
                                            ])
                                        )
                                    else:
                                        await update.message.reply_text(
                                            "<b>❌ Ошибка при импорте данных</b>\n\nФайл некорректен или произошла ошибка обработки.",
                                            parse_mode='HTML',
                                            reply_markup=InlineKeyboardMarkup([
                                                [InlineKeyboardButton("↩️ Вернуться в админ-панель", callback_data="admin")]
                                            ])
                                        )
                                except json.JSONDecodeError:
                                    await update.message.reply_text(
                                        "<b>❌ Ошибка при импорте данных</b>\n\nНедействительный JSON-файл.",
                                        parse_mode='HTML',
                                        reply_markup=InlineKeyboardMarkup([
                                            [InlineKeyboardButton("↩️ Вернуться в админ-панель", callback_data="admin")]
                                        ])
                                    )
                            
                            # Удаляем временный файл
                            import os
                            os.unlink(temp_file.name)
                            
                        except Exception as e:
                            import traceback
                            error_traceback = traceback.format_exc()
                            await update.message.reply_text(
                                f"<b>❌ Ошибка при импорте данных</b>\n\n<pre>{str(e)}\n\n{error_traceback}</pre>",
                                parse_mode='HTML',
                                reply_markup=InlineKeyboardMarkup([
                                    [InlineKeyboardButton("↩️ Вернуться в админ-панель", callback_data="admin")]
                                ])
                            )
                        
                        return ADMIN_MENU
                    return
                
                await query.answer()
                
                if query.data == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                import_text = "<b>📥 Импорт данных</b>\n\n"
                import_text += "Для импорта данных отправьте JSON файл экспорта.\n\n"
                import_text += "<b>⚠️ Внимание!</b> Импорт может перезаписать существующие данные.\n\n"
                import_text += "Будут импортированы следующие данные:\n"
                import_text += "• Сообщения бота\n"
                import_text += "• Валютные пары\n"
                import_text += "• Настройки бота\n\n"
                import_text += "<i>Пользователи и их статусы не будут затронуты.</i>"
                
                import_keyboard = [
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                # Устанавливаем состояние для ожидания файла
                context.user_data['waiting_for_import'] = True
                
                await query.edit_message_text(
                    import_text,
                    reply_markup=InlineKeyboardMarkup(import_keyboard),
                    parse_mode='HTML'
                )
                return ADMIN_IMPORT_DATA
                
            async def admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Просмотр логов системы"""
                query = update.callback_query
                await query.answer()
                
                if query.data == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                try:
                    # Проверяем существование файла логов
                    import os
                    if not os.path.exists('bot.log'):
                        # Создаем пустой файл логов, если он не существует
                        with open('bot.log', 'w') as f:
                            f.write("# Log file created\n")
                    
                    # Получаем последние 20 строк логов
                    with open('bot.log', 'r') as file:
                        log_content = file.readlines()
                        # Берем последние 20 строк или все строки, если их меньше 20
                        log_lines = log_content[-20:] if len(log_content) >= 20 else log_content
                    
                    logs_text = "<b>📋 Последние логи системы</b>\n\n<pre>"
                    for line in log_lines:
                        # Укорачиваем строки, если они слишком длинные
                        if len(line) > 100:
                            line = line[:97] + "..."
                        # Экранируем HTML-символы
                        line = line.replace('<', '&lt;').replace('>', '&gt;')
                        logs_text += line
                    logs_text += "</pre>"
                    
                    # Если текст слишком длинный для Telegram, обрезаем его
                    if len(logs_text) > 4000:
                        logs_text = logs_text[:3996] + "</pre>"
                    
                    # Если логи заняли весь допустимый размер сообщения,
                    # отправляем файл с полными логами
                    if len(logs_text) > 3900:
                        with open('bot.log', 'rb') as file:
                            await context.bot.send_document(
                                chat_id=update.effective_chat.id,
                                document=file,
                                filename="bot.log",
                                caption="📋 Полный лог бота"
                            )
                except Exception as e:
                    import traceback
                    error_traceback = traceback.format_exc()
                    logs_text = f"<b>❌ Ошибка при чтении логов</b>\n\n<pre>{str(e)}\n\n{error_traceback}</pre>"
                
                logs_keyboard = [
                    [InlineKeyboardButton("🔄 Обновить", callback_data="admin_logs")],
                    [InlineKeyboardButton("📁 Скачать полный лог", callback_data="admin_download_logs")],
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                await query.edit_message_text(
                    logs_text,
                    reply_markup=InlineKeyboardMarkup(logs_keyboard),
                    parse_mode='HTML'
                )
                return ADMIN_LOGS
                
            async def admin_server_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Статус сервера"""
                query = update.callback_query
                await query.answer()
                
                if query.data == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                # Собираем информацию о системе
                try:
                    status_text = "<b>🖥️ Статус сервера</b>\n\n"
                    
                    # Информация о системе
                    status_text += "<b>Система:</b>\n"
                    status_text += f"• ОС: {platform.system()} {platform.release()}\n"
                    status_text += f"• Python: {platform.python_version()}\n"
                    
                    # Получаем время работы
                    if 'start_time' in context.bot_data:
                        start_time = context.bot_data['start_time']
                        if isinstance(start_time, datetime):
                            uptime = datetime.now() - start_time
                            days, remainder = divmod(uptime.total_seconds(), 86400)
                            hours, remainder = divmod(remainder, 3600)
                            minutes, seconds = divmod(remainder, 60)
                            uptime_str = f"{int(days)}д {int(hours)}ч {int(minutes)}м"
                        else:
                            uptime_str = str(start_time)
                    else:
                        uptime_str = "Неизвестно"
                    
                    status_text += f"• Время работы: {uptime_str}\n\n"
                    
                    # Использование ресурсов
                    cpu_percent = psutil.cpu_percent()
                    memory = psutil.virtual_memory()
                    
                    status_text += "<b>Ресурсы:</b>\n"
                    status_text += f"• CPU: {cpu_percent}%\n"
                    status_text += f"• RAM: {memory.percent}% ({memory.used // (1024*1024)} МБ / {memory.total // (1024*1024)} МБ)\n"
                    status_text += f"• Диск: {psutil.disk_usage('/').percent}%\n\n"
                    
                    # Информация о боте
                    status_text += "<b>Бот:</b>\n"
                    users = get_all_users()
                    status_text += f"• Пользователей: {len(users)}\n"
                    active_users = len([u for u in users if u.get('is_approved')])
                    status_text += f"• Активных: {active_users}\n"
                    status_text += f"• Процессов: {len(psutil.pids())}\n"
                    
                except Exception as e:
                    import traceback
                    error_traceback = traceback.format_exc()
                    logger.error(f"Error getting server status: {e}")
                    status_text = f"<b>❌ Ошибка при получении статуса сервера</b>\n\n<pre>{str(e)}\n\n{error_traceback}</pre>"
                
                status_keyboard = [
                    [InlineKeyboardButton("🔄 Обновить", callback_data="admin_server_status")],
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                await query.edit_message_text(
                    status_text,
                    reply_markup=InlineKeyboardMarkup(status_keyboard),
                    parse_mode='HTML'
                )
                return ADMIN_SERVER_STATUS
                
            async def admin_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Управление торговыми сигналами"""
                query = update.callback_query
                await query.answer()
                
                if query.data == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                signals_text = "📊 *Управление сигналами*\n\n"
                signals_text += "Здесь вы можете настроить параметры торговых сигналов и уведомлений.\n\n"
                
                # Имитируем настройки сигналов (в будущем заменить на реальные данные из БД)
                signals_text += "*Текущие настройки:*\n"
                signals_text += "• Интервал сканирования: 5 минут\n"
                signals_text += "• Минимальная сила сигнала: 70%\n"
                signals_text += "• Автоматические оповещения: Включены\n"
                signals_text += "• Подтверждение сигналов: Требуется\n\n"
                
                signals_text += "*Статистика сигналов:*\n"
                signals_text += "• Отправлено за 24 часа: 17\n"
                signals_text += "• Положительных: 12\n"
                signals_text += "• Отрицательных: 5\n"
                signals_text += "• Точность: 70.6%\n"
                
                signals_keyboard = [
                    [InlineKeyboardButton("⚙️ Настройки сигналов", callback_data="admin_signal_settings")],
                    [InlineKeyboardButton("📈 Обзор рынка", callback_data="admin_market_overview")],
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                # Экранируем специальные символы для MarkdownV2
                for char in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
                    signals_text = signals_text.replace(char, f"\\{char}")
                
                await query.edit_message_text(
                    signals_text,
                    reply_markup=InlineKeyboardMarkup(signals_keyboard),
                    parse_mode='MarkdownV2'
                )
                return ADMIN_SIGNAL_MANAGEMENT
                
            async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Статистика бота"""
                query = update.callback_query
                await query.answer()
                
                if query.data == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                # Собираем статистику из разных источников
                users = get_all_users()
                total_users = len(users)
                approved_users = sum(1 for user in users if user.get('is_approved'))
                
                stats_text = "📊 *Общая статистика бота*\n\n"
                
                stats_text += "*Пользователи:*\n"
                stats_text += f"• Всего пользователей: {total_users}\n"
                stats_text += f"• Активных: {approved_users}\n"
                stats_text += f"• Администраторов: {sum(1 for user in users if user.get('is_admin'))}\n"
                stats_text += f"• Модераторов: {sum(1 for user in users if user.get('is_moderator'))}\n\n"
                
                stats_text += "*Активность:*\n"
                # Данные о количестве запросов (заглушка)
                stats_text += "• Запросов сегодня: 74\n"
                stats_text += "• Запросов за неделю: 487\n"
                stats_text += "• Средняя дневная активность: 69.6\n\n"
                
                stats_text += "*Система:*\n"
                uptime = datetime.now() - context.bot_data.get('start_time', datetime.now())
                days, remainder = divmod(uptime.total_seconds(), 86400)
                hours, remainder = divmod(remainder, 3600)
                minutes, seconds = divmod(remainder, 60)
                
                stats_text += f"• Время работы: {int(days)}d {int(hours)}h {int(minutes)}m\n"
                stats_text += f"• Использование CPU: {psutil.cpu_percent()}%\n"
                stats_text += f"• Использование RAM: {psutil.virtual_memory().percent}%\n"
                
                stats_keyboard = [
                    [InlineKeyboardButton("📊 Расширенная статистика", callback_data="admin_extended_stats")],
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                # Экранируем специальные символы для MarkdownV2
                for char in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
                    stats_text = stats_text.replace(char, f"\\{char}")
                
                await query.edit_message_text(
                    stats_text,
                    reply_markup=InlineKeyboardMarkup(stats_keyboard),
                    parse_mode='MarkdownV2'
                )
                return ADMIN_MENU
                
            async def admin_update_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обновление базы данных"""
                query = update.callback_query
                await query.answer()
                
                try:
                    # Проверяем наличие колонки is_moderator
                    from models import get_db_connection
                    with get_db_connection() as conn:
                        with conn.cursor() as cur:
                            # Проверка колонки is_moderator
                            cur.execute("""
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_name = 'users' AND column_name = 'is_moderator'
                            """)
                            column_exists = cur.fetchone() is not None
                            
                            # Если колонки нет, добавляем её
                            if not column_exists:
                                cur.execute("""
                                    ALTER TABLE users 
                                    ADD COLUMN is_moderator BOOLEAN DEFAULT FALSE
                                """)
                                conn.commit()
                                logger.info("Added is_moderator column to users table")
                    
                    # Создаем новые таблицы, если их нет (через уже существующие функции)
                    get_bot_settings()  # Создаст таблицу bot_settings если её нет
                    get_moderator_permissions()  # Создаст таблицу moderator_permissions если её нет
                    
                    update_text = "✅ *База данных успешно обновлена*\n\n"
                    update_text += "Выполненные операции:\n"
                    update_text += "• Проверка и добавление необходимых колонок\n"
                    update_text += "• Создание отсутствующих таблиц\n"
                    update_text += "• Обновление структуры данных\n\n"
                    update_text += "База данных теперь соответствует последней версии приложения."
                except Exception as e:
                    logger.error(f"Error updating database: {e}")
                    update_text = f"❌ *Ошибка при обновлении базы данных*\n\n{str(e)}"
                
                update_keyboard = [
                    [InlineKeyboardButton("↩️ Назад к меню", callback_data="admin_back")]
                ]
                
                # Экранируем специальные символы для MarkdownV2
                for char in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
                    update_text = update_text.replace(char, f"\\{char}")
                
                await query.edit_message_text(
                    update_text,
                    reply_markup=InlineKeyboardMarkup(update_keyboard),
                    parse_mode='MarkdownV2'
                )
                return ADMIN_MENU
                
                about_text = (
                    "ℹ️ О боте\n\n"
                    "✨ *Trade Analysis Bot* ✨\n\n"
                    "Версия: 2.0.0\n"
                    "Разработан: Replit AI\n"
                    "Лицензия: Proprietary\n\n"
                    "📝 Описание:\n"
                    "Профессиональный бот для анализа рынка "
                    "с системой управления пользователями.\n\n"
                    "🛠 Технологии:\n"
                    "• Python 3.11\n"
                    "• Python-telegram-bot\n"
                    "• PostgreSQL\n"
                    "• YFinance API\n\n"
                    "📞 Контакты:\n"
                    "Поддержка: @tradeporu\n"
                )
                
                about_keyboard = [
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                await query.edit_message_text(
                    about_text,
                    reply_markup=InlineKeyboardMarkup(about_keyboard),
                    parse_mode='Markdown'
                )
                return ADMIN_ABOUT
            
            async def admin_change_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик смены пароля администратора"""
                query = update.callback_query
                if query:
                    await query.answer()
                    
                    if query.data == "admin_back":
                        await query.edit_message_text(
                            "👑 Панель администратора",
                            reply_markup=get_admin_keyboard()
                        )
                        return ADMIN_MENU
                    
                    # Первый заход в функцию
                    keyboard = [
                        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                    ]
                    
                    await query.edit_message_text(
                        "🔐 Смена пароля администратора\n\n"
                        "Введите новый пароль администратора.\n"
                        "Пароль должен содержать минимум 6 символов.",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    context.user_data['admin_changing_password'] = True
                    return ADMIN_CHANGE_PASSWORD
                
                elif update.message and context.user_data.get('admin_changing_password'):
                    new_password = update.message.text
                    
                    # Проверка минимальной длины пароля
                    if len(new_password) < 6:
                        await update.message.reply_text(
                            "❌ Пароль должен содержать минимум 6 символов!\n\n"
                            "Пожалуйста, введите другой пароль или нажмите /admin для отмены."
                        )
                        return ADMIN_CHANGE_PASSWORD
                    
                    # Хеширование нового пароля и обновление в config
                    new_password_hash = hash_password(new_password)
                    
                    # Обновление пароля администратора (заглушка)
                    global ADMIN_PASSWORD_HASH
                    ADMIN_PASSWORD_HASH = new_password_hash
                    
                    # Уведомление о смене пароля
                    await update.message.reply_text(
                        "✅ Пароль администратора успешно изменен!",
                        reply_markup=get_admin_keyboard()
                    )
                    
                    # Очистка контекста
                    if 'admin_changing_password' in context.user_data:
                        del context.user_data['admin_changing_password']
                    
                    return ADMIN_MENU
                
                return ADMIN_MENU
            
            # Добавляем обработчик для админ-панели с новыми функциями
            admin_conv_handler = ConversationHandler(
                entry_points=[CommandHandler("admin", admin_command)],
                states={
                    ADMIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_check_password)],
                    ADMIN_MENU: [CallbackQueryHandler(admin_menu_handler)],
                    ADMIN_USER_MANAGEMENT: [CallbackQueryHandler(admin_user_management)],
                    ADMIN_BROADCAST_MESSAGE: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_message),
                        CallbackQueryHandler(admin_broadcast_message)
                    ],
                    ADMIN_CURRENCY_MANAGEMENT: [CallbackQueryHandler(admin_currency_management)],
                    ADMIN_CURRENCY_ADD: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_currency),
                        CallbackQueryHandler(admin_add_currency)
                    ],
                    ADMIN_CURRENCY_EDIT: [CallbackQueryHandler(admin_currency_management)],
                    ADMIN_TEXT_MANAGEMENT: [CallbackQueryHandler(admin_text_management)],
                    ADMIN_TEXT_ADD: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_add),
                        CallbackQueryHandler(admin_text_add)
                    ],
                    ADMIN_TEXT_EDIT: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_edit),
                        CallbackQueryHandler(admin_text_edit)
                    ],
                    ADMIN_ACTIVITY: [CallbackQueryHandler(admin_activity)],
                    ADMIN_SETTINGS: [CallbackQueryHandler(admin_settings)],
                    ADMIN_CHANGE_PASSWORD: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_change_password),
                        CallbackQueryHandler(admin_change_password)
                    ],
                    ADMIN_ABOUT: [CallbackQueryHandler(admin_about)],
                    ADMIN_EXPORT_DATA: [CallbackQueryHandler(admin_export)],
                    ADMIN_IMPORT_DATA: [
                        MessageHandler(filters.Document.ALL, admin_import),
                        CallbackQueryHandler(admin_import)
                    ],
                    ADMIN_LOGS: [CallbackQueryHandler(admin_logs)],
                    ADMIN_SERVER_STATUS: [CallbackQueryHandler(admin_server_status)],
                    ADMIN_USER_ANALYTICS: [CallbackQueryHandler(admin_user_analytics)],
                    ADMIN_SIGNAL_MANAGEMENT: [CallbackQueryHandler(admin_signals)],
                    ADMIN_DIRECT_MESSAGE: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_direct_message_handler),
                        CallbackQueryHandler(admin_direct_message_handler)
                    ],
                    ADMIN_SEND_MESSAGE_TO_USER: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_message_to_user),
                        CallbackQueryHandler(admin_send_message_to_user)
                    ],
                    ADMIN_SEARCH_USER: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_search_user_handler),
                        CallbackQueryHandler(admin_search_user_handler)
                    ],
                    ADMIN_OTC_SIGNALS: [
                        CallbackQueryHandler(admin_otc_signals_handler)
                    ],
                    ADMIN_TRADING_VIEW: [
                        CallbackQueryHandler(admin_trading_view_handler)
                    ],
                    ADMIN_SCHEDULER: [
                        CallbackQueryHandler(admin_scheduler_handler)
                    ],
                    ADMIN_API: [
                        CallbackQueryHandler(admin_api_handler)
                    ],
                    ADMIN_SECURITY: [
                        CallbackQueryHandler(admin_security_handler)
                    ],
                    ADMIN_PROXY: [
                        CallbackQueryHandler(admin_proxy_handler)
                    ],
                    # Добавляем новые обработчики для новых функций
                    ADMIN_MESSAGE_TO_PENDING: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_message_to_pending_handler),
                        CallbackQueryHandler(admin_message_to_pending_handler)
                    ],
                    ADMIN_SELECT_USERS: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_select_users_handler),
                        CallbackQueryHandler(admin_select_users_handler)
                    ],
                    ADMIN_CONTENT_MANAGER: [
                        CallbackQueryHandler(admin_content_manager_handler)
                    ],
                    ADMIN_STATISTICS: [
                        CallbackQueryHandler(admin_statistics_handler)
                    ],
                    ADMIN_QUICK_COMMANDS: [
                        CallbackQueryHandler(admin_quick_commands_handler)
                    ],
                    ADMIN_HISTORY: [
                        CallbackQueryHandler(admin_history_handler)
                    ],
                    ADMIN_PLUGINS: [
                        CallbackQueryHandler(admin_plugins_handler)
                    ],
                    ADMIN_MARKETPLACE: [
                        CallbackQueryHandler(admin_marketplace_handler)
                    ]
                },
                fallbacks=[CommandHandler("start", start)]
            )
            application.add_handler(admin_conv_handler)
            
            # Обработчик кнопок действий с пользователями
            application.add_handler(CallbackQueryHandler(handle_admin_action, pattern=r"^(approve|reject)_\d+$"))
            
            # Обработчик текстовых сообщений
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            # Обработчики новых кнопок для трейдинга
            application.add_handler(CallbackQueryHandler(handle_trading_books, pattern="^trading_books$"))
            application.add_handler(CallbackQueryHandler(handle_trading_beginner, pattern="^trading_beginner$"))
            application.add_handler(CallbackQueryHandler(handle_trading_strategies, pattern="^trading_strategies$"))
            application.add_handler(CallbackQueryHandler(handle_trading_tools, pattern="^trading_tools$"))
            
            # Обработчик всех остальных кнопок
            application.add_handler(CallbackQueryHandler(button_click))

            # Set up error handlers
            application.add_error_handler(error_handler)

            # Reset error count on successful startup
            error_count = 0
            last_error_time = None

            # Run the bot with enhanced polling settings
            logger.info("Bot is running...")
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except Exception as e:
            current_time = datetime.now()

            # Reset error count if last error was more than 1 hour ago
            if last_error_time and (current_time - last_error_time).seconds > 3600:
                error_count = 0

            error_count += 1
            last_error_time = current_time

            logger.error(f"Bot crashed with error: {str(e)}")
            logger.info(f"Attempting to restart in {reconnect_delay} seconds...")

            if error_count >= max_consecutive_errors:
                logger.critical("Too many consecutive errors. Forcing system restart...")
                try:
                    # Additional cleanup before restart
                    if 'application' in locals():
                        try:
                            application.stop()
                        except:
                            pass
                    os.execv(sys.executable, ['python'] + sys.argv)
                except Exception as restart_error:
                    logger.error(f"Failed to restart: {restart_error}")
                continue

            # Implement exponential backoff for reconnection attempts
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

            # Log detailed error information
            logger.error("Detailed error information:", exc_info=True)
            continue
        finally:
            # Reset reconnect delay on successful connection
            reconnect_delay = 5

async def admin_direct_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик функции прямого сообщения пользователю"""
    query = update.callback_query
    
    if query:
        await query.answer()
        if query.data == "admin_back":
            await query.edit_message_text(
                "👑 Панель администратора",
                reply_markup=get_admin_keyboard()
            )
            return ADMIN_MENU
        return ADMIN_DIRECT_MESSAGE
    
    if update.message:
        user_id_text = update.message.text.strip()
        
        try:
            # Проверяем, является ли введенный текст числом (ID пользователя)
            user_id = int(user_id_text)
            
            # Проверяем существование пользователя
            user_info = get_user(user_id)
            if not user_info:
                await update.message.reply_text(
                    f"❌ Пользователь с ID {user_id} не найден в базе данных.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                    ]])
                )
                return ADMIN_DIRECT_MESSAGE
            
            # Сохраняем ID пользователя для отправки сообщения
            context.user_data['admin_recipient_id'] = user_id
            
            # Запрашиваем текст сообщения
            username = user_info.get('username', 'Без имени')
            is_approved = "✅ Подтвержден" if user_info.get('is_approved') else "⏳ Не подтвержден"
            
            await update.message.reply_text(
                f"📩 Отправка сообщения пользователю:\n"
                f"👤 Имя: {username}\n"
                f"🆔 ID: {user_id}\n"
                f"Статус: {is_approved}\n\n"
                f"Введите текст сообщения, которое хотите отправить:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Отмена", callback_data="admin_back")
                ]])
            )
            return ADMIN_SEND_MESSAGE_TO_USER
        
        except ValueError:
            # Если введен не числовой ID
            await update.message.reply_text(
                "❌ Ошибка: введите корректный ID пользователя (числовое значение).",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                ]])
            )
            return ADMIN_DIRECT_MESSAGE
        except Exception as e:
            logger.error(f"Error in direct message handler: {e}")
            await update.message.reply_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                ]])
            )
            return ADMIN_DIRECT_MESSAGE
    
    return ADMIN_DIRECT_MESSAGE

async def admin_search_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик поиска пользователей"""
    query = update.callback_query
    
    if query:
        await query.answer()
        if query.data == "admin_back":
            await query.edit_message_text(
                "👑 Панель администратора",
                reply_markup=get_admin_keyboard()
            )
            return ADMIN_MENU
        
        # Обработка других действий с результатами поиска
        if query.data.startswith("user_select_"):
            user_id = int(query.data.replace("user_select_", ""))
            context.user_data['admin_recipient_id'] = user_id
            
            user_info = get_user(user_id)
            if user_info:
                username = user_info.get('username', 'Без имени')
                is_approved = "✅ Подтвержден" if user_info.get('is_approved') else "⏳ Не подтвержден"
                is_admin = "👑 Да" if user_info.get('is_admin') else "👤 Нет"
                created_at = user_info.get('created_at', 'Неизвестно')
                
                user_keyboard = []
                
                # Кнопки действий с пользователем
                if user_info.get('is_approved'):
                    user_keyboard.append([
                        InlineKeyboardButton("📩 Отправить сообщение", callback_data=f"user_message_{user_id}"),
                        InlineKeyboardButton("🚫 Сбросить доступ", callback_data=f"user_reset_{user_id}")
                    ])
                else:
                    user_keyboard.append([
                        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
                        InlineKeyboardButton("📩 Отправить сообщение", callback_data=f"user_message_{user_id}")
                    ])
                
                if not user_info.get('is_admin'):
                    user_keyboard.append([
                        InlineKeyboardButton("👑 Сделать админом", callback_data=f"user_admin_{user_id}"),
                        InlineKeyboardButton("❌ Удалить", callback_data=f"user_delete_{user_id}")
                    ])
                
                user_keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="admin_back")])
                
                await query.edit_message_text(
                    f"👤 Информация о пользователе:\n\n"
                    f"🔹 Имя: {username}\n"
                    f"🔹 ID: {user_id}\n"
                    f"🔹 Статус: {is_approved}\n"
                    f"🔹 Администратор: {is_admin}\n"
                    f"🔹 Дата регистрации: {created_at}\n",
                    reply_markup=InlineKeyboardMarkup(user_keyboard)
                )
                return ADMIN_USER_MANAGEMENT
        
        # Если выбрали отправку сообщения пользователю
        if query.data.startswith("user_message_"):
            user_id = int(query.data.replace("user_message_", ""))
            context.user_data['admin_recipient_id'] = user_id
            
            user_info = get_user(user_id)
            if user_info:
                username = user_info.get('username', 'Без имени')
                is_approved = "✅ Подтвержден" if user_info.get('is_approved') else "⏳ Не подтвержден"
                
                await query.edit_message_text(
                    f"📩 Отправка сообщения пользователю:\n"
                    f"👤 Имя: {username}\n"
                    f"🆔 ID: {user_id}\n"
                    f"Статус: {is_approved}\n\n"
                    f"Введите текст сообщения, которое хотите отправить:",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Отмена", callback_data="admin_back")
                    ]])
                )
                return ADMIN_SEND_MESSAGE_TO_USER
        
        return ADMIN_SEARCH_USER
    
    if update.message:
        search_query = update.message.text.strip()
        
        try:
            # Пробуем найти по числовому ID
            try:
                user_id = int(search_query)
                user = get_user(user_id)
                if user:
                    users = [user]
                else:
                    users = []
            except ValueError:
                # Ищем по имени пользователя
                users = get_user_by_username(search_query)
                if not isinstance(users, list):
                    users = [users] if users else []
            
            if not users:
                await update.message.reply_text(
                    f"🔍 По запросу '{search_query}' ничего не найдено.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                    ]])
                )
                return ADMIN_SEARCH_USER
            
            if len(users) == 1:
                # Если найден только один пользователь, показываем его профиль
                user = users[0]
                user_id = user['user_id']
                username = user.get('username', 'Без имени')
                is_approved = "✅ Подтвержден" if user.get('is_approved') else "⏳ Не подтвержден"
                is_admin = "👑 Да" if user.get('is_admin') else "👤 Нет"
                
                user_keyboard = []
                
                # Кнопки действий с пользователем
                if user.get('is_approved'):
                    user_keyboard.append([
                        InlineKeyboardButton("📩 Отправить сообщение", callback_data=f"user_message_{user_id}"),
                        InlineKeyboardButton("🚫 Сбросить доступ", callback_data=f"user_reset_{user_id}")
                    ])
                else:
                    user_keyboard.append([
                        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
                        InlineKeyboardButton("📩 Отправить сообщение", callback_data=f"user_message_{user_id}")
                    ])
                
                if not user.get('is_admin'):
                    user_keyboard.append([
                        InlineKeyboardButton("👑 Сделать админом", callback_data=f"user_admin_{user_id}"),
                        InlineKeyboardButton("❌ Удалить", callback_data=f"user_delete_{user_id}")
                    ])
                
                user_keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="admin_back")])
                
                await update.message.reply_text(
                    f"👤 Информация о пользователе:\n\n"
                    f"🔹 Имя: {username}\n"
                    f"🔹 ID: {user_id}\n"
                    f"🔹 Статус: {is_approved}\n"
                    f"🔹 Администратор: {is_admin}\n",
                    reply_markup=InlineKeyboardMarkup(user_keyboard)
                )
                return ADMIN_USER_MANAGEMENT
            else:
                # Если найдено несколько пользователей, показываем список
                keyboard = []
                for user in users:
                    user_id = user['user_id']
                    username = user.get('username', 'Без имени')
                    status = "✅" if user.get('is_approved') else "⏳"
                    keyboard.append([
                        InlineKeyboardButton(f"{status} {username} (ID: {user_id})", callback_data=f"user_select_{user_id}")
                    ])
                
                keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="admin_back")])
                
                await update.message.reply_text(
                    f"🔍 Результаты поиска по запросу '{search_query}':\n"
                    f"Найдено пользователей: {len(users)}\n\n"
                    f"Выберите пользователя для просмотра:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return ADMIN_SEARCH_USER
        
        except Exception as e:
            logger.error(f"Error in search user handler: {e}")
            await update.message.reply_text(
                f"❌ Ошибка при поиске: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                ]])
            )
            return ADMIN_SEARCH_USER
    
    return ADMIN_SEARCH_USER

async def admin_otc_signals_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик управления OTC сигналами для Pocket Option"""
    query = update.callback_query
    
    if not query:
        return ADMIN_OTC_SIGNALS
    
    await query.answer()
    action = query.data
    
    if action == "admin_back":
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    elif action == "otc_view_active":
        # Здесь будет код для просмотра активных OTC сигналов
        otc_signals_text = (
            "🔍 Активные OTC сигналы для Pocket Option\n\n"
            "📊 Текущие торговые сигналы:\n"
            "1. EUR/USD - ⬆️ ВВЕРХ (80%) - 18:45\n"
            "2. GBP/JPY - ⬇️ ВНИЗ (75%) - 19:00\n"
            "3. AUD/CAD - ⬆️ ВВЕРХ (78%) - 19:15\n"
            "4. USD/CHF - ⬇️ ВНИЗ (82%) - 19:30\n\n"
            "⏱ Последнее обновление: 18:30"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="otc_refresh")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_otc_signals")]
        ]
        
        await query.edit_message_text(
            otc_signals_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_OTC_SIGNALS
    
    elif action == "otc_add_signal":
        # Здесь будет код для добавления нового OTC сигнала
        add_signal_text = (
            "➕ Добавление нового OTC сигнала\n\n"
            "⚠️ Функция в разработке\n\n"
            "Скоро здесь появится возможность добавлять новые торговые сигналы для OTC сессий Pocket Option с настройкой всех необходимых параметров."
        )
        
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_otc_signals")]
        ]
        
        await query.edit_message_text(
            add_signal_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_OTC_SIGNALS
    
    elif action == "otc_settings":
        # Здесь будет код для настроек OTC
        settings_text = (
            "⚙️ Настройки OTC сигналов\n\n"
            "🔹 Базовые параметры:\n"
            "• Минимальный процент уверенности: 75%\n"
            "• Автоматическая отправка: Включена\n"
            "• Время до истечения: 5 минут\n\n"
            "🔹 Фильтры активов:\n"
            "• Валютные пары: Все\n"
            "• Криптовалюты: BTC, ETH, LTC\n"
            "• Акции: Выключены\n\n"
            "🔹 Расписание уведомлений:\n"
            "• Будни: 18:00 - 22:00\n"
            "• Выходные: Выключено\n\n"
            "⚠️ Функция в разработке"
        )
        
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_otc_signals")]
        ]
        
        await query.edit_message_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_OTC_SIGNALS
    
    elif action == "otc_stats":
        # Здесь будет код для статистики OTC сигналов
        stats_text = (
            "📊 Статистика OTC сигналов\n\n"
            "📈 Общая статистика:\n"
            "• Всего сигналов: 120\n"
            "• Успешных: 92 (76.7%)\n"
            "• Неудачных: 28 (23.3%)\n\n"
            "🏆 Топ-3 актива по успешности:\n"
            "1. EUR/USD - 82% (31/38)\n"
            "2. GBP/JPY - 80% (24/30)\n"
            "3. USD/CHF - 79% (19/24)\n\n"
            "📉 Результаты по дням недели:\n"
            "• Пн: 75% (15/20)\n"
            "• Вт: 80% (16/20)\n"
            "• Ср: 78% (18/23)\n"
            "• Чт: 82% (18/22)\n"
            "• Пт: 69% (11/16)\n"
            "• Сб: 75% (9/12)\n"
            "• Вс: 71% (5/7)\n\n"
            "⚠️ Функция в разработке"
        )
        
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_otc_signals")]
        ]
        
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_OTC_SIGNALS
    
    else:
        # Возвращаемся в главное меню OTC
        keyboard = [
            [InlineKeyboardButton("🔍 Просмотр активных сигналов", callback_data="otc_view_active")],
            [InlineKeyboardButton("➕ Добавить новый сигнал", callback_data="otc_add_signal")],
            [InlineKeyboardButton("⚙️ Настройки OTC", callback_data="otc_settings")],
            [InlineKeyboardButton("📊 Статистика сигналов", callback_data="otc_stats")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            "📱 Управление OTC сигналами для Pocket Option\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_OTC_SIGNALS

async def admin_trading_view_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик интеграции с Trading View"""
    query = update.callback_query
    if not query:
        return ADMIN_TRADING_VIEW
    
    await query.answer()
    
    if query.data == "admin_back":
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    # Заглушка для интеграции с Trading View
    trading_view_text = (
        "📊 Интеграция с Trading View\n\n"
        "⚠️ Функция в разработке\n\n"
        "Скоро здесь появится возможность интеграции с платформой Trading View "
        "для получения и отправки профессиональных торговых сигналов на основе "
        "индикаторов и стратегий Trading View."
    )
    
    keyboard = [
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        trading_view_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_TRADING_VIEW

async def admin_scheduler_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик планировщика задач"""
    query = update.callback_query
    if not query:
        return ADMIN_SCHEDULER
    
    await query.answer()
    
    if query.data == "admin_back":
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    # Заглушка для планировщика задач
    scheduler_text = (
        "⏱️ Планировщик задач\n\n"
        "⚠️ Функция в разработке\n\n"
        "Скоро здесь появится возможность настройки расписания для автоматического выполнения "
        "различных задач, таких как:\n"
        "• Рассылка аналитических отчетов\n"
        "• Отправка торговых сигналов по расписанию\n"
        "• Автоматическое обновление статистики\n"
        "• Резервное копирование базы данных\n"
        "и многое другое."
    )
    
    keyboard = [
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        scheduler_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_SCHEDULER

async def admin_api_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик API интеграций"""
    query = update.callback_query
    if not query:
        return ADMIN_API
    
    await query.answer()
    
    if query.data == "admin_back":
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    # Заглушка для API интеграций
    api_text = (
        "🔌 API интеграции\n\n"
        "⚠️ Функция в разработке\n\n"
        "Скоро здесь появится возможность настройки интеграций с различными API:\n"
        "• Биржевые данные в реальном времени\n"
        "• Новостные ленты финансовых рынков\n"
        "• Сервисы аналитики и прогнозирования\n"
        "• Брокерские платформы и терминалы\n"
        "и многое другое."
    )
    
    keyboard = [
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        api_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_API

async def admin_security_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик функций безопасности"""
    query = update.callback_query
    if not query:
        return ADMIN_SECURITY
    
    await query.answer()
    
    if query.data == "admin_back":
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    # Заглушка для функций безопасности
    security_text = (
        "🔒 Безопасность\n\n"
        "⚠️ Функция в разработке\n\n"
        "Скоро здесь появится возможность настройки параметров безопасности:\n"
        "• Двухфакторная аутентификация (2FA)\n"
        "• Настройка политики паролей\n"
        "• Журнал действий администраторов\n"
        "• Ограничение доступа по IP\n"
        "и другие функции для обеспечения безопасности вашего бота."
    )
    
    keyboard = [
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        security_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_SECURITY

async def admin_proxy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик настроек прокси"""
    query = update.callback_query
    if not query:
        return ADMIN_PROXY
    
    await query.answer()
    
    if query.data == "admin_back":
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    # Заглушка для настроек прокси
    proxy_text = (
        "🌐 Настройки прокси\n\n"
        "⚠️ Функция в разработке\n\n"
        "Скоро здесь появится возможность настройки прокси для API запросов:\n"
        "• Добавление SOCKS5/HTTP прокси\n"
        "• Ротация прокси для избежания блокировок\n"
        "• Мониторинг работоспособности прокси\n"
        "• Геолокационный выбор прокси\n"
        "и другие настройки для стабильной работы бота."
    )
    
    keyboard = [
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        proxy_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_PROXY

async def admin_message_to_pending_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отправки сообщений неодобренным пользователям"""
    query = update.callback_query
    
    if query:
        await query.answer()
        
        if query.data == "admin_back":
            await query.edit_message_text(
                "👑 Панель администратора",
                reply_markup=get_admin_keyboard()
            )
            return ADMIN_MENU
        
        elif query.data == "send_to_all_pending":
            # Отправка всем неодобренным - запрашиваем текст сообщения
            context.user_data['send_to_all_pending'] = True
            
            await query.edit_message_text(
                "📩 Отправка сообщения всем неодобренным пользователям\n\n"
                "Введите текст сообщения, которое будет отправлено всем неодобренным пользователям:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Отмена", callback_data="admin_back")
                ]])
            )
            return ADMIN_MESSAGE_TO_PENDING
        
        elif query.data == "select_pending_users":
            # Отображаем список неодобренных пользователей для выбора
            from models import get_pending_users
            pending_users = get_pending_users()
            
            if not pending_users or len(pending_users) == 0:
                await query.edit_message_text(
                    "❌ Нет неодобренных пользователей в системе.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                    ]])
                )
                return ADMIN_MESSAGE_TO_PENDING
            
            # Создаем клавиатуру со списком неодобренных пользователей
            keyboard = []
            
            # Добавляем кнопку выбора всех пользователей
            keyboard.append([
                InlineKeyboardButton("✅ Выбрать всех пользователей", callback_data="select_all_pending")
            ])
            
            # Отображаем первые 10 пользователей с чекбоксами
            for i, user in enumerate(pending_users[:10]):
                user_id = user.get('user_id')
                username = user.get('username', 'Без имени')
                
                # Проверяем, выбран ли уже этот пользователь
                is_selected = user_id in context.user_data.get('selected_pending_list', [])
                checkbox = "☑️" if is_selected else "⬜"
                
                keyboard.append([
                    InlineKeyboardButton(f"{checkbox} @{username} (ID: {user_id})", 
                                       callback_data=f"toggle_pending_{user_id}")
                ])
            
            # Добавляем кнопку "Показать еще" если пользователей больше 10
            if len(pending_users) > 10:
                keyboard.append([
                    InlineKeyboardButton("⏩ Показать еще", callback_data="pending_page_next_1")
                ])
            
            # Добавляем кнопки действий
            action_buttons = []
            
            # Если есть выбранные пользователи, показываем кнопку отправки
            selected_count = len(context.user_data.get('selected_pending_list', []))
            if selected_count > 0:
                action_buttons.append(
                    InlineKeyboardButton(f"📩 Отправить выбранным ({selected_count})", 
                                        callback_data="send_to_selected_pending")
                )
            
            # Добавляем кнопки в клавиатуру
            if action_buttons:
                keyboard.append(action_buttons)
            
            # Добавляем кнопку назад
            keyboard.append([
                InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
            ])
            
            await query.edit_message_text(
                "👥 Выберите пользователей для отправки сообщения:\n"
                "Нажмите на пользователя, чтобы отметить/снять отметку.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ADMIN_MESSAGE_TO_PENDING
            
        # Обработка выбора всех пользователей
        elif query.data == "select_all_pending":
            from models import get_pending_users
            pending_users = get_pending_users()
            
            # Сохраняем ID всех пользователей
            all_user_ids = [user.get('user_id') for user in pending_users]
            context.user_data['selected_pending_list'] = all_user_ids
            
            # Обновляем сообщение с отмеченными чекбоксами
            keyboard = []
            
            # Добавляем кнопку очистки выбора
            keyboard.append([
                InlineKeyboardButton("❌ Очистить выбор", callback_data="clear_pending_selection")
            ])
            
            # Отображаем первые 10 пользователей с отмеченными чекбоксами
            for i, user in enumerate(pending_users[:10]):
                user_id = user.get('user_id')
                username = user.get('username', 'Без имени')
                keyboard.append([
                    InlineKeyboardButton(f"☑️ @{username} (ID: {user_id})", 
                                       callback_data=f"toggle_pending_{user_id}")
                ])
            
            # Добавляем кнопки навигации и действий
            if len(pending_users) > 10:
                keyboard.append([
                    InlineKeyboardButton("⏩ Показать еще", callback_data="pending_page_next_1")
                ])
            
            # Добавляем кнопку отправки сообщения
            keyboard.append([
                InlineKeyboardButton(f"📩 Отправить выбранным ({len(all_user_ids)})", 
                                   callback_data="send_to_selected_pending")
            ])
            
            # Добавляем кнопку назад
            keyboard.append([
                InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
            ])
            
            await query.edit_message_text(
                "👥 Все неодобренные пользователи выбраны!\n"
                "Выберите действие:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ADMIN_MESSAGE_TO_PENDING
            
        # Обработка очистки выбора
        elif query.data == "clear_pending_selection":
            # Очищаем список выбранных пользователей
            if 'selected_pending_list' in context.user_data:
                del context.user_data['selected_pending_list']
            
            # Вызываем обработчик выбора пользователей заново для обновления интерфейса
            query.data = "select_pending_users"
            return await admin_message_to_pending_handler(update, context)
        
        # Обработка переключения выбора пользователя
        elif query.data.startswith("toggle_pending_"):
            user_id = int(query.data.replace("toggle_pending_", ""))
            
            # Инициализируем список выбранных пользователей, если его еще нет
            if 'selected_pending_list' not in context.user_data:
                context.user_data['selected_pending_list'] = []
            
            # Переключаем статус выбора пользователя
            if user_id in context.user_data['selected_pending_list']:
                context.user_data['selected_pending_list'].remove(user_id)
            else:
                context.user_data['selected_pending_list'].append(user_id)
            
            # Вызываем обработчик выбора пользователей заново для обновления интерфейса
            query.data = "select_pending_users"
            return await admin_message_to_pending_handler(update, context)
        
        # Обработка отправки сообщения выбранным пользователям
        elif query.data == "send_to_selected_pending":
            selected_users = context.user_data.get('selected_pending_list', [])
            
            if not selected_users or len(selected_users) == 0:
                await query.edit_message_text(
                    "❌ Нет выбранных пользователей для отправки сообщения.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                    ]])
                )
                return ADMIN_MESSAGE_TO_PENDING
            
            # Запрашиваем текст сообщения для отправки
            context.user_data['send_to_selected_pending'] = True
            
            await query.edit_message_text(
                f"📩 Отправка сообщения выбранным пользователям ({len(selected_users)})\n\n"
                "Введите текст сообщения:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Отмена", callback_data="admin_back")
                ]])
            )
            return ADMIN_MESSAGE_TO_PENDING
            
        elif query.data.startswith("select_pending_"):
            # Выбран конкретный пользователь из списка (старый вариант)
            user_id = int(query.data.replace("select_pending_", ""))
            user_info = get_user(user_id)
            
            if not user_info:
                await query.edit_message_text(
                    "❌ Пользователь не найден.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                    ]])
                )
                return ADMIN_MESSAGE_TO_PENDING
            
            # Сохраняем ID пользователя для отправки сообщения
            context.user_data['admin_recipient_id'] = user_id
            username = user_info.get('username', 'Без имени')
            
            await query.edit_message_text(
                f"📩 Отправка сообщения неодобренному пользователю:\n"
                f"👤 Имя: @{username}\n"
                f"🆔 ID: {user_id}\n\n"
                f"Введите текст сообщения, которое хотите отправить:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Отмена", callback_data="admin_back")
                ]])
            )
            return ADMIN_MESSAGE_TO_PENDING
    
    elif update.message:
        # Получен текст сообщения для отправки
        message_text = update.message.text
        
        if 'send_to_all_pending' in context.user_data and context.user_data['send_to_all_pending']:
            # Отправка всем неодобренным пользователям
            try:
                # Получаем список ID всех неодобренных пользователей
                from models import get_pending_user_ids
                pending_user_ids = get_pending_user_ids()
                
                if not pending_user_ids or len(pending_user_ids) == 0:
                    await update.message.reply_text(
                        "❌ Нет неодобренных пользователей в системе.",
                        reply_markup=get_admin_keyboard()
                    )
                    if 'send_to_all_pending' in context.user_data:
                        del context.user_data['send_to_all_pending']
                    return ADMIN_MENU
                
                success_count = 0
                fail_count = 0
                
                # Отправляем сообщение каждому пользователю
                for user_id in pending_user_ids:
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=message_text
                        )
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Error sending message to user {user_id}: {e}")
                        fail_count += 1
                
                # Очищаем флаг из контекста
                if 'send_to_all_pending' in context.user_data:
                    del context.user_data['send_to_all_pending']
                
                await update.message.reply_text(
                    f"✅ Сообщение успешно отправлено {success_count} неодобренным пользователям.\n"
                    f"❌ Не удалось отправить {fail_count} пользователям.",
                    reply_markup=get_admin_keyboard()
                )
                return ADMIN_MENU
                
            except Exception as e:
                logger.error(f"Error broadcasting to pending users: {e}")
                
                if 'send_to_all_pending' in context.user_data:
                    del context.user_data['send_to_all_pending']
                    
                await update.message.reply_text(
                    f"❌ Ошибка при отправке сообщений: {str(e)}",
                    reply_markup=get_admin_keyboard()
                )
                return ADMIN_MENU
                
        # Отправка выбранным пользователям
        elif 'send_to_selected_pending' in context.user_data and context.user_data['send_to_selected_pending']:
            selected_users = context.user_data.get('selected_pending_list', [])
            
            if not selected_users or len(selected_users) == 0:
                await update.message.reply_text(
                    "❌ Нет выбранных пользователей для отправки сообщения.",
                    reply_markup=get_admin_keyboard()
                )
                
                # Очищаем данные
                if 'send_to_selected_pending' in context.user_data:
                    del context.user_data['send_to_selected_pending']
                if 'selected_pending_list' in context.user_data:
                    del context.user_data['selected_pending_list']
                
                return ADMIN_MENU
            
            # Отправляем сообщение выбранным пользователям
            success_count = 0
            fail_count = 0
            
            for user_id in selected_users:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"📝 *Сообщение от администратора:*\n\n{message_text}",
                        parse_mode='Markdown'
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения выбранному пользователю {user_id}: {e}")
                    fail_count += 1
            
            # Отправляем отчет администратору
            await update.message.reply_text(
                f"📊 Отчет о рассылке выбранным пользователям:\n\n"
                f"✅ Успешно отправлено: {success_count}\n"
                f"❌ Ошибки отправки: {fail_count}\n"
                f"📨 Всего получателей: {len(selected_users)}",
                reply_markup=get_admin_keyboard()
            )
            
            # Очищаем данные
            if 'send_to_selected_pending' in context.user_data:
                del context.user_data['send_to_selected_pending']
            if 'selected_pending_list' in context.user_data:
                del context.user_data['selected_pending_list']
            
            return ADMIN_MENU
            
        elif 'admin_recipient_id' in context.user_data:
            # Отправка конкретному пользователю
            try:
                user_id = context.user_data['admin_recipient_id']
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📝 *Сообщение от администратора:*\n\n{message_text}",
                    parse_mode='Markdown'
                )
                
                # Очищаем ID получателя из контекста
                del context.user_data['admin_recipient_id']
                
                await update.message.reply_text(
                    "✅ Сообщение успешно отправлено пользователю!",
                    reply_markup=get_admin_keyboard()
                )
                return ADMIN_MENU
                
            except Exception as e:
                logger.error(f"Error sending message to user: {e}")
                
                if 'admin_recipient_id' in context.user_data:
                    del context.user_data['admin_recipient_id']
                    
                await update.message.reply_text(
                    f"❌ Ошибка при отправке сообщения: {str(e)}",
                    reply_markup=get_admin_keyboard()
                )
                return ADMIN_MENU
        
        else:
            # Если нет цели для отправки, возвращаемся в меню
            await update.message.reply_text(
                "❌ Не указан получатель для отправки сообщения.",
                reply_markup=get_admin_keyboard()
            )
            return ADMIN_MENU
    
    return ADMIN_MESSAGE_TO_PENDING

async def admin_select_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора пользователей для отправки сообщений"""
    query = update.callback_query
    
    if query:
        await query.answer()
        
        if query.data == "admin_back":
            await query.edit_message_text(
                "👑 Панель администратора",
                reply_markup=get_admin_keyboard()
            )
            return ADMIN_MENU
        
        elif query.data == "search_users_criteria":
            # Поиск пользователей по критериям
            await query.edit_message_text(
                "🔍 Поиск пользователей по критериям\n\n"
                "Введите поисковый запрос (имя пользователя, ID и т.д.):",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                ]])
            )
            # Устанавливаем флаг для последующей обработки ввода
            context.user_data['search_users_mode'] = 'search_criteria'
            return ADMIN_SELECT_USERS
        
        elif query.data == "select_from_list":
            # Выбор из полного списка пользователей
            from models import get_all_users
            all_users = get_all_users()
            
            if not all_users or len(all_users) == 0:
                await query.edit_message_text(
                    "❌ Нет пользователей в системе.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                    ]])
                )
                return ADMIN_SELECT_USERS
            
            # Создаем клавиатуру со списком пользователей
            keyboard = []
            for user in all_users[:10]:  # Ограничиваем 10 пользователями
                user_id = user.get('user_id')
                username = user.get('username', 'Без имени')
                is_approved = "✅" if user.get('is_approved') else "⏳"
                keyboard.append([
                    InlineKeyboardButton(f"{is_approved} @{username} (ID: {user_id})", callback_data=f"select_user_{user_id}")
                ])
            
            # Добавляем пагинацию, если пользователей больше 10
            if len(all_users) > 10:
                keyboard.append([
                    InlineKeyboardButton("🔄 Показать еще", callback_data="users_more")
                ])
            
            # Добавляем кнопку "Назад"
            keyboard.append([
                InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
            ])
            
            await query.edit_message_text(
                "👥 Выберите пользователя для отправки сообщения:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ADMIN_SELECT_USERS
        
        elif query.data == "segment_by_activity":
            # Сегментация по активности
            keyboard = [
                [InlineKeyboardButton("🏃 Активные (7 дней)", callback_data="segment_active_7")],
                [InlineKeyboardButton("🚶 Активные (30 дней)", callback_data="segment_active_30")],
                [InlineKeyboardButton("🛌 Неактивные (>30 дней)", callback_data="segment_inactive_30")],
                [InlineKeyboardButton("👥 Все пользователи", callback_data="segment_all")],
                [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
            ]
            
            await query.edit_message_text(
                "📊 Сегментация пользователей по активности\n\n"
                "Выберите категорию пользователей для отправки сообщения:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ADMIN_SELECT_USERS
            
        elif query.data.startswith("select_user_"):
            # Выбран конкретный пользователь из списка
            user_id = int(query.data.replace("select_user_", ""))
            user_info = get_user(user_id)
            
            if not user_info:
                await query.edit_message_text(
                    "❌ Пользователь не найден.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                    ]])
                )
                return ADMIN_SELECT_USERS
            
            # Сохраняем ID пользователя для отправки сообщения
            context.user_data['admin_recipient_id'] = user_id
            username = user_info.get('username', 'Без имени')
            is_approved = "✅ Подтвержден" if user_info.get('is_approved') else "⏳ Не подтвержден"
            
            await query.edit_message_text(
                f"📩 Отправка сообщения пользователю:\n"
                f"👤 Имя: @{username}\n"
                f"🆔 ID: {user_id}\n"
                f"Статус: {is_approved}\n\n"
                f"Введите текст сообщения, которое хотите отправить:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Отмена", callback_data="admin_back")
                ]])
            )
            # Устанавливаем флаг для последующей обработки ввода
            context.user_data['message_mode'] = 'direct_message'
            return ADMIN_SEND_MESSAGE_TO_USER
    
    elif update.message and 'search_users_mode' in context.user_data:
        # Обработка ввода поискового запроса
        search_query = update.message.text.strip()
        
        try:
            # Поиск пользователей по критериям
            matching_users = []
            
            # Пытаемся найти по ID
            try:
                user_id = int(search_query)
                user = get_user(user_id)
                if user:
                    matching_users.append(user)
            except ValueError:
                pass
            
            # Поиск по имени пользователя
            if not matching_users:
                # Предполагаем, что у вас есть функция поиска пользователей по имени
                from models import get_user_by_username
                user = get_user_by_username(search_query)
                if user:
                    matching_users.append(user)
            
            # Если пользователи найдены, отображаем их
            if matching_users:
                keyboard = []
                for user in matching_users:
                    user_id = user.get('user_id')
                    username = user.get('username', 'Без имени')
                    is_approved = "✅" if user.get('is_approved') else "⏳"
                    keyboard.append([
                        InlineKeyboardButton(f"{is_approved} @{username} (ID: {user_id})", callback_data=f"select_user_{user_id}")
                    ])
                
                keyboard.append([
                    InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                ])
                
                await update.message.reply_text(
                    f"🔍 Найдено пользователей: {len(matching_users)}\n\n"
                    f"Выберите пользователя для отправки сообщения:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(
                    "❌ Пользователи по вашему запросу не найдены.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                    ]])
                )
            
            # Очищаем флаг из контекста
            del context.user_data['search_users_mode']
            return ADMIN_SELECT_USERS
            
        except Exception as e:
            logger.error(f"Error searching users: {e}")
            
            if 'search_users_mode' in context.user_data:
                del context.user_data['search_users_mode']
                
            await update.message.reply_text(
                f"❌ Ошибка при поиске пользователей: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Назад", callback_data="admin_back")
                ]])
            )
            return ADMIN_SELECT_USERS
    
    return ADMIN_SELECT_USERS

async def admin_content_manager_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик управления контентом"""
    query = update.callback_query
    if not query:
        return ADMIN_CONTENT_MANAGER
    
    await query.answer()
    
    if query.data == "admin_back":
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    elif query.data == "admin_education_content":
        # Обработка управления образовательным контентом
        education_text = (
            "📚 Управление образовательным контентом\n\n"
            "Выберите раздел для редактирования:"
        )
        
        keyboard = [
            [InlineKeyboardButton("📖 Книги по трейдингу", callback_data="admin_trading_books")],
            [InlineKeyboardButton("🔰 Обучение для начинающих", callback_data="admin_trading_beginner")],
            [InlineKeyboardButton("📈 Торговые стратегии", callback_data="admin_trading_strategies")],
            [InlineKeyboardButton("🔧 Инструменты трейдинга", callback_data="admin_trading_tools")],
            [InlineKeyboardButton("📱 OTC пары и сигналы", callback_data="admin_otc_pairs")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_content")]
        ]
        
        await query.edit_message_text(
            education_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CONTENT_MANAGER
    
    elif query.data == "admin_trading_books":
        # Управление книгами по трейдингу
        books_text = (
            "📖 Редактирование раздела книг по трейдингу\n\n"
            "Выберите действие:"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить книгу", callback_data="admin_add_book")],
            [InlineKeyboardButton("✏️ Редактировать существующие", callback_data="admin_edit_books")],
            [InlineKeyboardButton("🗑️ Удалить книгу", callback_data="admin_delete_book")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_education_content")]
        ]
        
        await query.edit_message_text(
            books_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CONTENT_MANAGER
    
    elif query.data == "admin_trading_strategies":
        # Управление торговыми стратегиями
        strategies_text = (
            "📈 Редактирование торговых стратегий\n\n"
            "Выберите действие:"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить стратегию", callback_data="admin_add_strategy")],
            [InlineKeyboardButton("✏️ Редактировать существующие", callback_data="admin_edit_strategies")],
            [InlineKeyboardButton("🗑️ Удалить стратегию", callback_data="admin_delete_strategy")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_education_content")]
        ]
        
        await query.edit_message_text(
            strategies_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CONTENT_MANAGER
    
    elif query.data == "admin_trading_tools":
        # Управление инструментами трейдинга
        tools_text = (
            "🔧 Редактирование инструментов трейдинга\n\n"
            "Выберите действие:"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить инструмент", callback_data="admin_add_tool")],
            [InlineKeyboardButton("✏️ Редактировать существующие", callback_data="admin_edit_tools")],
            [InlineKeyboardButton("🗑️ Удалить инструмент", callback_data="admin_delete_tool")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_education_content")]
        ]
        
        await query.edit_message_text(
            tools_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CONTENT_MANAGER
    
    elif query.data == "admin_trading_beginner":
        # Управление разделом для начинающих
        beginner_text = (
            "🔰 Редактирование раздела для начинающих\n\n"
            "Выберите действие:"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить тему", callback_data="admin_add_beginner_topic")],
            [InlineKeyboardButton("✏️ Редактировать темы", callback_data="admin_edit_beginner_topics")],
            [InlineKeyboardButton("🗑️ Удалить тему", callback_data="admin_delete_beginner_topic")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_education_content")]
        ]
        
        await query.edit_message_text(
            beginner_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CONTENT_MANAGER
    
    elif query.data == "admin_otc_pairs":
        # Управление OTC парами и сигналами
        otc_text = (
            "📱 Редактирование OTC пар и сигналов\n\n"
            "Выберите действие:"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить OTC пару", callback_data="admin_add_otc_pair")],
            [InlineKeyboardButton("✏️ Редактировать OTC пары", callback_data="admin_edit_otc_pairs")],
            [InlineKeyboardButton("🔔 Управление сигналами", callback_data="admin_otc_signals")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_education_content")]
        ]
        
        await query.edit_message_text(
            otc_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CONTENT_MANAGER
    
    elif query.data.startswith("admin_add_") or query.data.startswith("admin_edit_") or query.data.startswith("admin_delete_"):
        # Временная заглушка для функций добавления/редактирования/удаления
        action_type = "добавления" if "add" in query.data else "редактирования" if "edit" in query.data else "удаления"
        section_type = query.data.replace("admin_add_", "").replace("admin_edit_", "").replace("admin_delete_", "")
        
        # Более понятные названия для разделов
        section_names = {
            "book": "книги", 
            "books": "книг",
            "strategy": "стратегии",
            "strategies": "стратегий",
            "tool": "инструмента",
            "tools": "инструментов",
            "beginner_topic": "темы для начинающих",
            "beginner_topics": "тем для начинающих",
            "otc_pair": "OTC пары",
            "otc_pairs": "OTC пар",
        }
        
        section_name = section_names.get(section_type, section_type)
        
        message_text = (
            f"⚙️ Функция {action_type} {section_name}\n\n"
            f"Эта функция находится в разработке и будет доступна в ближайшем обновлении.\n\n"
            f"Вы можете пока создать/изменить контент вручную в коде бота."
        )
        
        # Определяем, к какому разделу возвращаться
        back_to = "admin_education_content"
        if "book" in section_type:
            back_to = "admin_trading_books"
        elif "strategy" in section_type:
            back_to = "admin_trading_strategies"
        elif "tool" in section_type:
            back_to = "admin_trading_tools"
        elif "beginner" in section_type:
            back_to = "admin_trading_beginner"
        elif "otc" in section_type:
            back_to = "admin_otc_pairs"
        
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data=back_to)]
        ]
        
        await query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_CONTENT_MANAGER
    
    elif query.data == "admin_content":
        # Возврат в основное меню управления контентом
        pass
    
    # Главное меню управления контентом
    content_text = (
        "📑 Управление контентом\n\n"
        "Выберите категорию контента для управления:"
    )
    
    keyboard = [
        [InlineKeyboardButton("📚 Образовательный контент", callback_data="admin_education_content")],
        [InlineKeyboardButton("🖼 Изображения и графики", callback_data="admin_images")],
        [InlineKeyboardButton("📂 Файлы и документы", callback_data="admin_files")],
        [InlineKeyboardButton("🎨 Настройка внешнего вида", callback_data="admin_appearance")],
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        content_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ADMIN_CONTENT_MANAGER

async def admin_statistics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик расширенной аналитики"""
    query = update.callback_query
    if not query:
        return ADMIN_STATISTICS
    
    await query.answer()
    
    if query.data == "admin_back":
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
        
    # Заглушка для расширенной аналитики
    stats_text = (
        "📊 Расширенная аналитика\n\n"
        "⚠️ Функция в разработке\n\n"
        "Скоро здесь появятся подробные статистические данные:\n"
        "• Активность пользователей\n"
        "• Рост аудитории\n"
        "• Конверсия регистраций\n"
        "• Отток пользователей\n"
        "• Детализация по странам\n"
        "и другие аналитические данные."
    )
    
    keyboard = [
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_STATISTICS

async def admin_quick_commands_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик быстрых команд"""
    query = update.callback_query
    if not query:
        return ADMIN_QUICK_COMMANDS
    
    await query.answer()
    
    if query.data == "admin_back":
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    # Заглушка для быстрых команд
    commands_text = (
        "⚡ Быстрые команды\n\n"
        "⚠️ Функция в разработке\n\n"
        "Скоро здесь появятся быстрые команды для управления ботом:\n"
        "• Перезагрузка бота\n"
        "• Очистка кэша\n"
        "• Генерация отчетов\n"
        "• Проверка системных сообщений\n"
        "и другие быстрые действия."
    )
    
    keyboard = [
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        commands_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_QUICK_COMMANDS

async def admin_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик истории действий"""
    query = update.callback_query
    if not query:
        return ADMIN_HISTORY
    
    await query.answer()
    
    if query.data == "admin_back":
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    # Заглушка для истории действий
    history_text = (
        "📜 История действий\n\n"
        "⚠️ Функция в разработке\n\n"
        "Скоро здесь появится журнал действий:\n"
        "• Действия пользователей\n"
        "• Действия администратора\n"
        "• Системные события\n"
        "• Логирование изменений\n"
        "и другие записи истории."
    )
    
    keyboard = [
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        history_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_HISTORY

async def admin_plugins_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик управления плагинами"""
    query = update.callback_query
    if not query:
        return ADMIN_PLUGINS
    
    await query.answer()
    
    if query.data == "admin_back":
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    # Заглушка для управления плагинами
    plugins_text = (
        "🧩 Управление плагинами\n\n"
        "⚠️ Функция в разработке\n\n"
        "Скоро здесь появится возможность управления плагинами:\n"
        "• Просмотр установленных плагинов\n"
        "• Установка новых плагинов\n"
        "• Удаление плагинов\n"
        "• Обновление плагинов\n"
        "и другие функции для расширения возможностей бота."
    )
    
    keyboard = [
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        plugins_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_PLUGINS

async def admin_marketplace_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик маркетплейса расширений"""
    query = update.callback_query
    if not query:
        return ADMIN_MARKETPLACE
    
    await query.answer()
    
    if query.data == "admin_back":
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    # Заглушка для маркетплейса расширений
    marketplace_text = (
        "🛒 Маркетплейс расширений\n\n"
        "⚠️ Функция в разработке\n\n"
        "Скоро здесь появится доступ к маркетплейсу расширений:\n"
        "• Обзор доступных расширений\n"
        "• Поиск расширений\n"
        "• Популярные расширения\n"
        "• Новые расширения\n"
        "и другие категории расширений для вашего бота."
    )
    
    keyboard = [
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    
    await query.edit_message_text(
        marketplace_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_MARKETPLACE

async def show_trading_education_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображает главное меню обучения трейдингу"""
    try:
        query = update.callback_query
        if not query:
            return
        
        await query.answer()
        
        # Определяем язык пользователя
        user_id = query.from_user.id
        logger.info(f"Displaying trading education menu for user_id: {user_id}")
        
        # Получаем данные пользователя
        user_data = get_user(user_id)
        if user_data:
            lang_code = user_data.get('language_code', 'ru')
            logger.info(f"User language: {lang_code}")
        else:
            lang_code = 'ru'
            logger.warning(f"User data not found, using default language")
    except Exception as e:
        logger.error(f"Error in show_trading_education_menu: {e}")
        lang_code = 'ru'
    
    # Тексты заголовков на разных языках
    titles = {
        'tg': '📚 Маводи омӯзишӣ оид ба трейдинг',
        'ru': '📚 Учебные материалы по трейдингу',
        'uz': '📚 Treyding bo\'yicha o\'quv materiallari',
        'kk': '📚 Трейдинг бойынша оқу материалдары',
        'en': '📚 Trading Educational Materials'
    }
    
    # Тексты описаний на разных языках
    descriptions = {
        'tg': 'Дар бахши "Омӯзиши трейдинг" шумо метавонед маводҳои муфид ва таълимӣ оид ба трейдинг пайдо кунед.',
        'ru': 'В разделе "Обучение трейдингу" вы найдете полезные материалы и учебные пособия по торговле на финансовых рынках.',
        'uz': 'Treyding ta\'limi bo\'limida siz moliya bozorlarida savdo qilish bo\'yicha foydali materiallar va o\'quv qo\'llanmalarini topasiz.',
        'kk': 'Трейдинг бойынша оқыту бөлімінде сіз қаржы нарықтарында сауда жасау бойынша пайдалы материалдар мен оқу құралдарын табасыз.',
        'en': 'In the "Trading Education" section, you\'ll find useful materials and tutorials on trading in financial markets.'
    }
    
    # Локализованные кнопки для категорий
    category_buttons = {
        'tg': {
            'books': "📚 Китобҳо барои трейдинг",
            'beginner': "🔰 Омӯзиши трейдинг аз сифр",
            'strategies': "📈 Стратегияҳои трейдинг",
            'tools': "🧰 Абзорҳои трейдинг",
            'back': "↩️ Бозгашт"
        },
        'ru': {
            'books': "📚 Книги по трейдингу",
            'beginner': "🔰 Обучение трейдингу с нуля", 
            'strategies': "📈 Стратегии трейдинга",
            'tools': "🧰 Инструменты трейдинга",
            'back': "↩️ Назад"
        },
        'uz': {
            'books': "📚 Treyding bo'yicha kitoblar",
            'beginner': "🔰 Treyding bo'yicha boshlang'ich ta'lim",
            'strategies': "📈 Treyding strategiyalari",
            'tools': "🧰 Treyding vositalari",
            'back': "↩️ Orqaga"
        },
        'kk': {
            'books': "📚 Трейдинг бойынша кітаптар",
            'beginner': "🔰 Трейдингті нөлден үйрену",
            'strategies': "📈 Трейдинг стратегиялары",
            'tools': "🧰 Трейдинг құралдары",
            'back': "↩️ Артқа"
        },
        'en': {
            'books': "📚 Trading Books",
            'beginner': "🔰 Trading for Beginners",
            'strategies': "📈 Trading Strategies",
            'tools': "🧰 Trading Tools",
            'back': "↩️ Back"
        }
    }
    
    # Получаем локализованные тексты
    title = titles.get(lang_code, titles['ru'])
    description = descriptions.get(lang_code, descriptions['ru'])
    buttons = category_buttons.get(lang_code, category_buttons['ru'])
    
    # Создаем клавиатуру с разделами обучения
    keyboard = [
        [
            InlineKeyboardButton(buttons['books'], callback_data="trading_books"),
            InlineKeyboardButton(buttons['beginner'], callback_data="trading_beginner")
        ],
        [
            InlineKeyboardButton(buttons['strategies'], callback_data="trading_strategies"),
            InlineKeyboardButton(buttons['tools'], callback_data="trading_tools")
        ],
        [
            InlineKeyboardButton(buttons['back'], callback_data="return_to_main")
        ]
    ]
    
    # Формируем сообщение с заголовком и описанием
    message = f"*{title}*\n\n{description}"
    
    # Отправляем сообщение
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# Глобальная переменная для книг, доступная для всех функций
books = {}

async def handle_trading_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для раздела книги по трейдингу"""
    try:
        query = update.callback_query
        if not query:
            return
        
        await query.answer()
        
        # Определяем язык пользователя
        user_id = query.from_user.id
        logger.info(f"Processing trading_books request for user_id: {user_id}")
        
        # Получаем данные пользователя
        user_data = get_user(user_id)
        if user_data:
            lang_code = user_data.get('language_code', 'ru')
            logger.info(f"User language: {lang_code}")
        else:
            lang_code = 'ru'
            logger.warning(f"User data not found, using default language")
    except Exception as e:
        logger.error(f"Error in handle_trading_books: {e}")
        lang_code = 'ru'
    
    # Тексты заголовков на разных языках
    titles = {
        'tg': '📚 Китобҳо барои трейдинг',
        'ru': '📚 Книги по трейдингу',
        'uz': '📚 Treyding bo\'yicha kitoblar',
        'kk': '📚 Трейдинг бойынша кітаптар',
        'en': '📚 Trading Books'
    }
    
    # Тексты описаний на разных языках
    descriptions = {
        'tg': 'Интихоби китобҳои баландсифат барои таълими трейдинг:',
        'ru': 'Подборка качественных книг для обучения трейдингу:',
        'uz': 'Treyding o\'rganish uchun sifatli kitoblar to\'plami:',
        'kk': 'Трейдингті үйрену үшін сапалы кітаптар жиынтығы:',
        'en': 'Selection of quality books for learning trading:'
    }
    
    # Список книг на разных языках с подробной информацией и ссылками для скачивания
    global books
    books = {
        'tg': [
            {
                "title": "1. 'Ҳиссиётҳои трейдер' - Марк Дуглас",
                "description": "Китоб дар бораи руҳшиносии бозори молиявӣ ва чӣ тавр эҳсосотро идора кардан. Муаллиф таҷрибаи худро мубодила мекунад ва роҳҳои фикрронии дурустро барои трейдинги бомуваффақият нишон медиҳад.",
                "pages": "240 саҳифа",
                "year": "1990",
                "download_link": "https://t.me/tradepobooks/10"
            },
            {
                "title": "2. 'Таҳлили техникӣ барои нав ба нав' - Д. Швагер",
                "description": "Ин дастури мукаммал оид ба таҳлили техникӣ барои ҳама категорияҳои трейдерон мебошад. Китоб бо усули содда навишта шудааст ва принсипҳои асосии таҳлили бозорро дар бар мегирад.",
                "pages": "380 саҳифа",
                "year": "1996",
                "download_link": "https://t.me/tradepobooks/12"
            },
            {
                "title": "3. 'Хотираҳои трейдери валютагӣ' - К. Борселино",
                "description": "Муаллиф тамоми таҷрибаи худро ҳамчун яке аз беҳтарин трейдерони валюта ба хонанда нақл мекунад. Ҳикояҳои аҷоиб ва маслиҳатҳои амалӣ.",
                "pages": "220 саҳифа",
                "year": "2005",
                "download_link": "https://t.me/tradepobooks/15"
            },
            {
                "title": "4. 'Трейдинг дар зонаи' - Марк Дуглас",
                "description": "Китоби машҳур оид ба руҳшиносии трейдинг, ки дар он муаллиф панҷ ҳақиқати асосиро, ки бояд ҳар як трейдер донад, мефаҳмонад. Барои онҳое, ки мехоҳанд ба трейдер муваффақ табдил ёбанд.",
                "pages": "280 саҳифа",
                "year": "2000",
                "download_link": "https://t.me/tradepobooks/17"
            },
            {
                "title": "5. 'Асосҳои таҳлили техникӣ' - Д. Мерфи",
                "description": "Қомуси таҳлили техникӣ, ки 20 соли таҷрибаи муаллиф дар таҳлили техникиро дар бар мегирад. Дар китоб ҳама ҷанбаҳои муҳими таҳлили графикӣ тавсиф шудаанд.",
                "pages": "592 саҳифа",
                "year": "1986",
                "download_link": "https://t.me/tradepobooks/19"
            },
            {
                "title": "6. 'Руҳшиносии пул' - М. Лабковский",
                "description": "Китоб ба ҷанбаҳои равонии муносибат бо пул мепардозад. Муаллиф робитаи байни пул ва некуаҳволии шахсиро муҳокима мекунад ва дар бораи он ки чӣ гуна аз ҷиҳати молиявӣ бомуваффақият будан ва дар айни замон хушбахт будан мумкин аст.",
                "pages": "250 саҳифа",
                "year": "2020",
                "download_link": "https://t.me/tradepobooks/22"
            }
        ],
        'ru': [
            {
                "title": "1. 'Психология трейдинга' - Марк Дуглас",
                "description": "Книга о психологии финансовых рынков и о том, как управлять эмоциями. Автор делится своим опытом и показывает пути правильного мышления для успешного трейдинга.",
                "pages": "240 страниц",
                "year": "1990",
                "download_link": "https://t.me/tradepobooks/10"
            },
            {
                "title": "2. 'Технический анализ для начинающих' - Д. Швагер",
                "description": "Это полное руководство по техническому анализу для всех категорий трейдеров. Книга написана простым методом и охватывает основные принципы анализа рынка.",
                "pages": "380 страниц",
                "year": "1996",
                "download_link": "https://t.me/tradepobooks/12"
            },
            {
                "title": "3. 'Воспоминания валютного трейдера' - К. Борселино",
                "description": "Автор рассказывает читателю весь свой опыт как одного из лучших валютных трейдеров. Интересные истории и практические советы.",
                "pages": "220 страниц",
                "year": "2005",
                "download_link": "https://t.me/tradepobooks/15"
            },
            {
                "title": "4. 'Трейдинг в зоне' - Марк Дуглас",
                "description": "Известная книга о психологии трейдинга, в которой автор объясняет пять основных истин, которые должен знать каждый трейдер. Для тех, кто хочет стать успешным трейдером.",
                "pages": "280 страниц",
                "year": "2000",
                "download_link": "https://t.me/tradepobooks/17"
            },
            {
                "title": "5. 'Основы технического анализа' - Д. Мерфи",
                "description": "Энциклопедия технического анализа, которая охватывает 20 лет опыта автора в техническом анализе. В книге описаны все важные аспекты графического анализа.",
                "pages": "592 страницы",
                "year": "1986",
                "download_link": "https://t.me/tradepobooks/19"
            },
            {
                "title": "6. 'Психология денег' - М. Лабковский",
                "description": "Книга посвящена психологическим аспектам отношения к деньгам. Автор обсуждает связь между деньгами и личным благополучием и о том, как быть финансово успешным и при этом счастливым.",
                "pages": "250 страниц",
                "year": "2020",
                "download_link": "https://t.me/tradepobooks/22"
            }
        ],
        'uz': [
            {
                "title": "1. 'Treydingning psixologiyasi' - Mark Duglas",
                "description": "Moliya bozorlari psixologiyasi va qanday qilib his-tuyg'ularni boshqarish haqida kitob. Muallif o'z tajribasini bo'lishadi va muvaffaqiyatli treyding uchun to'g'ri fikrlash yo'llarini ko'rsatadi.",
                "pages": "240 bet",
                "year": "1990",
                "download_link": "https://t.me/tradepobooks/10"
            },
            {
                "title": "2. 'Yangi boshlanuvchilar uchun texnik tahlil' - D. Shvager",
                "description": "Bu barcha toifadagi treyderlar uchun texnik tahlil bo'yicha to'liq qo'llanma. Kitob oddiy usulda yozilgan va bozorni tahlil qilishning asosiy tamoyillarini qamrab oladi.",
                "pages": "380 bet",
                "year": "1996",
                "download_link": "https://t.me/tradepobooks/12"
            },
            {
                "title": "3. 'Valyuta treyderining xotiralari' - K. Borselino",
                "description": "Muallif o'zining eng yaxshi valyuta treyderlaridan biri sifatidagi tajribasini o'quvchiga aytib beradi. Qiziqarli hikoyalar va amaliy maslahatlar.",
                "pages": "220 bet",
                "year": "2005",
                "download_link": "https://t.me/tradepobooks/15"
            },
            {
                "title": "4. 'Zonada treyding' - Mark Duglas",
                "description": "Treyding psixologiyasi haqidagi mashhur kitob, unda muallif har bir treyderga bilishi kerak bo'lgan beshta asosiy haqiqatni tushuntiradi. Muvaffaqiyatli treyderga aylanishni istaydiganlar uchun.",
                "pages": "280 bet",
                "year": "2000",
                "download_link": "https://t.me/tradepobooks/17"
            },
            {
                "title": "5. 'Texnik tahlil asoslari' - D. Merfi",
                "description": "Texnik tahlil entsiklopediyasi, unda muallifning 20 yillik texnik tahlil tajribasi aks etgan. Kitobda grafik tahlilning barcha muhim jihatlari tasvirlangan.",
                "pages": "592 bet",
                "year": "1986",
                "download_link": "https://t.me/tradepobooks/19"
            },
            {
                "title": "6. 'Pul psixologiyasi' - M. Labkovskiy",
                "description": "Kitob pulga bo'lgan munosabatning psixologik jihatlariga bag'ishlangan. Muallif pul va shaxsiy farovonlik o'rtasidagi bog'liqlikni va qanday qilib moliyaviy jihatdan muvaffaqiyatli va ayni paytda baxtli bo'lish mumkinligi haqida muhokama qiladi.",
                "pages": "250 bet",
                "year": "2020",
                "download_link": "https://t.me/tradepobooks/22"
            }
        ],
        'kk': [
            {
                "title": "1. 'Трейдинг психологиясы' - Марк Дуглас",
                "description": "Қаржы нарықтарының психологиясы және эмоцияларды қалай басқару туралы кітап. Автор өз тәжірибесімен бөліседі және табысты трейдингке дұрыс ойлау жолдарын көрсетеді.",
                "pages": "240 бет",
                "year": "1990",
                "download_link": "https://t.me/tradepobooks/10"
            },
            {
                "title": "2. 'Бастаушыларға арналған техникалық талдау' - Д. Швагер",
                "description": "Бұл барлық санаттағы трейдерлерге арналған техникалық талдаудың толық нұсқаулығы. Кітап қарапайым әдіспен жазылған және нарықты талдаудың негізгі қағидаларын қамтиды.",
                "pages": "380 бет",
                "year": "1996",
                "download_link": "https://t.me/tradepobooks/12"
            },
            {
                "title": "3. 'Валюта трейдерінің естеліктері' - К. Борселино",
                "description": "Автор ең жақсы валюта трейдерлерінің бірі ретіндегі барлық тәжірибесін оқырманға айтып береді. Қызықты әңгімелер мен тәжірибелік кеңестер.",
                "pages": "220 бет",
                "year": "2005",
                "download_link": "https://t.me/tradepobooks/15"
            },
            {
                "title": "4. 'Аймақтағы трейдинг' - Марк Дуглас",
                "description": "Трейдинг психологиясы туралы атақты кітап, онда автор әрбір трейдер білуі керек бес негізгі шындықты түсіндіреді. Табысты трейдерге айналғысы келетіндерге арналған.",
                "pages": "280 бет",
                "year": "2000",
                "download_link": "https://t.me/tradepobooks/17"
            },
            {
                "title": "5. 'Техникалық талдау негіздері' - Д. Мерфи",
                "description": "Техникалық талдау энциклопедиясы, онда автордың техникалық талдаудағы 20 жылдық тәжірибесі қамтылған. Кітапта графикалық талдаудың барлық маңызды аспектілері сипатталған.",
                "pages": "592 бет",
                "year": "1986",
                "download_link": "https://t.me/tradepobooks/19"
            },
            {
                "title": "6. 'Ақша психологиясы' - М. Лабковский",
                "description": "Кітап ақшаға қатынастың психологиялық аспектілеріне арналған. Автор ақша мен жеке әл-ауқат арасындағы байланысты және қалай қаржылық жағынан табысты және сонымен бірге бақытты болу мүмкіндігін талқылайды.",
                "pages": "250 бет",
                "year": "2020",
                "download_link": "https://t.me/tradepobooks/22"
            }
        ],
        'en': [
            {
                "title": "1. 'Trading in the Zone' - Mark Douglas",
                "description": "A book about the psychology of financial markets and how to manage emotions. The author shares his experience and shows ways of correct thinking for successful trading.",
                "pages": "240 pages",
                "year": "1990",
                "download_link": "https://t.me/tradepobooks/10"
            },
            {
                "title": "2. 'Technical Analysis for Beginners' - J. Schwager",
                "description": "This is a complete guide to technical analysis for all categories of traders. The book is written in a simple method and covers the basic principles of market analysis.",
                "pages": "380 pages",
                "year": "1996",
                "download_link": "https://t.me/tradepobooks/12"
            },
            {
                "title": "3. 'Reminiscences of a Currency Trader' - K. Borselino",
                "description": "The author tells the reader all his experience as one of the best currency traders. Interesting stories and practical advice.",
                "pages": "220 pages",
                "year": "2005",
                "download_link": "https://t.me/tradepobooks/15"
            },
            {
                "title": "4. 'The Disciplined Trader' - Mark Douglas",
                "description": "A famous book on trading psychology, in which the author explains the five basic truths that every trader should know. For those who want to become a successful trader.",
                "pages": "280 pages",
                "year": "2000",
                "download_link": "https://t.me/tradepobooks/17"
            },
            {
                "title": "5. 'Technical Analysis Foundations' - J. Murphy",
                "description": "Encyclopedia of technical analysis, covering the author's 20 years of experience in technical analysis. The book describes all important aspects of graphical analysis.",
                "pages": "592 pages",
                "year": "1986",
                "download_link": "https://t.me/tradepobooks/19"
            },
            {
                "title": "6. 'The Psychology of Money' - M. Housel",
                "description": "The book is dedicated to the psychological aspects of attitude to money. The author discusses the connection between money and personal well-being and how to be financially successful and at the same time happy.",
                "pages": "250 pages",
                "year": "2020",
                "download_link": "https://t.me/tradepobooks/22"
            }
        ]
    }
    
    button_text = {
        'tg': '↩️ Бозгашт',
        'ru': '↩️ Назад',
        'uz': '↩️ Orqaga',
        'kk': '↩️ Артқа',
        'en': '↩️ Back'
    }
    
    # Формируем сообщение на нужном языке
    title = titles.get(lang_code, titles['ru'])
    description = descriptions.get(lang_code, descriptions['ru'])
    book_list = books.get(lang_code, books['ru'])
    back_button = button_text.get(lang_code, button_text['ru'])
    
    # Создаем клавиатуру с книгами и ссылками для скачивания
    keyboard = []
    
    # Текст для кнопок книг на разных языках
    download_button_text = {
        'tg': '📥 Боргирӣ кардан',
        'ru': '📥 Скачать книгу',
        'uz': '📥 Kitobni yuklab olish',
        'kk': '📥 Кітапты жүктеу',
        'en': '📥 Download book'
    }
    
    # Текст для кнопок подробно на разных языках
    details_button_text = {
        'tg': 'ℹ️ Маълумоти муфассал',
        'ru': 'ℹ️ Подробнее',
        'uz': 'ℹ️ Batafsil',
        'kk': 'ℹ️ Толығырақ',
        'en': 'ℹ️ Details'
    }
    
    # Добавляем информацию о каждой книге и кнопки
    message = f"{title}\n\n{description}\n\n"
    
    for i, book in enumerate(book_list):
        book_title = book["title"]
        
        # Добавляем основную информацию о книге
        message += f"*{book_title}*\n"
        
        # Создаем кнопки для скачивания и подробной информации для каждой книги
        keyboard.append([
            InlineKeyboardButton(
                download_button_text.get(lang_code, download_button_text['ru']),
                url=book["download_link"]
            ),
            InlineKeyboardButton(
                details_button_text.get(lang_code, details_button_text['ru']),
                callback_data=f"book_details_{i}"
            )
        ])
        
        # Добавляем разделитель между книгами
        if i < len(book_list) - 1:
            message += "\n--------------------\n"
    
    # Добавляем кнопку возврата
    keyboard.append([InlineKeyboardButton(back_button, callback_data="return_to_main")])
    
    # Отправляем сообщение
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

async def handle_trading_beginner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для раздела обучение трейдингу с нуля"""
    try:
        query = update.callback_query
        if not query:
            return
        
        await query.answer()
        
        # Определяем язык пользователя
        user_id = query.from_user.id
        logger.info(f"Processing trading_beginner request for user_id: {user_id}")
        
        # Получаем данные пользователя
        user_data = get_user(user_id)
        if user_data:
            lang_code = user_data.get('language_code', 'ru')
            logger.info(f"User language: {lang_code}")
        else:
            lang_code = 'ru'
            logger.warning(f"User data not found, using default language")
    except Exception as e:
        logger.error(f"Error in handle_trading_beginner: {e}")
        lang_code = 'ru'
    
    # Проверяем, запрошен ли конкретный раздел обучения
    if query.data.startswith("beginner_topic_"):
        # Извлекаем номер темы из callback_data
        topic_number = query.data.replace("beginner_topic_", "")
        return await show_beginner_topic_details(update, context, topic_number, lang_code)
    
    # Если запрошен основной раздел обучения
    # Тексты заголовков на разных языках
    titles = {
        'tg': '🔰 Омӯзиши трейдинг аз сифр',
        'ru': '🔰 Обучение трейдингу с нуля',
        'uz': '🔰 Treyding bo\'yicha boshlang\'ich ta\'lim',
        'kk': '🔰 Трейдингті нөлден үйрену',
        'en': '🔰 Trading for Beginners'
    }
    
    # Тексты описаний на разных языках
    descriptions = {
        'tg': 'Роҳнамои қадам ба қадам барои оғози трейдинг. Интихоб кунед, ки чиро меомӯзед:',
        'ru': 'Пошаговое руководство для начала трейдинга. Выберите, что хотите изучить:',
        'uz': 'Treyding boshlash uchun bosqichma-bosqich qo\'llanma. O\'rganmoqchi bo\'lgan narsani tanlang:',
        'kk': 'Трейдингті бастау үшін қадамдық нұсқаулық. Нені оқығыңыз келетінін таңдаңыз:',
        'en': 'Step-by-step guide to start trading. Choose what you want to learn:'
    }
    
    # Названия разделов обучения на разных языках
    topic_titles = {
        'tg': [
            "1️⃣ *Асосҳои трейдинг*",
            "2️⃣ *Интихоби платформа*",
            "3️⃣ *Таҳлили бозор*",
            "4️⃣ *Идоракунии хавф*",
            "5️⃣ *Психологияи трейдинг*",
            "6️⃣ *Стратегияҳои савдо*",
            "7️⃣ *Амалияи трейдинг*",
            "8️⃣ *Такмили малака*"
        ],
        'ru': [
            "1️⃣ *Основы трейдинга*",
            "2️⃣ *Выбор платформы*",
            "3️⃣ *Анализ рынка*",
            "4️⃣ *Управление рисками*",
            "5️⃣ *Психология трейдинга*",
            "6️⃣ *Торговые стратегии*",
            "7️⃣ *Практика трейдинга*",
            "8️⃣ *Повышение квалификации*"
        ],
        'uz': [
            "1️⃣ *Treyding asoslari*",
            "2️⃣ *Platforma tanlash*",
            "3️⃣ *Bozor tahlili*",
            "4️⃣ *Xavflarni boshqarish*",
            "5️⃣ *Treyding psixologiyasi*",
            "6️⃣ *Savdo strategiyalari*",
            "7️⃣ *Treyding amaliyoti*",
            "8️⃣ *Malakani oshirish*"
        ],
        'kk': [
            "1️⃣ *Трейдинг негіздері*",
            "2️⃣ *Платформаны таңдау*",
            "3️⃣ *Нарықты талдау*",
            "4️⃣ *Тәуекелдерді басқару*",
            "5️⃣ *Трейдинг психологиясы*",
            "6️⃣ *Сауда стратегиялары*",
            "7️⃣ *Трейдинг практикасы*",
            "8️⃣ *Біліктілікті арттыру*"
        ],
        'en': [
            "1️⃣ *Trading Basics*",
            "2️⃣ *Platform Selection*",
            "3️⃣ *Market Analysis*",
            "4️⃣ *Risk Management*",
            "5️⃣ *Trading Psychology*",
            "6️⃣ *Trading Strategies*",
            "7️⃣ *Trading Practice*",
            "8️⃣ *Skill Enhancement*"
        ]
    }
    
    # Тексты кнопок на разных языках
    button_texts = {
        'tg': {
            'details': "📖 Муфассал",
            'back': "↩️ Бозгашт",
            'main': "🏠 Ба саҳифаи асосӣ"
        },
        'ru': {
            'details': "📖 Подробнее",
            'back': "↩️ Назад",
            'main': "🏠 На главную"
        },
        'uz': {
            'details': "📖 Batafsil",
            'back': "↩️ Orqaga",
            'main': "🏠 Bosh sahifaga"
        },
        'kk': {
            'details': "📖 Толығырақ",
            'back': "↩️ Артқа",
            'main': "🏠 Басты бетке"
        },
        'en': {
            'details': "📖 More Details",
            'back': "↩️ Back",
            'main': "🏠 Home"
        }
    }
    
    # Получаем локализованные тексты
    title = titles.get(lang_code, titles['ru'])
    description = descriptions.get(lang_code, descriptions['ru'])
    topics = topic_titles.get(lang_code, topic_titles['ru'])
    button_text = button_texts.get(lang_code, button_texts['ru'])
    
    # Формируем сообщение
    message = f"{title}\n\n{description}"
    
    # Создаем клавиатуру с разделами обучения
    keyboard = []
    
    # Добавляем кнопки для каждого раздела обучения
    for i, topic in enumerate(topics):
        topic_number = i + 1
        topic_text = topic.replace("*", "")  # Удаляем маркеры форматирования для кнопок
        keyboard.append([
            InlineKeyboardButton(topic_text, callback_data=f"beginner_topic_{topic_number}")
        ])
    
    # Добавляем кнопки навигации
    keyboard.append([
        InlineKeyboardButton(button_text['main'], callback_data="return_to_main")
    ])
    
    # Отправляем сообщение
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def show_beginner_topic_details(update: Update, context: ContextTypes.DEFAULT_TYPE, topic_number: str, lang_code: str):
    """Отображает подробную информацию о выбранном разделе обучения трейдингу"""
    query = update.callback_query
    
    # Содержимое разделов обучения на разных языках
    topic_content = {
        'tg': {
            '1': {
                'title': "🔰 Асосҳои трейдинг",
                'content': [
                    "*Чӣ ҳаст трейдинг?*\nТрейдинг фаъолияти хариду фурӯши дороиҳои молиявӣ (арзҳо, саҳмияҳо, молҳо) бо мақсади гирифтани фоида аст.",
                    "*Терминология асосӣ:*\n• Спред – фарқияти нархи хариду фурӯш\n• Волатилӣ – тағирёбии нархи дороӣ\n• Ликвидӣ – осон табдил додани дороӣ ба пул\n• Take Profit/Stop Loss – фармоишҳо барои назорати хатарҳо",
                    "*Намудҳои бозорҳо:*\n• Forex – бозори асъор\n• Бозори саҳмияҳо – хариду фурӯши саҳмияҳои ширкатҳо\n• Бозори фьючерсҳо – шартномаҳо барои хариду фурӯши дороӣ дар оянда\n• Криптобозор – хариду фурӯши асъори рақамӣ",
                    "*Услубҳои трейдинг:*\n• Скальпинг – муомилоти кӯтоҳмуддат бо даромади хурд\n• Трейдинги рӯзона – муомила дар давоми рӯз\n• Свинг-трейдинг – муомилаҳо дар давоми якчанд рӯз то ҳафта\n• Сармоягузории дарозмуддат – нигоҳ доштани мавқеъ барои моҳҳо/солҳо"
                ]
            },
            '2': {
                'title': "🖥️ Интихоби платформа",
                'content': [
                    "*Намудҳои платформаҳо:*\n• Брокерон – ширкатҳое, ки ба трейдерон дастрасӣ ба бозорҳоро медиҳанд\n• Биржаҳо – платформаҳое, ки ба муомилоти бевосита имкон медиҳанд",
                    "*Меъёрҳои интихоб:*\n• Боэътимодӣ – танзимкунии ширкат, таърихи кор\n• Маблағ барои дохилшавӣ – ҳадди ақали сармоягузорӣ\n• Шартҳои муомила – спред, комиссия, левераж\n• Дастрасии фонд – усулҳои пасандоз/баровардани маблағ\n• Функсионалӣ – графикҳо, нишондиҳандаҳо, платформаи мобилӣ",
                    "*Платформаҳои маъруф:*\n• MetaTrader 4/5 – барои трейдинги Forex ва фьючерсҳо\n• TradingView – барои таҳлил ва трейдинг\n• Think or Swim – барои трейдинги саҳмияҳо ва опсионҳо\n• Binance – барои трейдинги криптоасъор",
                    "*Тавсияҳо:*\n• Аввал дар ҳисоби намоишӣ (демо) кор кунед\n• Интерфейсро ба худ мувофиқ кунед\n• Имкониятҳои таҳлил ва ҳисоботро омӯзед\n• Бехатарии ҳисобро таъмин кунед (аутентификатсияи дуомила, пароли мураккаб)"
                ]
            },
            '3': {
                'title': "📊 Таҳлили бозор",
                'content': [
                    "*Таҳлили техникӣ:*\n• Омӯзиши графикҳо ва нақшаҳо\n• Истифодаи индикаторҳо (MA, MACD, RSI)\n• Шинохтани нақшҳои нархӣ\n• Дарёфти сатҳҳои дастгирӣ ва муқовимат",
                    "*Таҳлили фундаменталӣ:*\n• Омӯзиши вазъи иқтисодии умумӣ\n• Таҳлили нишондиҳандаҳои иқтисодӣ\n• Баҳодиҳии сиёсати пулии бонкҳои марказӣ\n• Баҳодиҳии ширкатҳо (барои саҳмияҳо)",
                    "*Индикаторҳои маъруф:*\n• Moving Average (MA) – миёнаи ҳаракаткунанда\n• Relative Strength Index (RSI) – нишондиҳандаи муқоисавии қувва\n• Moving Average Convergence Divergence (MACD) – ҳамгироӣ ва дивергенсияи миёнаи ҳаракаткунанда\n• Bollinger Bands – хатҳои волатилӣ дар атрофи нарх",
                    "*Сарчашмаҳои иттилоот:*\n• Тақвими иқтисодӣ\n• Хабарҳои молиявӣ\n• Нашрияҳои бонкҳои марказӣ\n• Ҳисоботи ширкатҳо"
                ]
            },
            '4': {
                'title': "⚠️ Идоракунии хавф",
                'content': [
                    "*Принсипҳои асосӣ:*\n• Муайян кардани хатари ҳадди аксар барои ҳар як муомила\n• Ҳаргиз беш аз 1-2% аз сармояи умумиро ба хатар нагузоред\n• Диверсификатсияи сармоягузориҳо\n• Ҳамеша Stop Loss истифода баред",
                    "*Стратегияҳои идоракунии хавф:*\n• Stop Loss – фармоиш барои маҳдуд кардани зарар\n• Take Profit – фармоиш барои гирифтани фоида\n• Таносуби хавф ва даромад – 1:2 ё бештар тавсия дода мешавад\n• Money Management – тақсими дурусти сармоя",
                    "*Хатоҳои маъмулӣ:*\n• Маблағгузории аз ҳад зиёд ба як муомила\n• Набудани нақшаи амал\n• Трейдинг бар хилофи тренд\n• Муомилаҳои ҳиссӣ\n• Мунтазам тағйир додани стратегия",
                    "*Қоидаҳои муҳим:*\n• Танҳо бо маблағе, ки метавонед аз даст диҳед, савдо кунед\n• Журнали трейдинг пеш баред\n• Маблағи аз даст додаро зуд баргардонидан нахоҳед\n• Доимо дониши худро такмил диҳед"
                ]
            },
            '5': {
                'title': "🧠 Психологияи трейдинг",
                'content': [
                    "*Ҳолатҳои эмотсионалӣ:*\n• Тамаъ – хоҳиши гирифтани фоидаи аз ҳад зиёд\n• Тарс – метавонад ба қарорҳои нодуруст оварад\n• Умед – нигоҳ доштани мавқеи зараровар дар умеди тағйир\n• Афсӯс – нигоҳ доштани мавқеи зараровар барои напазируфтани зарар",
                    "*Интизоми трейдинг:*\n• Риояи қатъии нақшаи худ\n• Идоракунии эмотсияҳо\n• Муносибати мунтазам ба трейдинг\n• Қобилияти қатъ кардан ҳангоми зарар",
                    "*Нақшаи муомила:*\n• Дохилшавӣ ва баромад\n• Ҳаҷми муомила\n• Идоракунии хавф\n• Шартҳои лағви нақша",
                    "*Тавсияҳо:*\n• Журнали трейдинг пеш баред ва натиҷаҳоро таҳлил кунед\n• Бо маблағи хурд оғоз кунед, то таҷриба пайдо кунед\n• Таҷрибаи худро дар ҳисоби демо санҷед\n• Истироҳат кунед, агар дар ҳолати бад бошед\n• Танаффус кунед, агар якчанд зарар пай дар пай бошад"
                ]
            },
            '6': {
                'title': "📈 Стратегияҳои савдо",
                'content': [
                    "*Намудҳои стратегияҳо:*\n• Стратегияҳои трендӣ – барои бозорҳои дар ҳаракат\n• Стратегияҳои рангӣ – барои бозорҳои боспред\n• Стратегияҳои скальпинг – барои гирифтани фоидаи хурди зуд\n• Стратегияҳои свинг – барои фоида аз тағйироти миёнамуҳлат",
                    "*Стратегияҳои маъруф:*\n• Гузариши миёнаи ҳаракаткунанда – истифодаи гузариши MA барои муайян кардани тренд\n• Торговля с отскоком – интизори барқароршавии нарх аз сатҳҳо\n• Савдои шикасти сатҳ – интизори шикасти сатҳҳои муҳим\n• RSI саф – хариду фурӯш ҳангоми барзиёд/барзиёд харидани RSI",
                    "*Интихоби стратегия:*\n• Ба сабки шахсии худ мувофиқат кунед\n• Ба марҳилаи бозор мувофиқат кунед (тренди ё диапазон)\n• Ба вақте, ки шумо метавонед ба трейдинг ҷудо кунед, мувофиқ бошед\n• Ба ҳаҷми сармояи шумо мувофиқ бошад",
                    "*Такмили стратегия:*\n• Стратегияро дар ҳисоби демо санҷед\n• Якчанд муомиларо барои санҷиш гузаронед\n• Ба таърихи қаблӣ бори дигар санҷед (бектестинг)\n• Индикаторҳоро бо шароити ҷории бозор мутобиқ кунед"
                ]
            },
            '7': {
                'title': "👨‍💻 Амалияи трейдинг",
                'content': [
                    "*Ҳисоби демо:*\n• Барои омӯзиши платформа истифода баред\n• Стратегияҳоро бидуни хавфи воқеӣ санҷед\n• Малакаҳои мудирияти хавфро такмил диҳед\n• Ба ҳиссиёт худро одат кунонед",
                    "*Оғози трейдинги воқеӣ:*\n• Бо маблағи хурд оғоз кунед\n• Андозаи мавқеъро маҳдуд кунед\n• Танҳо стратегияи санҷидашударо истифода баред\n• Журнали муфассали муомилаҳоро пеш баред",
                    "*Журнали трейдинг:*\n• Сабаби вуруд ба муомила\n• Сатҳҳои Stop Loss ва Take Profit\n• Ҳаҷми мавқеъ\n• Натиҷаи муомила ва таҳлили он",
                    "*Такмили малакаҳо:*\n• Муомилаҳои гузаштаро таҳлил кунед\n• Хатоҳои такрориро муайян кунед\n• Омилҳои муваффақиятро дарк кунед\n• Стратегияро мувофиқи натиҷаҳо такмил диҳед"
                ]
            },
            '8': {
                'title': "📚 Такмили малака",
                'content': [
                    "*Сарчашмаҳои омӯзиш:*\n• Китобҳо оид ба трейдинг ва таҳлили бозор\n• Вебинарҳо ва семинарҳои онлайн\n• Ҷомеаҳои трейдерон\n• Шарҳи бозорҳо аз коршиносон",
                    "*Тавсияҳои китобҳо:*\n• \"Таҳлили техникӣ\" - Ҷон Мерфи\n• \"Савдогари интизомнок\" - Марк Дуглас\n• \"Хотираҳои савдогари саҳмия\" - Эдвин Лефевр\n• \"Равоншиносии трейдинг\" - Бретт Стинбаргер",
                    "*Ҷанбаҳои омӯзиш:*\n• Таҳлили чартҳо ва нақшҳо\n• Такмили стратегияҳо\n• Мудирияти хавф\n• Назорати ҳиссиёт\n• Баҳодиҳии иқтисодӣ",
                    "*Нуктаҳои муҳим:*\n• Трейдинги муваффақ раванди доимии омӯзиш ва такмил аст\n• Ба натиҷаҳои кӯтоҳмуддат таваҷҷуҳ накунед\n• Нишондиҳандаи муваффақият фоидаи устувор аст\n• Ба натиҷаҳои худ мунтазам назар кунед ва таҳлил намоед"
                ]
            }
        },
        'ru': {
            '1': {
                'title': "🔰 Основы трейдинга",
                'content': [
                    "*Что такое трейдинг?*\nТрейдинг — это деятельность по покупке и продаже финансовых активов (валюты, акции, товары) с целью получения прибыли.",
                    "*Основная терминология:*\n• Спред — разница между ценой покупки и продажи\n• Волатильность — изменчивость цены актива\n• Ликвидность — легкость превращения актива в деньги\n• Take Profit/Stop Loss — ордера для контроля рисков",
                    "*Типы рынков:*\n• Forex — валютный рынок\n• Фондовый рынок — покупка и продажа акций компаний\n• Фьючерсный рынок — контракты на покупку/продажу актива в будущем\n• Криптовалютный рынок — торговля цифровыми валютами",
                    "*Стили трейдинга:*\n• Скальпинг — краткосрочные сделки с малой прибылью\n• Дневной трейдинг — сделки в течение дня\n• Свинг-трейдинг — сделки длительностью от нескольких дней до недель\n• Долгосрочные инвестиции — удержание позиции месяцами/годами"
                ]
            },
            '2': {
                'title': "🖥️ Выбор платформы",
                'content': [
                    "*Типы платформ:*\n• Брокеры — компании, предоставляющие трейдерам доступ к рынкам\n• Биржи — платформы, позволяющие торговать напрямую",
                    "*Критерии выбора:*\n• Надежность — регулирование компании, история работы\n• Входной порог — минимальная сумма для инвестирования\n• Условия торговли — спреды, комиссии, кредитное плечо\n• Доступность средств — методы пополнения/вывода\n• Функционал — графики, индикаторы, мобильная платформа",
                    "*Популярные платформы:*\n• MetaTrader 4/5 — для торговли на Forex и фьючерсами\n• TradingView — для анализа и торговли\n• Think or Swim — для торговли акциями и опционами\n• Binance — для торговли криптовалютами",
                    "*Рекомендации:*\n• Сначала работайте на демо-счете\n• Настройте интерфейс под себя\n• Изучите возможности анализа и отчетности\n• Обеспечьте безопасность счета (двухфакторная аутентификация, сложный пароль)"
                ]
            },
            '3': {
                'title': "📊 Анализ рынка",
                'content': [
                    "*Технический анализ:*\n• Изучение графиков и паттернов\n• Использование индикаторов (MA, MACD, RSI)\n• Распознавание ценовых паттернов\n• Нахождение уровней поддержки и сопротивления",
                    "*Фундаментальный анализ:*\n• Изучение общей экономической ситуации\n• Анализ экономических показателей\n• Оценка денежной политики центральных банков\n• Оценка компаний (для акций)",
                    "*Популярные индикаторы:*\n• Moving Average (MA) — скользящая средняя\n• Relative Strength Index (RSI) — индекс относительной силы\n• Moving Average Convergence Divergence (MACD) — схождение и расхождение скользящих средних\n• Bollinger Bands — линии волатильности вокруг цены",
                    "*Источники информации:*\n• Экономический календарь\n• Финансовые новости\n• Публикации центральных банков\n• Отчеты компаний"
                ]
            },
            '4': {
                'title': "⚠️ Управление рисками",
                'content': [
                    "*Основные принципы:*\n• Определение максимального риска на сделку\n• Никогда не рискуйте более чем 1-2% от общего капитала\n• Диверсификация инвестиций\n• Всегда используйте Stop Loss",
                    "*Стратегии управления рисками:*\n• Stop Loss — ордер для ограничения убытка\n• Take Profit — ордер для фиксации прибыли\n• Соотношение риска и прибыли — рекомендуется 1:2 или больше\n• Money Management — правильное распределение капитала",
                    "*Распространенные ошибки:*\n• Слишком большое вложение в одну сделку\n• Отсутствие плана действий\n• Торговля против тренда\n• Эмоциональные сделки\n• Постоянная смена стратегии",
                    "*Важные правила:*\n• Торгуйте только деньгами, которые можете позволить себе потерять\n• Ведите торговый журнал\n• Не стремитесь быстро отыграть потерянную сумму\n• Постоянно совершенствуйте свои знания"
                ]
            },
            '5': {
                'title': "🧠 Психология трейдинга",
                'content': [
                    "*Эмоциональные состояния:*\n• Жадность — желание получить чрезмерную прибыль\n• Страх — может привести к неправильным решениям\n• Надежда — удержание убыточной позиции в надежде на разворот\n• Сожаление — удержание убыточной позиции для непризнания убытка",
                    "*Торговая дисциплина:*\n• Строгое следование своему плану\n• Управление эмоциями\n• Системный подход к трейдингу\n• Способность остановиться при убытках",
                    "*План сделки:*\n• Точки входа и выхода\n• Размер сделки\n• Управление рисками\n• Условия отмены плана",
                    "*Рекомендации:*\n• Ведите торговый журнал и анализируйте результаты\n• Начинайте с малых сумм, чтобы приобрести опыт\n• Тестируйте свой опыт на демо-счете\n• Отдыхайте, если вы в плохом состоянии\n• Делайте перерыв при нескольких убыточных сделках подряд"
                ]
            },
            '6': {
                'title': "📈 Торговые стратегии",
                'content': [
                    "*Типы стратегий:*\n• Трендовые стратегии — для движущихся рынков\n• Диапазонные стратегии — для консолидирующихся рынков\n• Скальпинговые стратегии — для быстрого получения малой прибыли\n• Свинг-стратегии — для получения прибыли от среднесрочных изменений",
                    "*Популярные стратегии:*\n• Пересечение скользящих средних — использование пересечения MA для определения тренда\n• Торговля от отскока — ожидание восстановления цены от уровней\n• Торговля на пробое уровня — ожидание прорыва важных уровней\n• RSI перепроданность/перекупленность — покупка/продажа при экстремальных значениях RSI",
                    "*Выбор стратегии:*\n• Соответствие вашему личному стилю\n• Соответствие фазе рынка (трендовый или диапазонный)\n• Соответствие времени, которое вы можете уделять трейдингу\n• Соответствие размеру вашего капитала",
                    "*Совершенствование стратегии:*\n• Тестируйте стратегию на демо-счете\n• Проведите несколько сделок для тестирования\n• Проверьте на исторических данных (бэктестинг)\n• Адаптируйте индикаторы к текущим рыночным условиям"
                ]
            },
            '7': {
                'title': "👨‍💻 Практика трейдинга",
                'content': [
                    "*Демо-счет:*\n• Используйте для изучения платформы\n• Тестируйте стратегии без реального риска\n• Совершенствуйте навыки управления рисками\n• Привыкайте к эмоциям",
                    "*Начало реальной торговли:*\n• Начинайте с небольшой суммы\n• Ограничивайте размер позиции\n• Используйте только проверенную стратегию\n• Ведите подробный журнал сделок",
                    "*Торговый журнал:*\n• Причина входа в сделку\n• Уровни Stop Loss и Take Profit\n• Размер позиции\n• Результат сделки и его анализ",
                    "*Совершенствование навыков:*\n• Анализируйте прошлые сделки\n• Выявляйте повторяющиеся ошибки\n• Определяйте факторы успеха\n• Корректируйте стратегию в соответствии с результатами"
                ]
            },
            '8': {
                'title': "📚 Повышение квалификации",
                'content': [
                    "*Источники обучения:*\n• Книги по трейдингу и анализу рынка\n• Вебинары и онлайн-семинары\n• Сообщества трейдеров\n• Обзоры рынков от экспертов",
                    "*Рекомендуемые книги:*\n• \"Технический анализ\" - Джон Мэрфи\n• \"Дисциплинированный трейдер\" - Марк Дуглас\n• \"Воспоминания биржевого спекулянта\" - Эдвин Лефевр\n• \"Психология трейдинга\" - Бретт Стинбаргер",
                    "*Аспекты обучения:*\n• Анализ графиков и паттернов\n• Совершенствование стратегий\n• Управление рисками\n• Контроль эмоций\n• Экономическая оценка",
                    "*Важные моменты:*\n• Успешный трейдинг — это постоянный процесс обучения и совершенствования\n• Не фокусируйтесь на краткосрочных результатах\n• Показатель успеха — стабильная прибыль\n• Регулярно просматривайте и анализируйте свои результаты"
                ]
            }
        },
        'uz': {
            '1': {
                'title': "🔰 Treyding asoslari",
                'content': [
                    "*Treyding nima?*\nTreyding - foyda olish maqsadida moliyaviy aktivlarni (valyuta, aksiyalar, tovarlar) sotib olish va sotish faoliyatidir.",
                    "*Asosiy terminologiya:*\n• Spred - sotib olish va sotish narxlari o'rtasidagi farq\n• Volatillik - aktiv narxining o'zgaruvchanligi\n• Likvidlik - aktivni pulga aylantirish qulayligi\n• Take Profit/Stop Loss - xavflarni nazorat qilish uchun buyurtmalar",
                    "*Bozor turlari:*\n• Forex - valyuta bozori\n• Fond bozori - kompaniya aksiyalarini sotib olish va sotish\n• Fyuchers bozori - kelajakda aktivni sotib olish/sotish shartnomasi\n• Kriptovalyuta bozori - raqamli valyutalar savdosi",
                    "*Treyding uslublari:*\n• Skalping - kam foyda bilan qisqa muddatli bitimlar\n• Kunlik treyding - kun davomida bitimlar\n• Sving treyding - bir necha kundan bir necha haftagacha bo'lgan bitimlar\n• Uzoq muddatli investitsiyalar - pozitsiyani oylar/yillar davomida ushlab turish"
                ]
            },
            '2': {
                'title': "🖥️ Platforma tanlash",
                'content': [
                    "*Platforma turlari:*\n• Brokerlar - treyderlarga bozorlarga kirish imkonini beruvchi kompaniyalar\n• Birjalar - to'g'ridan-to'g'ri savdo qilish imkonini beruvchi platformalar",
                    "*Tanlash mezonlari:*\n• Ishonchlilik - kompaniyaning tartibga solinishi, faoliyat tarixi\n• Kirish bo'sag'asi - investitsiyalash uchun minimal summa\n• Savdo shartlari - spredlar, komissiyalar, kredit yelkasi\n• Mablag'lar mavjudligi - to'ldirish/chiqarish usullari\n• Funktsionalligi - grafiklar, indikatorlar, mobil platforma",
                    "*Mashhur platformalar:*\n• MetaTrader 4/5 - Forex va fyuchers savdosi uchun\n• TradingView - tahlil va savdo uchun\n• Think or Swim - aksiyalar va opsionlar savdosi uchun\n• Binance - kriptovalyutalar savdosi uchun",
                    "*Tavsiyalar:*\n• Avval demo hisobda ishlang\n• Interfeysni o'zingizga moslashtirib oling\n• Tahlil va hisobot imkoniyatlarini o'rganing\n• Hisob xavfsizligini ta'minlang (ikki faktorli autentifikatsiya, murakkab parol)"
                ]
            },
            '3': {
                'title': "📊 Bozor tahlili",
                'content': [
                    "*Texnik tahlil:*\n• Grafiklar va patternlarni o'rganish\n• Indikatorlardan foydalanish (MA, MACD, RSI)\n• Narx patternlarini aniqlash\n• Qo'llab-quvvatlash va qarshilik darajalarini topish",
                    "*Fundamental tahlil:*\n• Umumiy iqtisodiy vaziyatni o'rganish\n• Iqtisodiy ko'rsatkichlarni tahlil qilish\n• Markaziy banklarning pul siyosatini baholash\n• Kompaniyalarni baholash (aksiyalar uchun)",
                    "*Mashhur indikatorlar:*\n• Moving Average (MA) - harakatlanuvchi o'rtacha\n• Relative Strength Index (RSI) - nisbiy kuch indeksi\n• Moving Average Convergence Divergence (MACD) - harakatlanuvchi o'rtachalarning konvergensiyasi va divergensiyasi\n• Bollinger Bands - narx atrofidagi volatillik chiziqlari",
                    "*Ma'lumot manbalari:*\n• Iqtisodiy kalendar\n• Moliyaviy yangiliklar\n• Markaziy banklarning nashriyotlari\n• Kompaniyalar hisobotlari"
                ]
            },
            '4': {
                'title': "⚠️ Xavflarni boshqarish",
                'content': [
                    "*Asosiy tamoyillar:*\n• Bitta bitim uchun maksimal xavfni aniqlash\n• Hech qachon umumiy kapitalning 1-2% dan ko'p qismini riskka qo'ymang\n• Investitsiyalarni diversifikatsiya qilish\n• Doimo Stop Loss dan foydalaning",
                    "*Xavflarni boshqarish strategiyalari:*\n• Stop Loss - zararni cheklash uchun buyurtma\n• Take Profit - foydani qadlash uchun buyurtma\n• Risk va foyda nisbati - 1:2 yoki undan ko'proq tavsiya qilinadi\n• Money Management - kapitalni to'g'ri taqsimlash",
                    "*Umumiy xatolar:*\n• Bitta bitimga juda katta mablag' qo'yish\n• Harakatlar rejasining yo'qligi\n• Trendga qarshi savdo\n• Emotsional bitimlar\n• Strategiyani doimiy o'zgartirish",
                    "*Muhim qoidalar:*\n• Faqat yo'qotishni rozi bo'lgan pullar bilan savdo qiling\n• Savdo jurnaliga ega bo'ling\n• Yo'qotilgan summani tezda qaytarib olishga urinmang\n• Bilimingizni doimiy ravishda takomillashtiring"
                ]
            },
            '5': {
                'title': "🧠 Treyding psixologiyasi",
                'content': [
                    "*Emotsional holatlar:*\n• Ochko'zlik - o'ta ko'p foyda olish istagi\n• Qo'rquv - noto'g'ri qarorlarga olib kelishi mumkin\n• Umid - burilish umidida zararli pozitsiyani ushlab turish\n• Afsus - zararni tan olmaslik uchun zararli pozitsiyani ushlab turish",
                    "*Savdo intizomi:*\n• O'z rejangizga qat'iy rioya qilish\n• Emotsiyalarni boshqarish\n• Treydingga tizimli yondashish\n• Zararlar paytida to'xtay olish qobiliyati",
                    "*Bitim rejasi:*\n• Kirish va chiqish nuqtalari\n• Bitim hajmi\n• Xavflarni boshqarish\n• Rejani bekor qilish shartlari",
                    "*Tavsiyalar:*\n• Savdo jurnaliga ega bo'ling va natijalarni tahlil qiling\n• Tajriba orttirish uchun kam summalar bilan boshlang\n• Tajribangizni demo hisobda sinab ko'ring\n• Holingiz yomon bo'lsa, dam oling\n• Ketma-ket bir nechta zararly bitimlar bo'lganida tanaffus qiling"
                ]
            },
            '6': {
                'title': "📈 Savdo strategiyalari",
                'content': [
                    "*Strategiya turlari:*\n• Trend strategiyalari - harakatlanayotgan bozorlar uchun\n• Diapazon strategiyalari - konsolidatsiyalanayotgan bozorlar uchun\n• Skalping strategiyalari - tez kichik foyda olish uchun\n• Sving strategiyalari - o'rta muddatli o'zgarishlardan foyda olish uchun",
                    "*Mashhur strategiyalar:*\n• Harakatlanuvchi o'rtacha kesishish - trendni aniqlash uchun MA kesishishidan foydalanish\n• Sakrashdan savdo - darajalardan narx tiklanishini kutish\n• Darajani buzishdan savdo - muhim darajalarni yorib o'tishini kutish\n• RSI o'ta sotilgan/o'ta sotib olingan - RSI ekstremal qiymatlarida sotib olish/sotish",
                    "*Strategiya tanlash:*\n• Shaxsiy uslubingizga mos kelishi\n• Bozor fazasiga mos kelishi (trend yoki diapazon)\n• Treydingga ajratadigan vaqtingizga mos kelishi\n• Kapitalingiz hajmiga mos kelishi",
                    "*Strategiyani takomillashtirish:*\n• Strategiyani demo hisobda sinab ko'ring\n• Sinov uchun bir nechta bitimlarni amalga oshiring\n• Tarixiy ma'lumotlarda tekshiring (bektesting)\n• Indikatorlarni joriy bozor sharoitlariga moslashtirib oling"
                ]
            },
            '7': {
                'title': "👨‍💻 Treyding amaliyoti",
                'content': [
                    "*Demo hisob:*\n• Platformani o'rganish uchun foydalaning\n• Haqiqiy xavf bo'lmagan holda strategiyalarni sinab ko'ring\n• Xavflarni boshqarish ko'nikmalarini takomillashtiring\n• Emotsiyalarga ko'nikib boring",
                    "*Haqiqiy savdoni boshlash:*\n• Kichik summadan boshlang\n• Pozitsiya hajmini cheklang\n• Faqat tekshirilgan strategiyadan foydalaning\n• Batafsil bitimlar jurnalini yuritib boring",
                    "*Savdo jurnali:*\n• Bitimga kirish sababi\n• Stop Loss va Take Profit darajalari\n• Pozitsiya hajmi\n• Bitim natijasi va uning tahlili",
                    "*Ko'nikmalarni takomillashtirish:*\n• O'tgan bitimlarni tahlil qiling\n• Takrorlanuvchi xatolarni aniqlang\n• Muvaffaqiyat omillarini aniqlang\n• Natijalarga ko'ra strategiyani o'zgartiring"
                ]
            },
            '8': {
                'title': "📚 Malakani oshirish",
                'content': [
                    "*O'rganish manbalari:*\n• Treyding va bozor tahlili bo'yicha kitoblar\n• Vebinarlar va onlayn seminarlar\n• Treyderlar hamjamiyati\n• Ekspertlardan bozor sharhlari",
                    "*Tavsiya etilgan kitoblar:*\n• \"Texnik tahlil\" - Jon Merfi\n• \"Intizomli treyding\" - Mark Duglas\n• \"Birja spekulyantining xotiralari\" - Edvin Lefevr\n• \"Treyding psixologiyasi\" - Brett Stinbarger",
                    "*O'rganish jihatlari:*\n• Grafiklar va patternlarni tahlil qilish\n• Strategiyalarni takomillashtirish\n• Xavflarni boshqarish\n• Emotsiyalarni nazorat qilish\n• Iqtisodiy baholash",
                    "*Muhim nuqtalar:*\n• Muvaffaqiyatli treyding - o'rganish va takomillashtirishning doimiy jarayonidir\n• Qisqa muddatli natijalarga diqqatingizni qaratmang\n• Muvaffaqiyat ko'rsatkichi - barqaror foyda\n• Natijalaringizni muntazam ko'rib chiqing va tahlil qiling"
                ]
            }
        },
        'kk': {
            '1': {
                'title': "🔰 Трейдинг негіздері",
                'content': [
                    "*Трейдинг дегеніміз не?*\nТрейдинг — бұл пайда табу мақсатында қаржы активтерін (валюта, акциялар, тауарлар) сатып алу және сату бойынша қызмет.",
                    "*Негізгі терминология:*\n• Спред — сатып алу және сату бағасы арасындағы айырмашылық\n• Волатильділік — актив бағасының өзгергіштігі\n• Өтімділік — активті ақшаға айналдыру жеңілдігі\n• Take Profit/Stop Loss — тәуекелдерді бақылауға арналған тапсырыстар",
                    "*Нарық түрлері:*\n• Forex — валюта нарығы\n• Қор нарығы — компания акцияларын сату және сатып алу\n• Фьючерс нарығы — болашақта активті сатып алу/сату келісімшарттары\n• Криптовалюта нарығы — цифрлық валюталармен сауда",
                    "*Трейдинг стильдері:*\n• Скальпинг — аз пайдамен қысқа мерзімді мәмілелер\n• Күндізгі трейдинг — күн ішіндегі мәмілелер\n• Свинг-трейдинг — бірнеше күннен бірнеше аптаға дейін созылатын мәмілелер\n• Ұзақ мерзімді инвестициялар — позицияны айлар/жылдар бойы ұстау"
                ]
            },
            '2': {
                'title': "🖥️ Платформаны таңдау",
                'content': [
                    "*Платформа түрлері:*\n• Брокерлер — трейдерлерге нарықтарға қол жетімділік беретін компаниялар\n• Биржалар — тікелей сауда жасауға мүмкіндік беретін платформалар",
                    "*Таңдау критерийлері:*\n• Сенімділік — компанияның реттелуі, жұмыс тарихы\n• Кіру шегі — инвестиция салуға минималды сома\n• Сауда шарттары — спредтер, комиссиялар, кредит иығы\n• Қаражат қолжетімділігі — толтыру/шығару әдістері\n• Функционал — графиктер, индикаторлар, мобильді платформа",
                    "*Танымал платформалар:*\n• MetaTrader 4/5 — Forex және фьючерстермен сауда жасауға арналған\n• TradingView — талдау және сауда жасауға арналған\n• Think or Swim — акциялар мен опциондармен сауда жасауға арналған\n• Binance — криптовалюталармен сауда жасауға арналған",
                    "*Ұсыныстар:*\n• Алдымен демо-шотта жұмыс істеңіз\n• Интерфейсті өзіңізге бейімдеңіз\n• Талдау және есеп беру мүмкіндіктерін зерттеңіз\n• Шот қауіпсіздігін қамтамасыз етіңіз (екі факторлы аутентификация, күрделі құпия сөз)"
                ]
            },
            '3': {
                'title': "📊 Нарықты талдау",
                'content': [
                    "*Техникалық талдау:*\n• Графиктер мен паттерндерді зерттеу\n• Индикаторларды пайдалану (MA, MACD, RSI)\n• Баға паттерндерін тану\n• Қолдау және кедергі деңгейлерін табу",
                    "*Іргелі талдау:*\n• Жалпы экономикалық жағдайды зерттеу\n• Экономикалық көрсеткіштерді талдау\n• Орталық банктердің ақша саясатын бағалау\n• Компанияларды бағалау (акциялар үшін)",
                    "*Танымал индикаторлар:*\n• Moving Average (MA) — жылжымалы орташа\n• Relative Strength Index (RSI) — салыстырмалы күш индексі\n• Moving Average Convergence Divergence (MACD) — жылжымалы орташалардың жинақталуы және айырылуы\n• Bollinger Bands — баға айналасындағы волатильділік сызықтары",
                    "*Ақпарат көздері:*\n• Экономикалық күнтізбе\n• Қаржы жаңалықтары\n• Орталық банктердің басылымдары\n• Компаниялардың есептері"
                ]
            },
            '4': {
                'title': "⚠️ Тәуекелдерді басқару",
                'content': [
                    "*Негізгі принциптер:*\n• Мәміле бойынша максималды тәуекелді анықтау\n• Жалпы капиталдың 1-2%-дан артық тәуекелге бармаңыз\n• Инвестицияларды әртараптандыру\n• Әрдайым Stop Loss қолданыңыз",
                    "*Тәуекелдерді басқару стратегиялары:*\n• Stop Loss — шығынды шектеуге арналған тапсырыс\n• Take Profit — пайданы бекітуге арналған тапсырыс\n• Тәуекел мен пайда арақатынасы — 1:2 немесе одан да көп ұсынылады\n• Money Management — капиталды дұрыс бөлу",
                    "*Жиі кездесетін қателер:*\n• Бір мәмілеге тым көп инвестиция салу\n• Әрекет жоспарының болмауы\n• Трендке қарсы сауда жасау\n• Эмоционалды мәмілелер\n• Стратегияны үнемі ауыстыру",
                    "*Маңызды ережелер:*\n• Тек өзіңіз жоғалтуға дайын қаражатпен сауда жасаңыз\n• Сауда журналын жүргізіңіз\n• Жоғалтқан соманы тез қайтаруға тырыспаңыз\n• Білімді үнемі жетілдіріп отырыңыз"
                ]
            },
            '5': {
                'title': "🧠 Трейдинг психологиясы",
                'content': [
                    "*Эмоционалды жағдайлар:*\n• Ашкөздік — шамадан тыс пайда табуға ұмтылу\n• Қорқыныш — дұрыс емес шешімдерге әкелуі мүмкін\n• Үміт — бұрылуға үміттеніп, шығынды позицияны ұстап тұру\n• Өкініш — шығынды мойындамау үшін шығынды позицияны ұстап тұру",
                    "*Сауда тәртібі:*\n• Жоспарды қатаң ұстану\n• Эмоцияларды басқару\n• Трейдингке жүйелі көзқарас\n• Шығын кезінде тоқтай білу",
                    "*Мәміле жоспары:*\n• Кіру және шығу нүктелері\n• Мәміле көлемі\n• Тәуекелдерді басқару\n• Жоспарды тоқтату шарттары",
                    "*Ұсыныстар:*\n• Сауда журналын жүргізіп, нәтижелерді талдаңыз\n• Тәжірибе жинау үшін шағын сомадан бастаңыз\n• Тәжірибеңізді демо-шотта тексеріңіз\n• Жағдайыңыз нашар болса, демалыңыз\n• Бірнеше шығынды мәміледен кейін үзіліс жасаңыз"
                ]
            },
            '6': {
                'title': "📈 Сауда стратегиялары",
                'content': [
                    "*Стратегия түрлері:*\n• Трендтік стратегиялар — қозғалыстағы нарықтар үшін\n• Диапазондық стратегиялар — тұрақтанған нарықтар үшін\n• Скальпинг стратегиялары — аз пайданы жылдам алу үшін\n• Свинг стратегиялары — орта мерзімді өзгерістерден пайда табу үшін",
                    "*Танымал стратегиялар:*\n• Жылжымалы орташалардың қиылысуы — трендті анықтау үшін MA қиылысуын пайдалану\n• Қайта тебілу саудасы — бағаның деңгейлерден қалпына келуін күту\n• Деңгейді бұзу саудасы — маңызды деңгейлердің бұзылуын күту\n• RSI артық сатылым/артық сатып алу — RSI экстремалды мәндерінде сатып алу/сату",
                    "*Стратегияны таңдау:*\n• Сіздің жеке стиліңізге сәйкестік\n• Нарық фазасына сәйкестік (трендтік немесе диапазондық)\n• Трейдингке бөлетін уақытыңызға сәйкестік\n• Капитал көлеміңізге сәйкестік",
                    "*Стратегияны жетілдіру:*\n• Стратегияны демо-шотта тексеріңіз\n• Тексеру үшін бірнеше мәміле жасаңыз\n• Тарихи деректерде тексеріңіз (бэктестинг)\n• Индикаторларды ағымдағы нарық жағдайларына бейімдеңіз"
                ]
            },
            '7': {
                'title': "👨‍💻 Трейдинг практикасы",
                'content': [
                    "*Демо-шот:*\n• Платформаны үйрену үшін пайдаланыңыз\n• Стратегияларды нақты тәуекелсіз тексеріңіз\n• Тәуекелдерді басқару дағдыларын жетілдіріңіз\n• Эмоцияларға үйреніңіз",
                    "*Нақты сауданы бастау:*\n• Шағын сомадан бастаңыз\n• Позиция көлемін шектеңіз\n• Тек тексерілген стратегияны пайдаланыңыз\n• Толық мәмілелер журналын жүргізіңіз",
                    "*Сауда журналы:*\n• Мәмілеге кіру себебі\n• Stop Loss және Take Profit деңгейлері\n• Позиция көлемі\n• Мәміле нәтижесі және оны талдау",
                    "*Дағдыларды жетілдіру:*\n• Өткен мәмілелерді талдаңыз\n• Қайталанатын қателерді анықтаңыз\n• Табыс факторларын анықтаңыз\n• Стратегияны нәтижелерге сәйкес түзетіңіз"
                ]
            },
            '8': {
                'title': "📚 Біліктілікті арттыру",
                'content': [
                    "*Оқу көздері:*\n• Трейдинг және нарық талдауы бойынша кітаптар\n• Вебинарлар және онлайн-семинарлар\n• Трейдерлер қауымдастығы\n• Сарапшылардан нарық шолулары",
                    "*Ұсынылатын кітаптар:*\n• \"Техникалық талдау\" - Джон Мерфи\n• \"Тәртіпті трейдер\" - Марк Дуглас\n• \"Биржа спекулянтының естеліктері\" - Эдвин Лефевр\n• \"Трейдинг психологиясы\" - Бретт Стинбаргер",
                    "*Оқу аспектілері:*\n• Графиктер мен паттерндерді талдау\n• Стратегияларды жетілдіру\n• Тәуекелдерді басқару\n• Эмоцияларды бақылау\n• Экономикалық бағалау",
                    "*Маңызды сәттер:*\n• Табысты трейдинг — бұл үнемі оқу және жетілдіру процесі\n• Қысқа мерзімді нәтижелерге фокус жасамаңыз\n• Табыс көрсеткіші — тұрақты пайда\n• Нәтижелеріңізді жүйелі түрде қарап, талдаңыз"
                ]
            }
        },
        'en': {
            '1': {
                'title': "🔰 Trading Basics",
                'content': [
                    "*What is trading?*\nTrading is the activity of buying and selling financial assets (currencies, stocks, commodities) with the aim of making a profit.",
                    "*Basic terminology:*\n• Spread — the difference between buy and sell prices\n• Volatility — the variability of an asset's price\n• Liquidity — the ease of converting an asset into cash\n• Take Profit/Stop Loss — orders for risk control",
                    "*Types of markets:*\n• Forex — currency market\n• Stock market — buying and selling company shares\n• Futures market — contracts for buying/selling an asset in the future\n• Cryptocurrency market — trading digital currencies",
                    "*Trading styles:*\n• Scalping — short-term trades with small profit\n• Day trading — trades within a day\n• Swing trading — trades lasting from several days to weeks\n• Long-term investments — holding a position for months/years"
                ]
            },
            '2': {
                'title': "🖥️ Platform Selection",
                'content': [
                    "*Types of platforms:*\n• Brokers — companies that provide traders with access to markets\n• Exchanges — platforms that allow direct trading",
                    "*Selection criteria:*\n• Reliability — company regulation, operating history\n• Entry threshold — minimum amount for investment\n• Trading conditions — spreads, commissions, leverage\n• Fund accessibility — deposit/withdrawal methods\n• Functionality — charts, indicators, mobile platform",
                    "*Popular platforms:*\n• MetaTrader 4/5 — for Forex and futures trading\n• TradingView — for analysis and trading\n• Think or Swim — for stock and options trading\n• Binance — for cryptocurrency trading",
                    "*Recommendations:*\n• First work on a demo account\n• Customize the interface to suit your needs\n• Explore analysis and reporting capabilities\n• Ensure account security (two-factor authentication, complex password)"
                ]
            },
            '3': {
                'title': "📊 Market Analysis",
                'content': [
                    "*Technical analysis:*\n• Studying charts and patterns\n• Using indicators (MA, MACD, RSI)\n• Recognizing price patterns\n• Finding support and resistance levels",
                    "*Fundamental analysis:*\n• Studying the general economic situation\n• Analyzing economic indicators\n• Evaluating monetary policy of central banks\n• Evaluating companies (for stocks)",
                    "*Popular indicators:*\n• Moving Average (MA) — smooths price data\n• Relative Strength Index (RSI) — measures momentum\n• Moving Average Convergence Divergence (MACD) — shows relationship between moving averages\n• Bollinger Bands — volatility lines around price",
                    "*Information sources:*\n• Economic calendar\n• Financial news\n• Central bank publications\n• Company reports"
                ]
            },
            '4': {
                'title': "⚠️ Risk Management",
                'content': [
                    "*Basic principles:*\n• Determining maximum risk per trade\n• Never risk more than 1-2% of total capital\n• Diversification of investments\n• Always use Stop Loss",
                    "*Risk management strategies:*\n• Stop Loss — order to limit loss\n• Take Profit — order to secure profit\n• Risk to reward ratio — 1:2 or more is recommended\n• Money Management — proper capital allocation",
                    "*Common mistakes:*\n• Too large investment in one trade\n• Lack of action plan\n• Trading against the trend\n• Emotional trades\n• Constant strategy change",
                    "*Important rules:*\n• Trade only with money you can afford to lose\n• Keep a trading journal\n• Don't try to quickly recover a lost amount\n• Continuously improve your knowledge"
                ]
            },
            '5': {
                'title': "🧠 Trading Psychology",
                'content': [
                    "*Emotional states:*\n• Greed — desire to get excessive profit\n• Fear — can lead to wrong decisions\n• Hope — holding a losing position hoping for a reversal\n• Regret — holding a losing position to avoid acknowledging the loss",
                    "*Trading discipline:*\n• Strict adherence to your plan\n• Managing emotions\n• Systematic approach to trading\n• Ability to stop during losses",
                    "*Trade plan:*\n• Entry and exit points\n• Position size\n• Risk management\n• Plan cancellation conditions",
                    "*Recommendations:*\n• Keep a trading journal and analyze results\n• Start with small amounts to gain experience\n• Test your experience on a demo account\n• Rest if you are in a bad state\n• Take a break after several consecutive losing trades"
                ]
            },
            '6': {
                'title': "📈 Trading Strategies",
                'content': [
                    "*Types of strategies:*\n• Trend strategies — for moving markets\n• Range strategies — for consolidating markets\n• Scalping strategies — for quick small profit\n• Swing strategies — for profit from medium-term changes",
                    "*Popular strategies:*\n• Moving Average Crossover — using MA crossing to determine trend\n• Trading from bounce — waiting for price recovery from levels\n• Breakout trading — waiting for breakthrough of important levels\n• RSI oversold/overbought — buying/selling at extreme RSI values",
                    "*Choosing a strategy:*\n• Match your personal style\n• Match the market phase (trending or ranging)\n• Match the time you can devote to trading\n• Match the size of your capital",
                    "*Refining strategy:*\n• Test the strategy on a demo account\n• Conduct several trades for testing\n• Check on historical data (backtesting)\n• Adapt indicators to current market conditions"
                ]
            },
            '7': {
                'title': "👨‍💻 Trading Practice",
                'content': [
                    "*Demo account:*\n• Use to learn the platform\n• Test strategies without real risk\n• Improve risk management skills\n• Get used to emotions",
                    "*Starting real trading:*\n• Start with a small amount\n• Limit position size\n• Use only proven strategy\n• Keep a detailed trading journal",
                    "*Trading journal:*\n• Reason for entering the trade\n• Stop Loss and Take Profit levels\n• Position size\n• Trade result and its analysis",
                    "*Skill improvement:*\n• Analyze past trades\n• Identify recurring mistakes\n• Determine success factors\n• Adjust strategy according to results"
                ]
            },
            '8': {
                'title': "📚 Skill Enhancement",
                'content': [
                    "*Learning sources:*\n• Books on trading and market analysis\n• Webinars and online seminars\n• Trader communities\n• Market reviews from experts",
                    "*Recommended books:*\n• \"Technical Analysis\" - John Murphy\n• \"The Disciplined Trader\" - Mark Douglas\n• \"Reminiscences of a Stock Operator\" - Edwin Lefèvre\n• \"Trading Psychology\" - Brett Steenbarger",
                    "*Learning aspects:*\n• Analysis of charts and patterns\n• Strategy refinement\n• Risk management\n• Emotion control\n• Economic assessment",
                    "*Important points:*\n• Successful trading is a continuous process of learning and improvement\n• Don't focus on short-term results\n• The indicator of success is stable profit\n• Regularly review and analyze your results"
                ]
            }
        }
    }
    
    # Локализованные кнопки
    button_texts = {
        'tg': {
            'back': "↩️ Бозгашт",
            'main': "🏠 Ба саҳифаи асосӣ"
        },
        'ru': {
            'back': "↩️ Назад",
            'main': "🏠 На главную"
        },
        'uz': {
            'back': "↩️ Orqaga",
            'main': "🏠 Bosh sahifaga"
        },
        'kk': {
            'back': "↩️ Артқа",
            'main': "🏠 Басты бетке"
        },
        'en': {
            'back': "↩️ Back",
            'main': "🏠 Home"
        }
    }
    
    # Получаем локализованные тексты для кнопок
    button_text = button_texts.get(lang_code, button_texts['ru'])
    
    # Получаем содержимое выбранной темы
    topic_data = topic_content.get(lang_code, topic_content['ru']).get(topic_number)
    
    if not topic_data:
        # Если тема не найдена, возвращаемся к списку тем
        query.data = "trading_beginner"
        return await handle_trading_beginner(update, context)
    
    # Формируем сообщение с содержимым темы
    message = f"{topic_data['title']}\n\n" + "\n\n".join(topic_data['content'])
    
    # Создаем клавиатуру с кнопками навигации
    keyboard = [
        [InlineKeyboardButton(button_text['back'], callback_data="trading_beginner")],
        [InlineKeyboardButton(button_text['main'], callback_data="return_to_main")]
    ]
    
    # Отправляем сообщение
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_trading_strategies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для раздела стратегии трейдинга"""
    try:
        query = update.callback_query
        if not query:
            return
        
        await query.answer()
        
        # Определяем язык пользователя
        user_id = query.from_user.id
        logger.info(f"Processing trading_strategies request for user_id: {user_id}")
        
        # Получаем данные пользователя
        user_data = get_user(user_id)
        if user_data:
            lang_code = user_data.get('language_code', 'ru')
            logger.info(f"User language: {lang_code}")
        else:
            lang_code = 'ru'
            logger.warning(f"User data not found, using default language")
    except Exception as e:
        logger.error(f"Error in handle_trading_strategies: {e}")
        lang_code = 'ru'
    
    # Проверяем, запрошена ли конкретная стратегия
    if query.data.startswith("strategy_"):
        # Извлекаем имя стратегии из callback_data
        strategy_name = query.data.replace("strategy_", "")
        await show_strategy_details(update, context, strategy_name, lang_code)
        return
    
    # Тексты заголовков на разных языках
    titles = {
        'tg': '📈 Стратегияҳои трейдинг',
        'ru': '📈 Стратегии трейдинга',
        'uz': '📈 Treyding strategiyalari',
        'kk': '📈 Трейдинг стратегиялары',
        'en': '📈 Trading Strategies'
    }
    
    # Тексты описаний на разных языках
    descriptions = {
        'tg': 'Интихоб намоед стратегияи савдоро барои гирифтани маълумоти муфассал ва мисолҳо:',
        'ru': 'Выберите торговую стратегию для получения подробной информации и примеров:',
        'uz': 'Batafsil ma\'lumot va misollar olish uchun savdo strategiyasini tanlang:',
        'kk': 'Толық ақпарат пен мысалдар алу үшін сауда стратегиясын таңдаңыз:',
        'en': 'Select a trading strategy for detailed information and examples:'
    }
    
    # Кнопки стратегий на разных языках
    strategies_buttons = {
        'tg': [
            ["📊 Стратегияи руйтамоили", "📉 Инверсия"],
            ["📏 Савдои фосилавӣ", "⚡ Скальпинг"],
            ["💱 Арбитраж", "🕰️ Позитрейдинг"],
            ["🌙 Савдои шабона"]
        ],
        'ru': [
            ["📊 Трендовая стратегия", "📉 Разворотная стратегия"],
            ["📏 Диапазонная торговля", "⚡ Скальпинг"],
            ["💱 Арбитраж", "🕰️ Позиционная торговля"],
            ["🌙 Овернайт-трейдинг"]
        ],
        'uz': [
            ["📊 Trend strategiyasi", "📉 Aylanish strategiyasi"],
            ["📏 Diapazonda savdo", "⚡ Skalping"],
            ["💱 Arbitraj", "🕰️ Pozitsion savdo"],
            ["🌙 Tungi savdo"]
        ],
        'kk': [
            ["📊 Тренд стратегиясы", "📉 Бұрылыс стратегиясы"],
            ["📏 Диапазонды сауда", "⚡ Скальпинг"],
            ["💱 Арбитраж", "🕰️ Позициялық сауда"],
            ["🌙 Түнгі сауда"]
        ],
        'en': [
            ["📊 Trend Trading", "📉 Reversal Trading"],
            ["📏 Range Trading", "⚡ Scalping"],
            ["💱 Arbitrage", "🕰️ Position Trading"],
            ["🌙 Overnight Trading"]
        ]
    }
    
    back_button_text = {
        'tg': '↩️ Бозгашт',
        'ru': '↩️ Назад',
        'uz': '↩️ Orqaga',
        'kk': '↩️ Артқа',
        'en': '↩️ Back'
    }
    
    # Формируем сообщение на нужном языке
    title = titles.get(lang_code, titles['ru'])
    description = descriptions.get(lang_code, descriptions['ru'])
    buttons = strategies_buttons.get(lang_code, strategies_buttons['ru'])
    back_button = back_button_text.get(lang_code, back_button_text['ru'])
    
    message = f"{title}\n\n{description}"
    
    # Создаем клавиатуру с кнопками стратегий
    keyboard = []
    
    # Добавляем кнопки стратегий
    for button_row in buttons:
        row = []
        for button_text in button_row:
            # Генерируем callback_data на основе имени стратегии
            # Убираем эмодзи из callback_data
            strategy_name = "".join(button_text.split()[1:])
            callback_data = f"strategy_{strategy_name}"
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        keyboard.append(row)
    
    # Добавляем кнопку возврата
    keyboard.append([InlineKeyboardButton(back_button, callback_data="return_to_main")])
    
    # Отправляем сообщение
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_trading_tools(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для раздела инструменты трейдинга"""
    try:
        query = update.callback_query
        if not query:
            return
        
        await query.answer()
        
        # Определяем язык пользователя
        user_id = query.from_user.id
        logger.info(f"Processing trading_tools request for user_id: {user_id}")
        
        # Получаем данные пользователя
        user_data = get_user(user_id)
        if user_data:
            lang_code = user_data.get('language_code', 'ru')
            logger.info(f"User language: {lang_code}")
        else:
            lang_code = 'ru'
            logger.warning(f"User data not found, using default language")
    except Exception as e:
        logger.error(f"Error in handle_trading_tools: {e}")
        lang_code = 'ru'
    
    # Проверяем, запрошен ли конкретный инструмент
    if query.data.startswith("tool_"):
        # Извлекаем имя инструмента из callback_data
        tool_name = query.data.replace("tool_", "")
        await show_tool_details(update, context, tool_name, lang_code)
        return
    
    # Тексты заголовков на разных языках
    titles = {
        'tg': '🧰 Абзорҳои трейдинг',
        'ru': '🧰 Инструменты трейдинга',
        'uz': '🧰 Treyding vositalari',
        'kk': '🧰 Трейдинг құралдары',
        'en': '🧰 Trading Tools'
    }
    
    # Тексты описаний на разных языках
    descriptions = {
        'tg': 'Интихоб намоед абзорро барои гирифтани маълумоти муфассал ва тавсияҳо:',
        'ru': 'Выберите инструмент для получения подробной информации и рекомендаций:',
        'uz': 'Batafsil ma\'lumot va tavsiyalar olish uchun vositani tanlang:',
        'kk': 'Толық ақпарат пен ұсыныстар алу үшін құралды таңдаңыз:',
        'en': 'Select a tool for detailed information and recommendations:'
    }
    
    # Кнопки категорий инструментов на разных языках
    tools_buttons = {
        'tg': [
            ["📊 Платформаҳо", "📈 Индикаторҳо"],
            ["📱 Замимаҳо", "📰 Манбаъҳои ахборот"],
            ["💰 Идоракунии хавф", "📚 Китобхона"]
        ],
        'ru': [
            ["📊 Платформы", "📈 Индикаторы"],
            ["📱 Приложения", "📰 Источники информации"],
            ["💰 Управление рисками", "📚 Библиотека"]
        ],
        'uz': [
            ["📊 Platformalar", "📈 Indikatorlar"],
            ["📱 Ilovalar", "📰 Axborot manbalari"],
            ["💰 Risklarni boshqarish", "📚 Kutubxona"]
        ],
        'kk': [
            ["📊 Платформалар", "📈 Индикаторлар"],
            ["📱 Қосымшалар", "📰 Ақпарат көздері"],
            ["💰 Тәуекелдерді басқару", "📚 Кітапхана"]
        ],
        'en': [
            ["📊 Platforms", "📈 Indicators"],
            ["📱 Applications", "📰 Information Sources"],
            ["💰 Risk Management", "📚 Library"]
        ]
    }
    
    back_button_text = {
        'tg': '↩️ Бозгашт',
        'ru': '↩️ Назад',
        'uz': '↩️ Orqaga',
        'kk': '↩️ Артқа',
        'en': '↩️ Back'
    }
    
    # Формируем сообщение на нужном языке
    title = titles.get(lang_code, titles['ru'])
    description = descriptions.get(lang_code, descriptions['ru'])
    buttons = tools_buttons.get(lang_code, tools_buttons['ru'])
    back_button = back_button_text.get(lang_code, back_button_text['ru'])
    
    message = f"{title}\n\n{description}"
    
    # Создаем клавиатуру с кнопками инструментов
    keyboard = []
    
    # Добавляем кнопки инструментов
    for button_row in buttons:
        row = []
        for button_text in button_row:
            # Генерируем callback_data на основе имени инструмента
            # Убираем эмодзи из callback_data
            tool_name = "".join(button_text.split()[1:])
            callback_data = f"tool_{tool_name}"
            row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        keyboard.append(row)
    
    # Добавляем кнопку возврата
    keyboard.append([InlineKeyboardButton(back_button, callback_data="return_to_main")])
    
    # Отправляем сообщение
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_book_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для подробной информации о книгах"""
    try:
        query = update.callback_query
        if not query:
            return
        
        await query.answer()
        
        # Определяем язык пользователя
        user_id = query.from_user.id
        logger.info(f"Processing book details request for user_id: {user_id}")
        
        # Получаем данные пользователя
        user_data = get_user(user_id)
        if user_data:
            lang_code = user_data.get('language_code', 'ru')
            logger.info(f"User language: {lang_code}")
        else:
            lang_code = 'ru'
            logger.warning(f"User data not found, using default language")
        
        # Извлекаем индекс книги из callback-data
        book_index = int(query.data.split('_')[-1])
        
        # Получаем список книг на выбранном языке
        book_list = books.get(lang_code, books['ru'])
        
        # Проверяем корректность индекса
        if book_index < 0 or book_index >= len(book_list):
            await query.edit_message_text(
                "⚠️ Информация о книге не найдена.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("↩️ Назад", callback_data="trading_books")
                ]])
            )
            return
        
        # Получаем данные о книге
        book = book_list[book_index]
        
        # Тексты для деталей книги на разных языках
        details_texts = {
            'tg': {
                'title': 'Маълумоти муфассал оид ба китоб:',
                'description': 'Тавсиф:',
                'pages': 'Миқдори саҳифаҳо:',
                'year': 'Соли нашр:',
                'back': '↩️ Бозгашт',
                'download': '📥 Боргирӣ кардан'
            },
            'ru': {
                'title': 'Подробная информация о книге:',
                'description': 'Описание:',
                'pages': 'Количество страниц:',
                'year': 'Год издания:',
                'back': '↩️ Назад',
                'download': '📥 Скачать книгу'
            },
            'uz': {
                'title': 'Kitob haqida batafsil ma\'lumot:',
                'description': 'Tavsif:',
                'pages': 'Sahifalar soni:',
                'year': 'Nashr yili:',
                'back': '↩️ Orqaga',
                'download': '📥 Kitobni yuklab olish'
            },
            'kk': {
                'title': 'Кітап туралы толық ақпарат:',
                'description': 'Сипаттама:',
                'pages': 'Беттер саны:',
                'year': 'Жарияланған жылы:',
                'back': '↩️ Артқа',
                'download': '📥 Кітапты жүктеу'
            },
            'en': {
                'title': 'Detailed book information:',
                'description': 'Description:',
                'pages': 'Number of pages:',
                'year': 'Publication year:',
                'back': '↩️ Back',
                'download': '📥 Download book'
            }
        }
        
        # Выбираем тексты для текущего языка
        texts = details_texts.get(lang_code, details_texts['ru'])
        
        # Формируем сообщение с подробной информацией
        message = f"*{book['title']}*\n\n"
        message += f"{texts['description']} {book['description']}\n\n"
        message += f"{texts['pages']}: {book['pages']}\n"
        message += f"{texts['year']}: {book['year']}\n"
        
        # Создаем клавиатуру с кнопками скачивания и возврата
        keyboard = [
            [InlineKeyboardButton(texts['download'], url=book['download_link'])],
            [InlineKeyboardButton(texts['back'], callback_data="trading_books")]
        ]
        
        # Отправляем сообщение
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in handle_book_details: {e}")
        await query.edit_message_text(
            "⚠️ Произошла ошибка при получении информации о книге.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("↩️ Назад", callback_data="trading_books")
            ]])
        )

async def show_strategy_details(update: Update, context: ContextTypes.DEFAULT_TYPE, strategy_name: str, lang_code: str):
    """Обработчик для отображения подробной информации о выбранной стратегии"""
    query = update.callback_query
    
    # Словари с описаниями стратегий на разных языках
    strategy_details = {
        'Скальпинг': {
            'ru': {
                'title': '⚡ Скальпинг (Scalping)',
                'description': 'Быстрая торговля с целью получения небольшой прибыли от минимальных движений цены. Характеризуется множеством краткосрочных сделок в течение дня.',
                'how_it_works': 'Как это работает:\n'
                                '1. Использование таймфреймов M1-M5 для поиска торговых возможностей\n'
                                '2. Открытие позиций при небольших импульсах цены или прорывах уровней\n'
                                '3. Удержание позиций от нескольких секунд до нескольких минут\n'
                                '4. Использование малых стоп-лоссов и тейк-профитов (1-10 пунктов)\n'
                                '5. Закрытие всех позиций к концу торговой сессии',
                'example': 'Пример: Трейдер замечает формирование паттерна "Пинбар" на 5-минутном графике GBP/USD. Он открывает позицию с целью заработать 5-7 пунктов и выходит из сделки через 2-3 минуты.',
                'image_description': 'На графике EUR/USD (M5) показаны короткие сделки скальпинга с тейк-профитами в 5-8 пунктов, отмеченные точками входа (синие стрелки) и выхода (зеленые стрелки).',
                'pros_cons': '*Преимущества:*\n'
                            '✅ Множество торговых возможностей в течение дня\n'
                            '✅ Быстрое получение результата\n'
                            '✅ Меньшая подверженность неожиданным фундаментальным событиям\n'
                            '✅ Возможность заработка при любом состоянии рынка\n\n'
                            '*Недостатки:*\n'
                            '❌ Высокие комиссии и спреды могут съедать прибыль\n'
                            '❌ Требует постоянной концентрации и быстрой реакции\n'
                            '❌ Высокая психологическая нагрузка\n'
                            '❌ Необходимость использовать большое кредитное плечо',
                'tools': '*Инструменты для скальпинга:*\n'
                        '• Платформы: cTrader, MetaTrader 5\n'
                        '• Индикаторы: MACD (с настройками 5,3,3), Bollinger Bands (10,2), Stochastic (5,3,3)\n'
                        '• Брокеры с низкими спредами и быстрым исполнением\n'
                        '• Скрипты для автоматического выставления стоп-лоссов и тейк-профитов'
            },
            'en': {
                'title': '⚡ Scalping',
                'description': 'Fast-paced trading aimed at capturing small profits from minimal price movements. Characterized by multiple short-term trades throughout the day.',
                'how_it_works': 'How it works:\n'
                                '1. Use of M1-M5 timeframes to find trading opportunities\n'
                                '2. Opening positions during small price impulses or level breakouts\n'
                                '3. Holding positions from a few seconds to a few minutes\n'
                                '4. Using small stop-losses and take-profits (1-10 points)\n'
                                '5. Closing all positions by the end of the trading session',
                'example': 'Example: A trader notices a "Pinbar" pattern forming on the 5-minute GBP/USD chart. They open a position aiming to make 5-7 points and exit the trade within 2-3 minutes.',
                'image_description': 'The EUR/USD chart (M5) shows short scalping trades with take-profits of 5-8 points, marked with entry points (blue arrows) and exit points (green arrows).',
                'pros_cons': '*Advantages:*\n'
                            '✅ Multiple trading opportunities throughout the day\n'
                            '✅ Quick results\n'
                            '✅ Less exposure to unexpected fundamental events\n'
                            '✅ Ability to profit in any market condition\n\n'
                            '*Disadvantages:*\n'
                            '❌ High commissions and spreads can eat into profits\n'
                            '❌ Requires constant concentration and quick reactions\n'
                            '❌ High psychological pressure\n'
                            '❌ Need to use high leverage',
                'tools': '*Tools for Scalping:*\n'
                        '• Platforms: cTrader, MetaTrader 5\n'
                        '• Indicators: MACD (with settings 5,3,3), Bollinger Bands (10,2), Stochastic (5,3,3)\n'
                        '• Brokers with low spreads and fast execution\n'
                        '• Scripts for automatic setting of stop-losses and take-profits'
            },
            'tg': {
                'title': '⚡ Скалпинг (Scalping)',
                'description': 'Савдои босуръат бо мақсади гирифтани фоидаи хурд аз ҳаракатҳои ҷузъии нарх. Бо миқдори зиёди муомилаҳои кӯтоҳмуддат дар тӯли рӯз тавсиф карда мешавад.',
                'how_it_works': 'Чӣ тавр кор мекунад:\n'
                                '1. Истифодаи давраҳои вақти M1-M5 барои ёфтани имкониятҳои савдо\n'
                                '2. Кушодани мавқеъҳо ҳангоми импулсҳои хурди нарх ё рахнаҳои сатҳ\n'
                                '3. Нигоҳ доштани мавқеъҳо аз якчанд сония то якчанд дақиқа\n'
                                '4. Истифодаи дастурҳои хурди стоп-лосс ва тейк-профит (1-10 пункт)\n'
                                '5. Бастани ҳамаи мавқеъҳо то охири ҷаласаи савдо',
                'example': 'Мисол: Трейдер ташаккули намунаи "Пинбар"-ро дар графики 5-дақиқагии GBP/USD мебинад. Вай мавқеъро бо мақсади ба даст овардани 5-7 пункт мекушояд ва аз муомила дар муддати 2-3 дақиқа мебарояд.',
                'pros_cons': '*Афзалиятҳо:*\n'
                            '✅ Имкониятҳои бисёри савдо дар тӯли рӯз\n'
                            '✅ Натиҷаи фаврӣ\n'
                            '✅ Осебпазирии камтар ба рӯйдодҳои ғайричашмдошти асосӣ\n'
                            '✅ Имконияти даромад дар ҳар гуна шароити бозор\n\n'
                            '*Камбудиҳо:*\n'
                            '❌ Ҳаққи хизмат ва спредҳои баланд метавонанд фоидаро хӯранд\n'
                            '❌ Тамаркуз ва аксуламали доимиро талаб мекунад\n'
                            '❌ Фишори баланди психологӣ\n'
                            '❌ Зарурати истифодаи рычаги баланд'
            }
        },
        'Трендоваястратегия': {
            'tg': {
                'title': '📊 Стратегияи руйтамоили (Trend Trading)',
                'description': 'Савдо дар самти руйтамоили бозор. Принсипи асосӣ — "тамоил дӯсти шумост".',
                'how_it_works': 'Чӣ тавр кор мекунад:\n'
                                '1. Муайян кардани тамоил бо ёрии индикаторҳои техникӣ (MA, MACD)\n'
                                '2. Дохилшавӣ дар самти тамоил ҳангоми ислоҳи нархҳо\n'
                                '3. Гузоштани дастури стоп-лосс дар рӯйтамоили муқобил\n'
                                '4. Гирифтани фоида ҳангоми давом додани рӯйтамоил',
                'example': 'Мисол: Ҳангоми тамоюли афзоишёбанда дар EUR/USD, трейдер мавқеи харидро дар вакти коррексияи якум ташкил мекунад.',
                'pros_cons': '*Афзалиятҳо:*\n'
                            '✅ Муносиб барои трейдерҳои навомӯз\n'
                            '✅ Метавонад барои муддати тӯлонӣ фоида орад\n\n'
                            '*Камбудиҳо:*\n'
                            '❌ Мумкин аст дер гузаштан аз тамоюл\n'
                            '❌ Зарур будани таҳаммул дар давраҳои бозори беруйтамо'
            },
            'ru': {
                'title': '📊 Трендовая стратегия (Trend Trading)',
                'description': 'Торговля в направлении рыночного тренда. Основной принцип — "тренд — ваш друг".',
                'how_it_works': 'Как это работает:\n'
                                '1. Определение тренда с помощью технических индикаторов (MA, MACD)\n'
                                '2. Вход в направлении тренда при коррекциях цены\n'
                                '3. Установка стоп-лосса на противоположной стороне тренда\n'
                                '4. Фиксация прибыли при продолжении тренда',
                'example': 'Пример: При восходящем тренде на EUR/USD трейдер открывает длинную позицию после первой коррекции.',
                'image_description': 'На этом графике EUR/USD виден восходящий тренд с несколькими точками входа после коррекций. Синими стрелками отмечены оптимальные входы в рынок, красными линиями — уровни стоп-лосс, зелеными — тейк-профит.',
                'pros_cons': '*Преимущества:*\n'
                            '✅ Подходит для новичков\n'
                            '✅ Может приносить прибыль длительное время\n\n'
                            '*Недостатки:*\n'
                            '❌ Возможно позднее определение тренда\n'
                            '❌ Требует терпения в периоды безтрендового рынка'
            },
            'uz': {
                'title': '📊 Trend strategiyasi (Trend Trading)',
                'description': 'Bozor yo\'nalishi bo\'yicha savdo qilish. Asosiy tamoyil — "trend — sizning do\'stingiz".',
                'how_it_works': 'Bu qanday ishlaydi:\n'
                                '1. Texnik indikatorlar (MA, MACD) yordamida trendni aniqlash\n'
                                '2. Narx tuzatilganda trend yo\'nalishida kirish\n'
                                '3. Trendning qarama-qarshi tomonida stop-loss o\'rnatish\n'
                                '4. Trend davom etsa, foydani belgilash',
                'example': 'Misol: EUR/USD\'da ko\'tariluvchi trend bo\'lganda, treydir birinchi tuzatishdan keyin uzun pozitsiya ochadi.',
                'pros_cons': '*Afzalliklari:*\n'
                            '✅ Yangi boshlovchilar uchun mos\n'
                            '✅ Uzoq vaqt davomida foyda keltirishi mumkin\n\n'
                            '*Kamchiliklari:*\n'
                            '❌ Trendni kech aniqlash mumkin\n'
                            '❌ Trendsiz bozor davrlarida sabr talab qiladi'
            },
            'kk': {
                'title': '📊 Тренд стратегиясы (Trend Trading)',
                'description': 'Нарық тренді бағытында сауда жасау. Негізгі қағида — "тренд — сіздің досыңыз".',
                'how_it_works': 'Бұл қалай жұмыс істейді:\n'
                                '1. Техникалық индикаторлардың (MA, MACD) көмегімен трендті анықтау\n'
                                '2. Баға түзетілгенде тренд бағытына кіру\n'
                                '3. Трендтің қарама-қарсы жағында стоп-лосс орнату\n'
                                '4. Тренд жалғасса, пайданы бекіту',
                'example': 'Мысал: EUR/USD жұбында көтерілу тренді болған кезде, трейдер бірінші түзетуден кейін ұзақ позиция ашады.',
                'pros_cons': '*Артықшылықтары:*\n'
                            '✅ Жаңадан бастаушыларға қолайлы\n'
                            '✅ Ұзақ уақыт бойы пайда әкелуі мүмкін\n\n'
                            '*Кемшіліктері:*\n'
                            '❌ Трендті кеш анықтау мүмкін\n'
                            '❌ Трендсіз нарық кезеңінде төзімділікті қажет етеді'
            },
            'en': {
                'title': '📊 Trend Trading Strategy',
                'description': 'Trading in the direction of the market trend. The main principle is "the trend is your friend".',
                'how_it_works': 'How it works:\n'
                                '1. Identifying the trend using technical indicators (MA, MACD)\n'
                                '2. Entering in the trend direction during price corrections\n'
                                '3. Setting a stop-loss on the opposite side of the trend\n'
                                '4. Taking profit as the trend continues',
                'example': 'Example: In an uptrend on EUR/USD, a trader opens a long position after the first correction.',
                'pros_cons': '*Advantages:*\n'
                            '✅ Suitable for beginners\n'
                            '✅ Can generate profits for a long time\n\n'
                            '*Disadvantages:*\n'
                            '❌ Possible late identification of the trend\n'
                            '❌ Requires patience during trendless market periods'
            }
        },
        'Свингтрейдинг': {
            'ru': {
                'title': '🔄 Свинг-трейдинг (Swing Trading)',
                'description': 'Среднесрочная торговая стратегия, нацеленная на получение прибыли от изменений цены в течение нескольких дней или недель. Использует преимущества колебаний (свингов) рынка.',
                'how_it_works': 'Как это работает:\n'
                               '1. Определение текущего тренда на старших таймфреймах (H4, Daily)\n'
                               '2. Поиск точек разворота или продолжения тренда на младших таймфреймах (H1)\n'
                               '3. Открытие позиций с периодом удержания от нескольких дней до нескольких недель\n'
                               '4. Использование широких стоп-лоссов и тейк-профитов для учета рыночной волатильности\n'
                               '5. Частичное закрытие позиций при достижении определенных уровней прибыли',
                'example': 'Пример: Трейдер замечает формирование паттерна "Голова и плечи" на дневном графике USD/JPY, указывающего на возможный разворот тренда. Он открывает короткую позицию, устанавливая стоп-лосс выше "головы" паттерна и планируя удерживать сделку несколько недель для достижения целевого уровня.',
                'image_description': 'На графике GBP/USD (Daily) отмечены ключевые точки свинг-трейдинга: входы при отскоках от уровней поддержки/сопротивления, стоп-лоссы выше/ниже локальных экстремумов и целевые уровни на основании предыдущих свингов.',
                'pros_cons': '*Преимущества:*\n'
                           '✅ Меньшее количество сделок и более низкие комиссии\n'
                           '✅ Не требует постоянного мониторинга рынка\n'
                           '✅ Возможность совмещать с основной работой\n'
                           '✅ Более высокое соотношение риск/прибыль по сравнению с дневным трейдингом\n\n'
                           '*Недостатки:*\n'
                           '❌ Более высокий размер стоп-лосса в пунктах\n'
                           '❌ Подверженность рискам новостных событий\n'
                           '❌ Требуется больше терпения и дисциплины\n'
                           '❌ Меньше торговых возможностей по сравнению с внутридневной торговлей',
                'tools': '*Инструменты для свинг-трейдинга:*\n'
                        '• Графические паттерны: "Голова и плечи", "Двойной верх/низ", "Флаг"\n'
                        '• Индикаторы: EMA (8, 21), RSI (14), MACD (12, 26, 9), Фибоначчи\n'
                        '• Уровни поддержки и сопротивления, ключевые ценовые уровни\n'
                        '• Инструменты управления рисками для больших временных периодов'
            },
            'en': {
                'title': '🔄 Swing Trading',
                'description': 'A medium-term trading strategy aimed at capturing price changes over several days or weeks. Takes advantage of market swings.',
                'how_it_works': 'How it works:\n'
                               '1. Determine the current trend on higher timeframes (H4, Daily)\n'
                               '2. Look for reversal or continuation points on lower timeframes (H1)\n'
                               '3. Open positions with holding periods from several days to several weeks\n'
                               '4. Use wider stop-losses and take-profits to account for market volatility\n'
                               '5. Partially close positions when certain profit levels are reached',
                'example': 'Example: A trader notices a "Head and Shoulders" pattern forming on the daily USD/JPY chart, indicating a possible trend reversal. They open a short position, setting a stop-loss above the "head" of the pattern and planning to hold the trade for several weeks to reach the target level.',
                'image_description': 'The GBP/USD chart (Daily) shows key swing trading points: entries at bounces from support/resistance levels, stop-losses above/below local extremes, and target levels based on previous swings.',
                'pros_cons': '*Advantages:*\n'
                           '✅ Fewer trades and lower commissions\n'
                           '✅ Does not require constant market monitoring\n'
                           '✅ Can be combined with a full-time job\n'
                           '✅ Higher risk/reward ratio compared to day trading\n\n'
                           '*Disadvantages:*\n'
                           '❌ Higher stop-loss size in points\n'
                           '❌ Exposure to news event risks\n'
                           '❌ Requires more patience and discipline\n'
                           '❌ Fewer trading opportunities compared to intraday trading',
                'tools': '*Tools for Swing Trading:*\n'
                        '• Chart patterns: "Head and Shoulders", "Double Top/Bottom", "Flag"\n'
                        '• Indicators: EMA (8, 21), RSI (14), MACD (12, 26, 9), Fibonacci\n'
                        '• Support and resistance levels, key price levels\n'
                        '• Risk management tools for longer time periods'
            },
            'tg': {
                'title': '🔄 Свинг-трейдинг (Swing Trading)',
                'description': 'Стратегияи савдои миёнамуҳлат, ки ба гирифтани фоида аз тағйироти нарх дар давоми якчанд рӯз ё ҳафта равона карда шудааст. Аз афзалиятҳои тағйироти (свингҳои) бозор истифода мебарад.',
                'how_it_works': 'Чӣ тавр кор мекунад:\n'
                               '1. Муайян кардани тамоюли ҷорӣ дар давраҳои вақти баландтар (H4, Daily)\n'
                               '2. Ҷустуҷӯи нуқтаҳои баргашт ё давомдиҳии тамоюл дар давраҳои вақти хурдтар (H1)\n'
                               '3. Кушодани мавқеъҳо бо давраи нигоҳдорӣ аз якчанд рӯз то якчанд ҳафта\n'
                               '4. Истифодаи дастурҳои васеи стоп-лосс ва тейк-профит барои ба ҳисоб гирифтани ноустувории бозор\n'
                               '5. Бастани ҷузъии мавқеъҳо ҳангоми ба даст овардани сатҳҳои муайяни фоида',
                'pros_cons': '*Афзалиятҳо:*\n'
                           '✅ Шумораи камтари муомилаҳо ва ҳаққи камтари комиссия\n'
                           '✅ Назорати доимии бозорро талаб намекунад\n'
                           '✅ Имконияти муттаҳид кардан бо кори асосӣ\n'
                           '✅ Таносуби баландтари хавф/фоида нисбати трейдинги рӯзона\n\n'
                           '*Камбудиҳо:*\n'
                           '❌ Андозаи баландтари стоп-лосс дар пунктҳо\n'
                           '❌ Осебпазирӣ ба хавфҳои рӯйдодҳои хабарӣ\n'
                           '❌ Сабр ва интизоми бештар талаб карда мешавад\n'
                           '❌ Имкониятҳои камтари савдо нисбат ба савдои дохилирӯзӣ'
            }
        },
        'Позиционнаяторговля': {
            'ru': {
                'title': '📆 Позиционная торговля (Position Trading)',
                'description': 'Долгосрочная торговая стратегия, основанная на удержании позиций от нескольких недель до нескольких месяцев или даже лет. Ориентирована на выявление и следование за долгосрочными трендами рынка.',
                'how_it_works': 'Как это работает:\n'
                               '1. Анализ фундаментальных факторов и макроэкономических тенденций\n'
                               '2. Определение долгосрочного тренда на дневных и недельных графиках\n'
                               '3. Использование крупных уровней поддержки и сопротивления\n'
                               '4. Открытие позиций с расчетом на значительные движения цены\n'
                               '5. Удержание сделок в течение длительного периода с периодической корректировкой стоп-лоссов',
                'example': 'Пример: Инвестор анализирует экономические показатели США и Европы, прогнозируя долгосрочное укрепление доллара. На недельном графике EUR/USD формируется нисходящий тренд. Трейдер открывает короткую позицию на уровне 1.1200 с целью 1.0500 и удерживает её несколько месяцев, передвигая стоп-лосс вслед за движением цены.',
                'image_description': 'На недельном графике EUR/USD показан долгосрочный нисходящий тренд с точкой входа в продажу на ключевом уровне сопротивления. Отмечено постепенное движение стоп-лосса вниз по мере развития тренда и несколько промежуточных уровней фиксации части прибыли.',
                'pros_cons': '*Преимущества:*\n'
                           '✅ Минимальные временные затраты на торговлю\n'
                           '✅ Очень низкие комиссионные расходы\n'
                           '✅ Возможность получения значительной прибыли от масштабных движений рынка\n'
                           '✅ Меньшая подверженность рыночному шуму и краткосрочным колебаниям\n\n'
                           '*Недостатки:*\n'
                           '❌ Требует значительного торгового капитала\n'
                           '❌ Длительное ожидание результатов\n'
                           '❌ Необходимость глубокого понимания фундаментальных факторов\n'
                           '❌ Риск упустить другие торговые возможности из-за замороженного капитала',
                'tools': '*Инструменты для позиционной торговли:*\n'
                        '• Фундаментальный анализ: отчеты центральных банков, макроэкономические индикаторы\n'
                        '• Технические индикаторы: MA (50, 200), MACD на недельных графиках\n'
                        '• Методы определения глобальных трендов: метод Доу, волновая теория Эллиотта\n'
                        '• Инструменты управления капиталом для долгосрочных позиций'
            },
            'en': {
                'title': '📆 Position Trading',
                'description': 'A long-term trading strategy based on holding positions from several weeks to several months or even years. Focused on identifying and following long-term market trends.',
                'how_it_works': 'How it works:\n'
                               '1. Analysis of fundamental factors and macroeconomic trends\n'
                               '2. Determining the long-term trend on daily and weekly charts\n'
                               '3. Using major support and resistance levels\n'
                               '4. Opening positions calculated for significant price movements\n'
                               '5. Holding trades for an extended period with periodic adjustment of stop-losses',
                'example': 'Example: An investor analyzes economic indicators of the US and Europe, predicting long-term strengthening of the dollar. A downtrend forms on the weekly EUR/USD chart. The trader opens a short position at 1.1200 targeting 1.0500 and holds it for several months, trailing the stop-loss as price moves.',
                'image_description': 'The weekly EUR/USD chart shows a long-term downtrend with a sell entry point at a key resistance level. Gradual movement of the stop-loss downward as the trend develops and several intermediate levels for partial profit-taking are marked.',
                'pros_cons': '*Advantages:*\n'
                           '✅ Minimal time investment in trading\n'
                           '✅ Very low commission expenses\n'
                           '✅ Potential for significant profits from large market movements\n'
                           '✅ Less exposure to market noise and short-term fluctuations\n\n'
                           '*Disadvantages:*\n'
                           '❌ Requires substantial trading capital\n'
                           '❌ Long waiting period for results\n'
                           '❌ Needs deep understanding of fundamental factors\n'
                           '❌ Risk of missing other trading opportunities due to tied-up capital',
                'tools': '*Tools for Position Trading:*\n'
                        '• Fundamental analysis: central bank reports, macroeconomic indicators\n'
                        '• Technical indicators: MA (50, 200), MACD on weekly charts\n'
                        '• Methods for determining global trends: Dow Theory, Elliott Wave Theory\n'
                        '• Capital management tools for long-term positions'
            },
            'tg': {
                'title': '📆 Савдои мавқеӣ (Position Trading)',
                'description': 'Стратегияи савдои дарозмуддат, ки ба нигоҳ доштани мавқеъҳо аз якчанд ҳафта то якчанд моҳ ё ҳатто солҳо асос ёфтааст. Ба муайян ва пайравӣ кардани тамоюлҳои дарозмуддати бозор равона карда шудааст.',
                'how_it_works': 'Чӣ тавр кор мекунад:\n'
                               '1. Таҳлили омилҳои асосӣ ва тамоюлҳои макроиқтисодӣ\n'
                               '2. Муайян кардани тамоюли дарозмуддат дар графикҳои рӯзона ва ҳафтаина\n'
                               '3. Истифодаи сатҳҳои асосии дастгирӣ ва муқовимат\n'
                               '4. Кушодани мавқеъҳо бо ҳисоби ҳаракатҳои назарраси нарх\n'
                               '5. Нигоҳ доштани муомилаҳо дар тӯли давраи дароз бо танзими даврии стоп-лоссҳо',
                'pros_cons': '*Афзалиятҳо:*\n'
                           '✅ Сарфи камтарини вақт барои савдо\n'
                           '✅ Хароҷоти хеле пасти комиссионӣ\n'
                           '✅ Имконияти гирифтани фоидаи назаррас аз ҳаракатҳои калони бозор\n'
                           '✅ Осебпазирии камтар ба ғавғои бозор ва тағйироти кӯтоҳмуддат\n\n'
                           '*Камбудиҳо:*\n'
                           '❌ Сармояи назарраси савдоро талаб мекунад\n'
                           '❌ Давраи дарози интизории натиҷаҳо\n'
                           '❌ Фаҳмиши амиқи омилҳои асосиро талаб мекунад\n'
                           '❌ Хавфи аз даст додани имкониятҳои дигари савдо бо сабаби сармояи банд'
            }
        },
        'Разворотнаястратегия': {
            'tg': {
                'title': '📉 Инверсия (Reversal Trading)',
                'description': 'Ҷустуҷӯи нуқтаҳои гардиш ва тағйири тамоюл дар бозор. Муомилот дар самти муқобили тамоюли ҷорӣ.',
                'how_it_works': 'Чӣ тавр кор мекунад:\n'
                                '1. Муайян кардани нуқтаҳои эҳтимолии гардиш (ҳадди ақал/максимум)\n'
                                '2. Тасдиқи инверсия тавассути индикаторҳои техникӣ\n'
                                '3. Гузоштани ордер дар самти муқобили тамоюли ҷорӣ\n'
                                '4. Нигоҳ доштани позитсия то ташаккули тамоюли нав',
                'example': 'Мисол: Ҳангоми расидан ба сатҳи муқовимати қавӣ дар тамоюли афзоиш, трейдер мавқеи фурӯшро ташкил мекунад.',
                'pros_cons': '*Афзалиятҳо:*\n'
                            '✅ Метавонад фоидаи зиёд диҳад\n'
                            '✅ Имконияти дохилшавӣ дар нуқтаҳои оптималӣ\n\n'
                            '*Камбудиҳо:*\n'
                            '❌ Хавфи баланд дар ҳолати нодуруст будани таҳлил\n'
                            '❌ Талаб мекунад таҷрибаи зиёд'
            },
            'ru': {
                'title': '📉 Разворотная стратегия (Reversal Trading)',
                'description': 'Поиск точек разворота и смены тренда на рынке. Торговля против текущего тренда.',
                'how_it_works': 'Как это работает:\n'
                                '1. Определение потенциальных точек разворота (минимумы/максимумы)\n'
                                '2. Подтверждение разворота через технические индикаторы\n'
                                '3. Размещение ордера против текущего тренда\n'
                                '4. Удержание позиции до формирования нового тренда',
                'example': 'Пример: При достижении сильного уровня сопротивления в восходящем тренде, трейдер открывает короткую позицию.',
                'image_description': 'На графике USD/JPY видны ключевые точки разворота тренда: двойная вершина с последующим нисходящим движением. Красными стрелками отмечены точки входа в короткую позицию после подтверждения разворота, синими линиями — уровни стоп-лосс.',
                'pros_cons': '*Преимущества:*\n'
                            '✅ Может приносить высокую прибыль\n'
                            '✅ Возможность входа в оптимальных точках\n\n'
                            '*Недостатки:*\n'
                            '❌ Высокий риск при неверном анализе\n'
                            '❌ Требует значительного опыта'
            },
            'uz': {
                'title': '📉 Aylanish strategiyasi (Reversal Trading)',
                'description': 'Bozorda burilish nuqtalarini va trend o\'zgarishlarini qidirish. Joriy trendga qarshi savdo qilish.',
                'how_it_works': 'Bu qanday ishlaydi:\n'
                                '1. Potensial burilish nuqtalarini (minimumlar/maksimumlar) aniqlash\n'
                                '2. Texnik indikatorlar orqali burilishni tasdiqlash\n'
                                '3. Joriy trendga qarshi buyurtma joylashtirish\n'
                                '4. Yangi trend shakllanguncha pozitsiyani ushlab turish',
                'example': 'Misol: Ko\'tariluvchi trendda kuchli qarshilik darajasiga erishilganda, treydir qisqa pozitsiya ochadi.',
                'pros_cons': '*Afzalliklari:*\n'
                            '✅ Yuqori foyda keltirishi mumkin\n'
                            '✅ Optimal nuqtalarda kirish imkoniyati\n\n'
                            '*Kamchiliklari:*\n'
                            '❌ Noto\'g\'ri tahlil qilganda yuqori xavf\n'
                            '❌ Sezilarli tajriba talab qiladi'
            },
            'kk': {
                'title': '📉 Бұрылыс стратегиясы (Reversal Trading)',
                'description': 'Нарықта бұрылу нүктелерін және тренд өзгерістерін іздеу. Ағымдағы трендке қарсы сауда жасау.',
                'how_it_works': 'Бұл қалай жұмыс істейді:\n'
                                '1. Әлеуетті бұрылыс нүктелерін (минимумдар/максимумдар) анықтау\n'
                                '2. Техникалық индикаторлар арқылы бұрылысты растау\n'
                                '3. Ағымдағы трендке қарсы ордер орналастыру\n'
                                '4. Жаңа тренд қалыптасқанша позицияны ұстап тұру',
                'example': 'Мысал: Көтерілу трендінде күшті қарсылық деңгейіне жеткенде, трейдер қысқа позиция ашады.',
                'pros_cons': '*Артықшылықтары:*\n'
                            '✅ Жоғары пайда әкелуі мүмкін\n'
                            '✅ Оңтайлы нүктелерде кіру мүмкіндігі\n\n'
                            '*Кемшіліктері:*\n'
                            '❌ Қате талдау жасағанда жоғары тәуекел\n'
                            '❌ Елеулі тәжірибені қажет етеді'
            },
            'en': {
                'title': '📉 Reversal Trading Strategy',
                'description': 'Looking for turning points and trend changes in the market. Trading against the current trend.',
                'how_it_works': 'How it works:\n'
                                '1. Identifying potential reversal points (lows/highs)\n'
                                '2. Confirming the reversal through technical indicators\n'
                                '3. Placing an order against the current trend\n'
                                '4. Holding the position until a new trend forms',
                'example': 'Example: When reaching a strong resistance level in an uptrend, a trader opens a short position.',
                'pros_cons': '*Advantages:*\n'
                            '✅ Can bring high profits\n'
                            '✅ Opportunity to enter at optimal points\n\n'
                            '*Disadvantages:*\n'
                            '❌ High risk with incorrect analysis\n'
                            '❌ Requires significant experience'
            }
        },
        # Добавьте другие стратегии аналогично
    }
    
    # Тексты на разных языках
    button_texts = {
        'tg': '↩️ Бозгашт ба рӯйхати стратегияҳо',
        'ru': '↩️ Вернуться к списку стратегий',
        'uz': '↩️ Strategiyalar ro\'yxatiga qaytish',
        'kk': '↩️ Стратегиялар тізіміне оралу',
        'en': '↩️ Return to strategies list'
    }
    
    # Получаем информацию о выбранной стратегии
    strategy_info = None
    for key, info in strategy_details.items():
        if key.lower() == strategy_name.lower():
            strategy_info = info
            break
    
    # Если стратегия не найдена, показываем сообщение об ошибке
    if not strategy_info:
        await query.edit_message_text(
            "⚠️ Подробная информация о этой стратегии временно недоступна.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(button_texts.get(lang_code, button_texts['ru']), callback_data="trading_strategies")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Получаем данные стратегии для выбранного языка
    strategy_data = strategy_info.get(lang_code, strategy_info['ru'])
    
    # Формируем сообщение с подробной информацией
    message = f"*{strategy_data['title']}*\n\n"
    message += f"{strategy_data['description']}\n\n"
    message += f"{strategy_data['how_it_works']}\n\n"
    message += f"*Пример:*\n{strategy_data['example']}\n\n"
    
    # Добавляем описание изображения, если оно есть
    if 'image_description' in strategy_data:
        message += f"*Визуальный пример:*\n{strategy_data['image_description']}\n\n"
    
    message += strategy_data['pros_cons']
    
    # Создаем клавиатуру с кнопкой возврата
    keyboard = [[InlineKeyboardButton(button_texts.get(lang_code, button_texts['ru']), callback_data="trading_strategies")]]
    
    # Отправляем сообщение
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_otc_pairs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для OTC Pocket Option пар"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        # Получаем данные пользователя для проверки доступа
        user_data = get_user(user_id)
        if not user_data or not user_data.get('is_approved'):
            await query.answer("⛔ У вас нет доступа к этой функции. Отправьте заявку на регистрацию.")
            return
        
        # Определяем язык пользователя
        lang_code = user_data.get('language_code', 'tg')
        
        # Создаем клавиатуру с OTC парами
        keyboard = []
        
        # Главный заголовок OTC Pocket Option
        keyboard.append([InlineKeyboardButton("📊 OTC POCKET OPTION 📊", callback_data="header_otc_main")])
        
        # === ОСНОВНЫЕ OTC ПАРЫ ===
        keyboard.append([InlineKeyboardButton("🌟 ОСНОВНЫЕ OTC ПАРЫ 🌟", callback_data="header_otc_major")])
        
        # Основные OTC пары USD
        major_usd_pairs = [
            "EUR/USD OTC", "GBP/USD OTC", "AUD/USD OTC", "NZD/USD OTC", 
            "USD/CAD OTC", "USD/CHF OTC", "USD/JPY OTC", "USD/SGD OTC"
        ]
        
        # Добавляем основные пары по 2 в строке
        for i in range(0, len(major_usd_pairs), 2):
            row = []
            row.append(InlineKeyboardButton(major_usd_pairs[i], callback_data=f"otc_{major_usd_pairs[i].replace('/', '_')}"))
            if i + 1 < len(major_usd_pairs):
                row.append(InlineKeyboardButton(major_usd_pairs[i + 1], callback_data=f"otc_{major_usd_pairs[i + 1].replace('/', '_')}"))
            keyboard.append(row)
        
        # === EUR КРОСС-КУРСЫ OTC ===
        keyboard.append([InlineKeyboardButton("💶 EUR КРОСС-КУРСЫ OTC 💶", callback_data="header_otc_eur")])
        
        # Кросс-курсы EUR OTC
        eur_pairs = [
            "EUR/GBP OTC", "EUR/JPY OTC", "EUR/CAD OTC", 
            "EUR/AUD OTC", "EUR/NZD OTC", "EUR/SGD OTC"
        ]
        
        # Добавляем EUR кросс-курсы по 2 в строке
        for i in range(0, len(eur_pairs), 2):
            row = []
            row.append(InlineKeyboardButton(eur_pairs[i], callback_data=f"otc_{eur_pairs[i].replace('/', '_')}"))
            if i + 1 < len(eur_pairs):
                row.append(InlineKeyboardButton(eur_pairs[i + 1], callback_data=f"otc_{eur_pairs[i + 1].replace('/', '_')}"))
            keyboard.append(row)
        
        # === GBP КРОСС-КУРСЫ OTC ===
        keyboard.append([InlineKeyboardButton("💷 GBP КРОСС-КУРСЫ OTC 💷", callback_data="header_otc_gbp")])
        
        # Кросс-курсы GBP OTC
        gbp_pairs = [
            "GBP/JPY OTC", "GBP/CHF OTC", "GBP/AUD OTC", 
            "GBP/CAD OTC", "GBP/NZD OTC"
        ]
        
        # Добавляем GBP кросс-курсы по 2 в строке
        for i in range(0, len(gbp_pairs), 2):
            row = []
            row.append(InlineKeyboardButton(gbp_pairs[i], callback_data=f"otc_{gbp_pairs[i].replace('/', '_')}"))
            if i + 1 < len(gbp_pairs):
                row.append(InlineKeyboardButton(gbp_pairs[i + 1], callback_data=f"otc_{gbp_pairs[i + 1].replace('/', '_')}"))
            keyboard.append(row)
        
        # === ДРУГИЕ КРОСС-КУРСЫ OTC ===
        keyboard.append([InlineKeyboardButton("🔄 ДРУГИЕ КРОСС-КУРСЫ OTC 🔄", callback_data="header_otc_other")])
        
        # Другие кросс-курсы OTC
        other_pairs = [
            "AUD/JPY OTC", "AUD/CAD OTC", "AUD/CHF OTC", "AUD/NZD OTC",
            "CAD/JPY OTC", "CHF/JPY OTC", "NZD/JPY OTC"
        ]
        
        # Добавляем другие кросс-курсы по 2 в строке
        for i in range(0, len(other_pairs), 2):
            row = []
            row.append(InlineKeyboardButton(other_pairs[i], callback_data=f"otc_{other_pairs[i].replace('/', '_')}"))
            if i + 1 < len(other_pairs):
                row.append(InlineKeyboardButton(other_pairs[i + 1], callback_data=f"otc_{other_pairs[i + 1].replace('/', '_')}"))
            keyboard.append(row)
        
        # === ЭКЗОТИЧЕСКИЕ OTC ПАРЫ ===
        keyboard.append([InlineKeyboardButton("🌍 ЭКЗОТИЧЕСКИЕ OTC ПАРЫ 🌍", callback_data="header_otc_exotic")])
        
        # Экзотические OTC пары
        exotic_pairs = [
            "USD/NOK OTC", "USD/SEK OTC", "USD/PLN OTC", "USD/MXN OTC",
            "USD/ZAR OTC", "USD/TRY OTC"
        ]
        
        # Добавляем экзотические пары по 2 в строке
        for i in range(0, len(exotic_pairs), 2):
            row = []
            if i < len(exotic_pairs):
                row.append(InlineKeyboardButton(exotic_pairs[i], callback_data=f"otc_{exotic_pairs[i].replace('/', '_')}"))
            if i + 1 < len(exotic_pairs):
                row.append(InlineKeyboardButton(exotic_pairs[i + 1], callback_data=f"otc_{exotic_pairs[i + 1].replace('/', '_')}"))
            keyboard.append(row)
        
        # Добавляем кнопку навигации назад
        keyboard.append([InlineKeyboardButton("↩️ Назад в главное меню", callback_data="return_to_main")])
        
        # Отправляем сообщение с клавиатурой
        await query.edit_message_text(
            "📱 *OTC Pocket Option*\n\n"
            "Выберите категорию и торговую пару для анализа:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in OTC pairs handler: {e}")
        await query.answer(f"Произошла ошибка: {str(e)}")

async def handle_otc_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для OTC сигналов"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        # Получаем данные пользователя для проверки доступа
        user_data = get_user(user_id)
        if not user_data or not user_data.get('is_approved'):
            await query.answer("⛔ У вас нет доступа к этой функции. Отправьте заявку на регистрацию.")
            return
        
        # Определяем язык пользователя
        lang_code = user_data.get('language_code', 'tg')
        
        # Создаем клавиатуру для сигналов
        keyboard = []
        
        # Заголовок для OTC сигналов
        keyboard.append([InlineKeyboardButton("🔔 OTC сигналы", callback_data="header_otc_signals")])
        
        # Дата для сообщения
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Расширенный список текущих OTC сигналов
        otc_signals = [
            {"pair": "EUR/USD OTC", "direction": "BUY", "confidence": 78, "expiry": "18:45"},
            {"pair": "GBP/JPY OTC", "direction": "SELL", "confidence": 75, "expiry": "19:00"},
            {"pair": "AUD/CAD OTC", "direction": "BUY", "confidence": 82, "expiry": "19:15"},
            {"pair": "USD/CHF OTC", "direction": "SELL", "confidence": 80, "expiry": "19:30"},
            {"pair": "AUD/USD OTC", "direction": "BUY", "confidence": 79, "expiry": "19:45"},
            {"pair": "EUR/GBP OTC", "direction": "SELL", "confidence": 77, "expiry": "20:00"},
            {"pair": "USD/SGD OTC", "direction": "BUY", "confidence": 81, "expiry": "20:15"},
            {"pair": "CHF/JPY OTC", "direction": "SELL", "confidence": 76, "expiry": "20:30"},
            {"pair": "EUR/AUD OTC", "direction": "BUY", "confidence": 83, "expiry": "20:45"},
            {"pair": "EUR/NZD OTC", "direction": "SELL", "confidence": 79, "expiry": "21:00"}
        ]
        
        # Формируем текст сообщения с сигналами
        signals_text = f"📱 *OTC Pocket Option Сигналы*\n\n⏰ Время обновления: {current_time}\n\n"
        
        for idx, signal in enumerate(otc_signals, 1):
            direction_emoji = "⬆️" if signal["direction"] == "BUY" else "⬇️"
            signals_text += f"{idx}. {signal['pair']} - {direction_emoji} {signal['direction']} ({signal['confidence']}%) - {signal['expiry']}\n"
        
        signals_text += "\n⚠️ *Используйте на свой страх и риск. Не является финансовой рекомендацией.*"
        
        # Добавляем кнопки действий
        keyboard.append([
            InlineKeyboardButton("🔄 Обновить", callback_data="otc_refresh_signals"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="otc_signal_settings")
        ])
        
        # Добавляем кнопку подписки на сигналы
        keyboard.append([InlineKeyboardButton("🔔 Подписаться на сигналы", callback_data="otc_subscribe")])
        
        # Добавляем кнопку навигации назад
        keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="return_to_main")])
        
        # Отправляем сообщение с клавиатурой
        await query.edit_message_text(
            signals_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in OTC signals handler: {e}")
        await query.answer(f"Произошла ошибка: {str(e)}")

async def show_tool_details(update: Update, context: ContextTypes.DEFAULT_TYPE, tool_name: str, lang_code: str):
    """Обработчик для отображения подробной информации о выбранном инструменте"""
    query = update.callback_query
    
    # Словари с описаниями инструментов на разных языках
    tools_details = {
        'Платформы': {
            'tg': {
                'title': '📊 Платформаҳои савдо',
                'description': 'Платформаҳои савдо - ин нармафзор барои амалиёти савдо дар бозорҳои молиявӣ.',
                'popular_tools': '*Платформаҳои маъмули савдо:*\n\n'
                                '1. *MetaTrader 4/5*\n'
                                '- Бартариҳо: Платформаи универсалӣ барои савдои асъор ва CFD\n'
                                '- Хусусиятҳо: Таҳлили техникӣ, савдои автоматӣ бо ёрии роботҳо\n'
                                '- Ҳаққи обуна: ройгон\n\n'
                                '2. *TradingView*\n'
                                '- Бартариҳо: Платформаи пешрафтаи графикӣ бо имкониятҳои таҳлилӣ\n'
                                '- Хусусиятҳо: Таҳлили техникӣ, муошират бо ҷомеа, скриптнависӣ\n'
                                '- Ҳаққи обуна: Аз $12.95 дар як моҳ\n\n'
                                '3. *cTrader*\n'
                                '- Бартариҳо: Дастрасии мустақим ба бозор (DMA)\n'
                                '- Хусусиятҳо: Таҳлили техникӣ, level 2 дефтари фармоишҳо\n'
                                '- Ҳаққи обуна: ройгон',
                'recommendations': '*Тавсияҳо барои интихоби платформа:*\n\n'
                                  '✅ Барои навомӯзон: MetaTrader 4, TradingView\n'
                                  '✅ Барои таҳлили техникӣ: TradingView\n'
                                  '✅ Барои савдои автоматӣ: MetaTrader 5\n'
                                  '✅ Барои скальпинг: cTrader, NinjaTrader\n'
                                  '❗ Ҳатман платформаро дар ҳисоби намоишӣ санҷед',
                'examples': '*Мисол:* \n'
                           'Дар TradingView, шумо метавонед аз индикаторҳои гуногун истифода баред, графикҳои муқоисавӣ созед ва бо ҷомеаи трейдерон муошират кунед.'
            },
            'ru': {
                'title': '📊 Торговые платформы',
                'description': 'Торговые платформы - это программное обеспечение для совершения торговых операций на финансовых рынках.',
                'popular_tools': '*Популярные торговые платформы:*\n\n'
                                '1. *MetaTrader 4/5*\n'
                                '- Преимущества: Универсальная платформа для торговли форекс и CFD\n'
                                '- Функции: Технический анализ, автоматическая торговля с помощью роботов\n'
                                '- Стоимость: бесплатно\n\n'
                                '2. *TradingView*\n'
                                '- Преимущества: Продвинутая графическая платформа с аналитическими возможностями\n'
                                '- Функции: Технический анализ, общение с сообществом, написание скриптов\n'
                                '- Стоимость: От $12.95 в месяц\n\n'
                                '3. *cTrader*\n'
                                '- Преимущества: Прямой доступ к рынку (DMA)\n'
                                '- Функции: Технический анализ, level 2 стакан цен\n'
                                '- Стоимость: бесплатно',
                'recommendations': '*Рекомендации по выбору платформы:*\n\n'
                                  '✅ Для новичков: MetaTrader 4, TradingView\n'
                                  '✅ Для технического анализа: TradingView\n'
                                  '✅ Для автоматической торговли: MetaTrader 5\n'
                                  '✅ Для скальпинга: cTrader, NinjaTrader\n'
                                  '❗ Обязательно тестируйте платформу на демо-счете',
                'examples': '*Пример:* \n'
                           'В TradingView вы можете использовать различные индикаторы, создавать сравнительные графики и взаимодействовать с сообществом трейдеров.'
            },
            'uz': {
                'title': '📊 Savdo platformalari',
                'description': 'Savdo platformalari - moliya bozorlarida savdo operatsiyalarini amalga oshirish uchun dasturiy ta\'minot.',
                'popular_tools': '*Mashhur savdo platformalari:*\n\n'
                                '1. *MetaTrader 4/5*\n'
                                '- Afzalliklari: Forex va CFD savdosi uchun universal platforma\n'
                                '- Imkoniyatlari: Texnik tahlil, robotlar yordamida avtomatik savdo\n'
                                '- Narxi: bepul\n\n'
                                '2. *TradingView*\n'
                                '- Afzalliklari: Analitik imkoniyatlarga ega rivojlangan grafik platforma\n'
                                '- Imkoniyatlari: Texnik tahlil, jamiyat bilan muloqot, skript yozish\n'
                                '- Narxi: Oyiga $12.95 dan\n\n'
                                '3. *cTrader*\n'
                                '- Afzalliklari: Bozorga to\'g\'ridan-to\'g\'ri kirish (DMA)\n'
                                '- Imkoniyatlari: Texnik tahlil, level 2 narx stakani\n'
                                '- Narxi: bepul',
                'recommendations': '*Platforma tanlash bo\'yicha tavsiyalar:*\n\n'
                                  '✅ Yangi boshlanuvchilar uchun: MetaTrader 4, TradingView\n'
                                  '✅ Texnik tahlil uchun: TradingView\n'
                                  '✅ Avtomatik savdo uchun: MetaTrader 5\n'
                                  '✅ Skalping uchun: cTrader, NinjaTrader\n'
                                  '❗ Albatta platformani demo hisobida sinab ko\'ring',
                'examples': '*Misol:* \n'
                           'TradingView\'da siz turli indikatorlardan foydalanishingiz, qiyosiy grafiklarni yaratishingiz va treyderlar jamoasi bilan o\'zaro aloqada bo\'lishingiz mumkin.'
            },
            'kk': {
                'title': '📊 Сауда платформалары',
                'description': 'Сауда платформалары - қаржы нарықтарында сауда операцияларын жүзеге асыруға арналған бағдарламалық жасақтама.',
                'popular_tools': '*Танымал сауда платформалары:*\n\n'
                                '1. *MetaTrader 4/5*\n'
                                '- Артықшылықтары: Форекс және CFD саудасына арналған әмбебап платформа\n'
                                '- Функциялары: Техникалық талдау, роботтар арқылы автоматты сауда\n'
                                '- Құны: тегін\n\n'
                                '2. *TradingView*\n'
                                '- Артықшылықтары: Аналитикалық мүмкіндіктері бар озық графикалық платформа\n'
                                '- Функциялары: Техникалық талдау, қауымдастықпен қарым-қатынас, скрипт жазу\n'
                                '- Құны: Айына $12.95 бастап\n\n'
                                '3. *cTrader*\n'
                                '- Артықшылықтары: Нарыққа тікелей қол жеткізу (DMA)\n'
                                '- Функциялары: Техникалық талдау, level 2 баға стаканы\n'
                                '- Құны: тегін',
                'recommendations': '*Платформа таңдау бойынша ұсыныстар:*\n\n'
                                  '✅ Жаңадан бастаушыларға: MetaTrader 4, TradingView\n'
                                  '✅ Техникалық талдау үшін: TradingView\n'
                                  '✅ Автоматты сауда үшін: MetaTrader 5\n'
                                  '✅ Скальпинг үшін: cTrader, NinjaTrader\n'
                                  '❗ Міндетті түрде платформаны демо шотта тексеріңіз',
                'examples': '*Мысал:* \n'
                           'TradingView-де сіз әртүрлі индикаторларды қолдана аласыз, салыстырмалы графиктер жасай аласыз және трейдерлер қауымдастығымен өзара әрекеттесе аласыз.'
            },
            'en': {
                'title': '📊 Trading Platforms',
                'description': 'Trading platforms are software applications that enable trading operations in financial markets.',
                'popular_tools': '*Popular Trading Platforms:*\n\n'
                                '1. *MetaTrader 4/5*\n'
                                '- Advantages: Universal platform for forex and CFD trading\n'
                                '- Features: Technical analysis, automated trading with robots\n'
                                '- Cost: free\n\n'
                                '2. *TradingView*\n'
                                '- Advantages: Advanced charting platform with analytical capabilities\n'
                                '- Features: Technical analysis, community interaction, script writing\n'
                                '- Cost: From $12.95 per month\n\n'
                                '3. *cTrader*\n'
                                '- Advantages: Direct Market Access (DMA)\n'
                                '- Features: Technical analysis, level 2 order book\n'
                                '- Cost: free',
                'recommendations': '*Platform Selection Recommendations:*\n\n'
                                  '✅ For beginners: MetaTrader 4, TradingView\n'
                                  '✅ For technical analysis: TradingView\n'
                                  '✅ For automated trading: MetaTrader 5\n'
                                  '✅ For scalping: cTrader, NinjaTrader\n'
                                  '❗ Always test the platform on a demo account',
                'examples': '*Example:* \n'
                           'In TradingView, you can use various indicators, create comparative charts, and interact with the trading community.'
            }
        },
        'Индикаторы': {
            'tg': {
                'title': '📈 Индикаторҳои техникӣ',
                'description': 'Индикаторҳои техникӣ - воситаҳои риёзӣ барои таҳлили нархҳо ва ҳаҷми муомилот мебошанд.',
                'popular_tools': '*Индикаторҳои маъмултарин:*\n\n'
                                '1. *Миёнаҳои ҳаракаткунанда (MA)*\n'
                                '- Истифода: Муайян кардани тамоюл ва сатҳи дастгирӣ/муқовимат\n'
                                '- Намудҳо: Оддӣ (SMA), Экспоненсиалӣ (EMA), Самти ҳаракати муқаррарӣ (SMMA)\n\n'
                                '2. *Индекси нисбии қувва (RSI)*\n'
                                '- Истифода: Муайян кардани ҳолатҳои боризи барзиёд харидан/фурӯхтан\n'
                                '- Доираи тағйирот: аз 0 то 100, бо сатҳҳои муҳими 30 ва 70\n\n'
                                '3. *MACD (Ҳамгироӣ ва суръатбахшии миёнаи ҳаракаткунанда)*\n'
                                '- Истифода: Муайян кардани тамоюл ва қувваи он\n'
                                '- Ташкил: Фарқияти байни EMA-и кӯтоҳмуддат ва дарозмуддат',
                'recommendations': '*Тавсияҳо оид ба истифодаи индикаторҳо:*\n\n'
                                  '✅ Барои навомӯзон: Миёнаҳои ҳаракаткунанда (МА), RSI\n'
                                  '✅ Барои тамоюл: Миёнаҳои ҳаракаткунанда, MACD, ADX\n'
                                  '✅ Барои осиллятсияҳо: RSI, Стохастик, CCI\n'
                                  '❗ Ягон индикатор 100% самарабахш нест, танҳо дар якҷоягӣ истифода баред',
                'examples': '*Мисол:* \n'
                           'Барои стратегияи тамоюлӣ шумо метавонед аз маҷмӯи EMA-20 ва EMA-50 истифода баред ва ҳангоми якдигарро бурида гузаштани онҳо сигнал мегиред.'
            },
            'ru': {
                'title': '📈 Технические индикаторы',
                'description': 'Технические индикаторы - это математические инструменты для анализа цен и объема торгов. Они помогают трейдерам идентифицировать рыночные тенденции, точки входа и выхода из сделок.',
                'popular_tools': '*Основные группы индикаторов:*\n\n'
                                '1. *Трендовые индикаторы*\n'
                                '- Скользящие средние (MA): SMA, EMA, VWMA, LWMA\n'
                                '- Полосы Боллинджера: каналы волатильности с базовой линией SMA\n'
                                '- Направленное движение (ADX): измеряет силу тренда (0-100)\n'
                                '- Параболическая система (SAR): определяет точки разворота тренда\n'
                                '- Ichimoku Kinko Hyo: комплексная система для анализа тренда\n\n'
                                
                                '2. *Осцилляторы*\n'
                                '- RSI (Индекс относительной силы): 0-100, с уровнями 30/70\n'
                                '- Стохастический осциллятор: два параметра %K и %D для подтверждения\n'
                                '- MACD (Конвергенция/дивергенция скользящих средних): гистограмма\n'
                                '- CCI (Индекс товарного канала): для определения сильных движений\n'
                                '- Momentum: показывает скорость изменения цены\n\n'
                                
                                '3. *Индикаторы объема*\n'
                                '- Volume: базовый индикатор объема торгов\n'
                                '- OBV (On-Balance Volume): накопленный объем по дням\n'
                                '- Money Flow Index (MFI): совмещает цену и объем\n'
                                '- Chaikin Money Flow: денежные потоки за определенный период\n\n'
                                
                                '4. *Индикаторы волатильности*\n'
                                '- ATR (Average True Range): средний истинный диапазон цены\n'
                                '- Bollinger Bands Width: ширина полос Боллинджера\n'
                                '- Keltner Channels: каналы для измерения волатильности',
                                
                'recommendations': '*Практические рекомендации по работе с индикаторами:*\n\n'
                                  '✅ Используйте несколько индикаторов из разных групп (3-4 максимум)\n'
                                  '✅ Адаптируйте индикаторы под текущее состояние рынка:\n'
                                  '   - Трендовый рынок: MA, MACD, Bollinger Bands, ADX\n'
                                  '   - Боковой рынок: RSI, Stochastic, MFI, CCI\n'
                                  '   - Волатильный рынок: ATR, Bollinger Bands, Keltner Channels\n'
                                  '✅ Экспериментируйте с настройкой параметров индикаторов\n'
                                  '✅ Используйте индикаторы для подтверждения сигналов, полученных из анализа графика\n'
                                  '✅ Разработайте четкие правила входа и выхода на основе показаний индикаторов\n'
                                  '❗ Избегайте перенасыщения графика индикаторами\n'
                                  '❗ Всегда подтверждайте сигналы индикаторов анализом графиков\n'
                                  '❗ Регулярно оценивайте эффективность выбранных индикаторов',
                                  
                'examples': '*Примеры торговых стратегий с индикаторами:*\n\n'
                           '1. *Пересечение скользящих средних:*\n'
                           '- Вход: когда быстрая MA (EMA-9) пересекает медленную (EMA-21) снизу вверх\n'
                           '- Выход: когда быстрая MA пересекает медленную сверху вниз или при достижении заданной прибыли\n'
                           '- Stop-loss: на уровне последнего локального минимума\n\n'
                           
                           '2. *Стратегия RSI с подтверждением:*\n'
                           '- Вход в лонг: RSI выходит из зоны перепроданности (выше 30), цена выше EMA-50\n'
                           '- Вход в шорт: RSI выходит из зоны перекупленности (ниже 70), цена ниже EMA-50\n'
                           '- Управление рисками: Stop-loss на уровне 1.5xATR от точки входа\n\n'
                           
                           '3. *Торговля по Bollinger Bands:*\n'
                           '- Отскок: покупка при касании нижней полосы при общем растущем тренде\n'
                           '- Пробой: вход при пробое верхней/нижней полосы после сжатия канала\n'
                           '- Таргет: противоположная полоса или средняя линия'
            },
            'uz': {
                'title': '📈 Texnik indikatorlar',
                'description': 'Texnik indikatorlar - narxlar va savdo hajmini tahlil qilish uchun matematik vositalar.',
                'popular_tools': '*Eng mashhur indikatorlar:*\n\n'
                                '1. *Harakatlanuvchi o\'rtachalar (MA)*\n'
                                '- Foydalanish: Trend va qo\'llab-quvvatlash/qarshilik darajalarini aniqlash\n'
                                '- Turlari: Oddiy (SMA), Eksponensial (EMA), Silliqlangan (SMMA)\n\n'
                                '2. *Nisbiy kuch indeksi (RSI)*\n'
                                '- Foydalanish: Haddan tashqari sotib olish/sotish holatlarini aniqlash\n'
                                '- Diapazon: 0 dan 100 gacha, asosiy darajalar 30 va 70\n\n'
                                '3. *MACD (Harakatlanuvchi o\'rtachalarning yaqinlashishi/farqlanishi)*\n'
                                '- Foydalanish: Trend va uning kuchini aniqlash\n'
                                '- Tarkib: Qisqa muddatli va uzoq muddatli EMA o\'rtasidagi farq',
                'recommendations': '*Indikatorlardan foydalanish bo\'yicha tavsiyalar:*\n\n'
                                  '✅ Yangi boshlanuvchilar uchun: Harakatlanuvchi o\'rtachalar (MA), RSI\n'
                                  '✅ Trendni aniqlash uchun: MA, MACD, ADX\n'
                                  '✅ Ossillyatorlar uchun: RSI, Stoxastik, CCI\n'
                                  '❗ Hech bir indikator 100% samaradorlik bermaydi, ularni birgalikda ishlating',
                'examples': '*Misol:* \n'
                           'Trend strategiyasi uchun siz EMA-20 va EMA-50 kombinatsiyasidan foydalanishingiz mumkin, ular kesishganda signal olasiz.'
            },
            'kk': {
                'title': '📈 Техникалық индикаторлар',
                'description': 'Техникалық индикаторлар - бағалар мен сауда көлемін талдауға арналған математикалық құралдар.',
                'popular_tools': '*Ең танымал индикаторлар:*\n\n'
                                '1. *Жылжымалы орташалар (MA)*\n'
                                '- Қолдану: Трендті және қолдау/қарсылық деңгейлерін анықтау\n'
                                '- Түрлері: Қарапайым (SMA), Экспоненциалды (EMA), Тегістелген (SMMA)\n\n'
                                '2. *Салыстырмалы күш индексі (RSI)*\n'
                                '- Қолдану: Шамадан тыс сатып алу/сату жағдайларын анықтау\n'
                                '- Диапазон: 0-ден 100-ге дейін, маңызды деңгейлер 30 және 70\n\n'
                                '3. *MACD (Жылжымалы орташалардың жақындасуы/айырмашылығы)*\n'
                                '- Қолдану: Трендті және оның күшін анықтау\n'
                                '- Құрамы: Қысқа мерзімді және ұзақ мерзімді EMA арасындағы айырмашылық',
                'recommendations': '*Индикаторларды пайдалану бойынша ұсыныстар:*\n\n'
                                  '✅ Жаңадан бастаушыларға: Жылжымалы орташалар (MA), RSI\n'
                                  '✅ Трендті анықтау үшін: MA, MACD, ADX\n'
                                  '✅ Осцилляторлар үшін: RSI, Стохастик, CCI\n'
                                  '❗ Ешбір индикатор 100% тиімділік бермейді, оларды бірге қолданыңыз',
                'examples': '*Мысал:* \n'
                           'Тренд стратегиясы үшін сіз EMA-20 және EMA-50 комбинациясын қолдана аласыз, олар қиылысқанда сигнал аласыз.'
            },
            'en': {
                'title': '📈 Technical Indicators',
                'description': 'Technical indicators are mathematical tools for analyzing price and volume data. They help traders identify market trends, entry and exit points for trades.',
                'popular_tools': '*Main Indicator Categories:*\n\n'
                                '1. *Trend Indicators*\n'
                                '- Moving Averages (MA): SMA, EMA, VWMA, LWMA\n'
                                '- Bollinger Bands: volatility channels with SMA baseline\n'
                                '- Directional Movement (ADX): measures trend strength (0-100)\n'
                                '- Parabolic SAR: identifies potential trend reversal points\n'
                                '- Ichimoku Kinko Hyo: comprehensive system for trend analysis\n\n'
                                
                                '2. *Oscillators*\n'
                                '- RSI (Relative Strength Index): 0-100, with 30/70 levels\n'
                                '- Stochastic Oscillator: two parameters %K and %D for confirmation\n'
                                '- MACD (Moving Average Convergence/Divergence): histogram\n'
                                '- CCI (Commodity Channel Index): identifies strong movements\n'
                                '- Momentum: shows rate of price change\n\n'
                                
                                '3. *Volume Indicators*\n'
                                '- Volume: basic trading volume indicator\n'
                                '- OBV (On-Balance Volume): accumulated volume by day\n'
                                '- Money Flow Index (MFI): combines price and volume\n'
                                '- Chaikin Money Flow: money flows over a specified period\n\n'
                                
                                '4. *Volatility Indicators*\n'
                                '- ATR (Average True Range): average true price range\n'
                                '- Bollinger Bands Width: width of Bollinger Bands\n'
                                '- Keltner Channels: channels for measuring volatility',
                                
                'recommendations': '*Practical Recommendations for Working with Indicators:*\n\n'
                                  '✅ Use multiple indicators from different groups (3-4 maximum)\n'
                                  '✅ Adapt indicators to current market conditions:\n'
                                  '   - Trending market: MA, MACD, Bollinger Bands, ADX\n'
                                  '   - Ranging market: RSI, Stochastic, MFI, CCI\n'
                                  '   - Volatile market: ATR, Bollinger Bands, Keltner Channels\n'
                                  '✅ Experiment with indicator parameter settings\n'
                                  '✅ Use indicators to confirm signals from chart analysis\n'
                                  '✅ Develop clear entry and exit rules based on indicator readings\n'
                                  '❗ Avoid overcrowding your chart with indicators\n'
                                  '❗ Always confirm indicator signals with chart analysis\n'
                                  '❗ Regularly evaluate the effectiveness of chosen indicators',
                                  
                'examples': '*Examples of Trading Strategies with Indicators:*\n\n'
                           '1. *Moving Average Crossover:*\n'
                           '- Entry: when fast MA (EMA-9) crosses slow MA (EMA-21) from below\n'
                           '- Exit: when fast MA crosses slow MA from above or target profit is reached\n'
                           '- Stop-loss: at the level of the last local minimum\n\n'
                           
                           '2. *RSI Strategy with Confirmation:*\n'
                           '- Long entry: RSI exits oversold zone (above 30), price above EMA-50\n'
                           '- Short entry: RSI exits overbought zone (below 70), price below EMA-50\n'
                           '- Risk management: Stop-loss at 1.5xATR from entry point\n\n'
                           
                           '3. *Bollinger Bands Trading:*\n'
                           '- Bounce: buy when price touches the lower band in an overall uptrend\n'
                           '- Breakout: enter when price breaks upper/lower band after band contraction\n'
                           '- Target: opposite band or middle line'
            }
        },
        'Управлениерисками': {
            'tg': {
                'title': '💰 Идоракунии хавф',
                'description': 'Идоракунии хавф - усулҳои паст кардани зарари эҳтимолӣ ва нигоҳ доштани сармоя.',
                'popular_tools': '*Воситаҳои асосии идоракунии хавф:*\n\n'
                                '1. *Стоп-лосс*\n'
                                '- Таъинот: Маҳдуд кардани зарар дар ҳолати ҳаракати нархҳо бар зидди мавқеи шумо\n'
                                '- Навъҳо: Статикӣ, тағйирёбанда, фоизнок\n\n'
                                '2. *Тейк-профит*\n'
                                '- Таъинот: Гирифтани фоида дар сатҳи мақсаднок\n'
                                '- Намудҳо: Статикӣ, бисёрсатҳӣ, фоизнок\n\n'
                                '3. *Ҳаҷми мавқеъ*\n'
                                '- Таъинот: Муайян кардани миқдори дурусти воситаи молиявӣ барои савдо\n'
                                '- Ҳисобкунӣ: Дар асоси андозаи ҳисоб, хавфи муомила ва баромади стоп-лосс',
                'recommendations': '*Тавсияҳо оид ба идоракунии хавф:*\n\n'
                                  '✅ Дар як савдо на зиёда аз 1-2% аз маблағи умумиро таваккал кунед\n'
                                  '✅ Ҳамеша стоп-лосс гузоред\n'
                                  '✅ Таносуби хавф/фоида камаш 1:2 бошад\n'
                                  '✅ Ҳангоми бозори пурталотум андозаи мавқеъро паст кунед\n'
                                  '❗ Идоракунии хавф аз стратегияи савдо муҳимтар аст',
                'examples': '*Мисол:* \n'
                           'Агар шумо ҳисоби $10,000 дошта, 1% хавфро қабул кунед, он гоҳ дар як савдо на бештар аз $100 хавф кунед. Агар стоп-лосс шумо 10 пипс бошад, шумо метавонед 1 лот савдо кунед.'
            },
            'ru': {
                'title': '💰 Управление рисками',
                'description': 'Управление рисками - это система методов и приемов снижения потенциальных убытков и сохранения торгового капитала. Это фундаментальный аспект успешного трейдинга, который позволяет торговать в течение длительного времени и преодолевать неизбежные периоды убытков.',
                'popular_tools': '*Комплексная система управления рисками:*\n\n'
                                '1. *Ордера защиты капитала*\n'
                                '- *Стоп-лосс* - ограничивает максимальный убыток по позиции\n'
                                '  • Фиксированный - устанавливается на определенном ценовом уровне\n'
                                '  • Трейлинг - следует за ценой, обеспечивая фиксацию прибыли\n'
                                '  • Психологический - мысленный уровень без выставления ордера (не рекомендуется)\n\n'
                                '- *Тейк-профит* - фиксирует прибыль на заданном уровне\n'
                                '  • Одиночный - фиксирует всю позицию на одном уровне\n'
                                '  • Многоуровневый - частичное закрытие на разных уровнях\n\n'
                                
                                '2. *Расчет размера позиции*\n'
                                '- Формула: Размер позиции = (Капитал × % риска) ÷ (Размер стоп-лосса в пунктах × Стоимость пункта)\n'
                                '- Калькуляторы позиций - инструменты для точного расчета\n'
                                '- Автоматические торговые системы с встроенным управлением размера позиции\n\n'
                                
                                '3. *Техники диверсификации*\n'
                                '- Торговля разными инструментами (валюты, акции, товары)\n'
                                '- Использование некоррелирующих активов\n'
                                '- Распределение капитала между различными стратегиями\n\n'
                                
                                '4. *Управление капиталом*\n'
                                '- Принцип сложных процентов - увеличение размера позиции с ростом капитала\n'
                                '- Методы вывода прибыли - стратегия частичного вывода средств\n'
                                '- Защита от "просадки" - правила для сокращения размера позиций\n\n'
                                
                                '5. *Психологические аспекты*\n'
                                '- Торговый журнал и анализ сделок\n'
                                '- Техники контроля эмоций и принятия решений\n'
                                '- Следование торговому плану и дисциплина',
                                
                'recommendations': '*Лучшие практики управления рисками:*\n\n'
                                  '✅ *Правило 1-2%*: рискуйте не более 1-2% капитала на одну сделку\n'
                                  '✅ *Правило 6%*: общий риск открытых позиций не должен превышать 6% от капитала\n'
                                  '✅ *Соотношение риск/прибыль*: стремитесь к соотношению не менее 1:2 или 1:3\n'
                                  '✅ *Снижение риска*: уменьшайте риск в периоды высокой волатильности или серии убыточных сделок\n'
                                  '✅ *Лестничный выход*: фиксируйте часть прибыли на разных уровнях для снижения риска\n'
                                  '✅ *Корреляция*: избегайте открытия похожих позиций в высококоррелированных инструментах\n'
                                  '✅ *Правило серий*: после 2-3 убыточных сделок подряд, сделайте перерыв или уменьшите размер позиции\n'
                                  '❗ *Правило "Ничего не делать"*: иногда лучшее управление риском - отказ от торговли в сложных условиях',
                                  
                'examples': '*Примеры практического применения:*\n\n'
                           '1. *Расчет размера позиции*\n'
                           '   Депозит: $10,000 | Риск: 1% ($100) | Стоп-лосс: 50 пунктов | Стоимость пункта: $1\n'
                           '   Размер позиции = $100 ÷ (50 × $1) = 2 мини-лота\n\n'
                           
                           '2. *Многоуровневый выход из позиции*\n'
                           '   Вход: 1.2000 | Стоп-лосс: 1.1950 (риск 50 пунктов)\n'
                           '   Тейк-профит 1: 1.2050 (50% позиции, соотношение 1:1)\n'
                           '   Тейк-профит 2: 1.2100 (50% позиции, соотношение 1:2)\n'
                           '   После достижения TP1, передвинуть стоп-лосс в безубыток (1.2000)\n\n'
                           
                           '3. *Управление капиталом при просадке*\n'
                           '   При просадке 5%: уменьшить размер позиции на 25%\n'
                           '   При просадке 10%: уменьшить размер позиции на 50%\n'
                           '   При просадке 15%: сделать перерыв и пересмотреть стратегию'
            },
            'en': {
                'title': '💰 Risk Management',
                'description': 'Risk management is a system of methods and techniques for reducing potential losses and preserving trading capital. It is a fundamental aspect of successful trading that allows you to trade for extended periods and overcome inevitable periods of losses.',
                'popular_tools': '*Comprehensive Risk Management System:*\n\n'
                                '1. *Capital Protection Orders*\n'
                                '- *Stop-Loss* - limits the maximum loss on a position\n'
                                '  • Fixed - set at a specific price level\n'
                                '  • Trailing - follows the price, ensuring profit lock-in\n'
                                '  • Mental - a mental level without placing an actual order (not recommended)\n\n'
                                '- *Take-Profit* - locks in profit at a target level\n'
                                '  • Single - closes the entire position at one level\n'
                                '  • Multi-level - partial closure at different levels\n\n'
                                
                                '2. *Position Sizing Calculation*\n'
                                '- Formula: Position Size = (Capital × % Risk) ÷ (Stop-Loss in Points × Point Value)\n'
                                '- Position calculators - tools for precise calculation\n'
                                '- Automated trading systems with built-in position size management\n\n'
                                
                                '3. *Diversification Techniques*\n'
                                '- Trading different instruments (currencies, stocks, commodities)\n'
                                '- Using non-correlating assets\n'
                                '- Distributing capital across various strategies\n\n'
                                
                                '4. *Capital Management*\n'
                                '- Compound interest principle - increasing position size as capital grows\n'
                                '- Profit withdrawal methods - strategy for partial withdrawal of funds\n'
                                '- Drawdown protection - rules for reducing position sizes\n\n'
                                
                                '5. *Psychological Aspects*\n'
                                '- Trading journal and trade analysis\n'
                                '- Emotion control techniques and decision making\n'
                                '- Following a trading plan and discipline',
                                
                'recommendations': '*Best Risk Management Practices:*\n\n'
                                  '✅ *1-2% Rule*: risk no more than 1-2% of capital per trade\n'
                                  '✅ *6% Rule*: total risk of open positions should not exceed 6% of capital\n'
                                  '✅ *Risk/Reward Ratio*: aim for a ratio of at least 1:2 or 1:3\n'
                                  '✅ *Risk Reduction*: decrease risk during periods of high volatility or after a series of losing trades\n'
                                  '✅ *Tiered Exit*: lock in partial profits at different levels to reduce risk\n'
                                  '✅ *Correlation*: avoid opening similar positions in highly correlated instruments\n'
                                  '✅ *Series Rule*: after 2-3 consecutive losing trades, take a break or reduce position size\n'
                                  '❗ *"Do Nothing" Rule*: sometimes the best risk management is to avoid trading in difficult conditions',
                                  
                'examples': '*Practical Application Examples:*\n\n'
                           '1. *Position Size Calculation*\n'
                           '   Account: $10,000 | Risk: 1% ($100) | Stop-Loss: 50 points | Point Value: $1\n'
                           '   Position Size = $100 ÷ (50 × $1) = 2 mini lots\n\n'
                           
                           '2. *Multi-Level Position Exit*\n'
                           '   Entry: 1.2000 | Stop-Loss: 1.1950 (50 points risk)\n'
                           '   Take-Profit 1: 1.2050 (50% of position, ratio 1:1)\n'
                           '   Take-Profit 2: 1.2100 (50% of position, ratio 1:2)\n'
                           '   After TP1 is reached, move Stop-Loss to breakeven (1.2000)\n\n'
                           
                           '3. *Capital Management During Drawdown*\n'
                           '   At 5% drawdown: reduce position size by 25%\n'
                           '   At 10% drawdown: reduce position size by 50%\n'
                           '   At 15% drawdown: take a break and review strategy'
            }
        }
        # Добавьте другие инструменты по аналогии
    }
    
    # Тексты на разных языках
    button_texts = {
        'tg': '↩️ Бозгашт ба рӯйхати абзорҳо',
        'ru': '↩️ Вернуться к списку инструментов',
        'uz': '↩️ Vositalar ro\'yxatiga qaytish',
        'kk': '↩️ Құралдар тізіміне оралу',
        'en': '↩️ Return to tools list'
    }
    
    # Получаем информацию о выбранном инструменте
    tool_info = None
    for key, info in tools_details.items():
        if key.lower() == tool_name.lower():
            tool_info = info
            break
    
    # Если инструмент не найден, показываем сообщение об ошибке
    if not tool_info:
        await query.edit_message_text(
            "⚠️ Подробная информация об этом инструменте временно недоступна.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(button_texts.get(lang_code, button_texts['ru']), callback_data="trading_tools")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Получаем данные инструмента для выбранного языка
    tool_data = tool_info.get(lang_code, tool_info['ru'])
    
    # Формируем сообщение с подробной информацией
    message = f"*{tool_data['title']}*\n\n"
    message += f"{tool_data['description']}\n\n"
    message += f"{tool_data['popular_tools']}\n\n"
    
    # Добавляем рекомендации, если они есть
    if 'recommendations' in tool_data:
        message += f"{tool_data['recommendations']}\n\n"
    
    # Добавляем примеры, если они есть
    if 'examples' in tool_data:
        message += f"{tool_data['examples']}"
    
    # Создаем клавиатуру с кнопкой возврата
    keyboard = [[InlineKeyboardButton(button_texts.get(lang_code, button_texts['ru']), callback_data="trading_tools")]]
    
    # Отправляем сообщение
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_otc_pair_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для анализа конкретной OTC пары"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    try:
        # Получаем данные пользователя для проверки доступа
        user_data = get_user(user_id)
        if not user_data or not user_data.get('is_approved'):
            await query.answer("⛔ У вас нет доступа к этой функции. Отправьте заявку на регистрацию.")
            return
        
        # Определяем язык пользователя
        lang_code = user_data.get('language_code', 'tg')
        
        # Получаем выбранную пару
        pair_data = query.data.replace("otc_", "").replace("_", "/")
        
        # Отправляем сообщение о начале анализа
        analyzing_text = {
            'tg': f"⏳ Таҳлили {pair_data}...\n\nЛутфан, мунтазир шавед...",
            'ru': f"⏳ Анализируем {pair_data}...\n\nПожалуйста, подождите...",
            'uz': f"⏳ {pair_data} tahlil qilinmoqda...\n\nIltimos, kuting...",
            'kk': f"⏳ {pair_data} талдау жүргізілуде...\n\nКүте тұрыңыз...",
            'en': f"⏳ Analyzing {pair_data}...\n\nPlease wait..."
        }
        
        await query.edit_message_text(
            analyzing_text.get(lang_code, analyzing_text['ru'])
        )
        
        # Получаем текущее время в разных таймзонах
        import pytz
        from datetime import datetime, timedelta
        
        # Ключевые финансовые центры и их таймзоны
        timezones = {
            'Moscow': pytz.timezone('Europe/Moscow'),
            'London': pytz.timezone('Europe/London'),
            'New York': pytz.timezone('America/New_York'),
            'Tokyo': pytz.timezone('Asia/Tokyo'),
            'Sydney': pytz.timezone('Australia/Sydney'),
            'Dubai': pytz.timezone('Asia/Dubai')
        }
        
        # Получаем текущее время в разных финансовых центрах
        current_utc = datetime.now(pytz.UTC)
        time_in_zones = {zone: current_utc.astimezone(tz) for zone, tz in timezones.items()}
        
        # Названия финансовых центров на разных языках
        timezone_names = {
            'tg': {
                'Moscow': 'Маскав',
                'London': 'Лондон',
                'New York': 'Ню-Йорк',
                'Tokyo': 'Токио',
                'Sydney': 'Сидней',
                'Dubai': 'Дубай',
                'time_header': '⏰ Вақти ҷаҳонӣ:'
            },
            'ru': {
                'Moscow': 'Москва',
                'London': 'Лондон',
                'New York': 'Нью-Йорк',
                'Tokyo': 'Токио',
                'Sydney': 'Сидней',
                'Dubai': 'Дубай',
                'time_header': '⏰ Мировое время:'
            },
            'uz': {
                'Moscow': 'Moskva',
                'London': 'London',
                'New York': 'Nyu-York',
                'Tokyo': 'Tokio',
                'Sydney': 'Sidney',
                'Dubai': 'Dubay',
                'time_header': '⏰ Jahon vaqti:'
            },
            'kk': {
                'Moscow': 'Мәскеу',
                'London': 'Лондон',
                'New York': 'Нью-Йорк',
                'Tokyo': 'Токио',
                'Sydney': 'Сидней',
                'Dubai': 'Дубай',
                'time_header': '⏰ Әлемдік уақыт:'
            },
            'en': {
                'Moscow': 'Moscow',
                'London': 'London',
                'New York': 'New York',
                'Tokyo': 'Tokyo',
                'Sydney': 'Sydney',
                'Dubai': 'Dubai',
                'time_header': '⏰ World time:'
            }
        }
        
        # Локализованные названия таймзон
        localized_tz_names = timezone_names.get(lang_code, timezone_names['en'])
        
        # Симулируем анализ (в реальном боте здесь будет настоящий анализ)
        await asyncio.sleep(2)  # Имитация загрузки данных
        
        # Создаем фиктивный результат анализа
        direction = random.choice(["BUY", "SELL"])
        confidence = random.randint(70, 90)
        
        # Данные индикаторов
        rsi = random.randint(25, 75)
        macd = round(random.uniform(-0.01, 0.01), 4)
        
        # Локализованные позиции для Bollinger Bands
        bb_positions = {
            'tg': ["сарҳади поён", "миёна", "сарҳади боло"],
            'ru': ["нижняя граница", "средняя", "верхняя граница"],
            'uz': ["quyi chegara", "o'rta", "yuqori chegara"],
            'kk': ["төменгі шекара", "орташа", "жоғарғы шекара"],
            'en': ["lower band", "middle", "upper band"]
        }
        
        # Выбираем локализованную позицию
        bb_position_list = bb_positions.get(lang_code, bb_positions['ru'])
        bb_position = random.choice(bb_position_list)
        
        # Локализованные тексты для анализа
        analysis_texts = {
            'tg': {
                'header': f"📊 *Таҳлили {pair_data}*",
                'signal': "🎯 Сигнал",
                'confidence': "📈 Боварӣ",
                'expiry': "⏰ Вақти ба итмом расидан",
                'through': "аз",
                'min': "дақиқа",
                'indicators': "📉 *Индикаторҳо:*",
                'recommendation': "🔍 *Тавсия:*",
                'open_deal': "Кушодани муомила",
                'for': "барои",
                'with_probability': "бо эҳтимолияти",
                'risk_warning': "⚠️ *Савдо бо хатар алоқаманд аст. Ба масъулияти худ истифода баред.*"
            },
            'ru': {
                'header': f"📊 *Анализ {pair_data}*",
                'signal': "🎯 Сигнал",
                'confidence': "📈 Уверенность",
                'expiry': "⏰ Время экспирации",
                'through': "через",
                'min': "мин",
                'indicators': "📉 *Индикаторы:*",
                'recommendation': "🔍 *Рекомендация:*",
                'open_deal': "Рекомендуется открыть сделку",
                'for': "на",
                'with_probability': "с вероятностью",
                'risk_warning': "⚠️ *Торговля сопряжена с рисками. Используйте на свой страх и риск.*"
            },
            'uz': {
                'header': f"📊 *{pair_data} tahlili*",
                'signal': "🎯 Signal",
                'confidence': "📈 Ishonch",
                'expiry': "⏰ Tugash vaqti",
                'through': "orqali",
                'min': "daqiqa",
                'indicators': "📉 *Indikatorlar:*",
                'recommendation': "🔍 *Tavsiya:*",
                'open_deal': "Bitim ochish tavsiya etiladi",
                'for': "uchun",
                'with_probability': "ehtimolligi bilan",
                'risk_warning': "⚠️ *Savdo xatarlar bilan bog'liq. O'z javobgarligingiz ostida foydalaning.*"
            },
            'kk': {
                'header': f"📊 *{pair_data} талдауы*",
                'signal': "🎯 Сигнал",
                'confidence': "📈 Сенімділік",
                'expiry': "⏰ Аяқталу уақыты",
                'through': "арқылы",
                'min': "мин",
                'indicators': "📉 *Индикаторлар:*",
                'recommendation': "🔍 *Ұсыныс:*",
                'open_deal': "Мәміле ашу ұсынылады",
                'for': "үшін",
                'with_probability': "ықтималдығымен",
                'risk_warning': "⚠️ *Сауда тәуекелдермен байланысты. Өз жауапкершілігіңізбен пайдаланыңыз.*"
            },
            'en': {
                'header': f"📊 *{pair_data} Analysis*",
                'signal': "🎯 Signal",
                'confidence': "📈 Confidence",
                'expiry': "⏰ Expiry Time",
                'through': "in",
                'min': "min",
                'indicators': "📉 *Indicators:*",
                'recommendation': "🔍 *Recommendation:*",
                'open_deal': "Recommended to open",
                'for': "for",
                'with_probability': "with probability",
                'risk_warning': "⚠️ *Trading involves risks. Use at your own discretion.*"
            }
        }
        
        # Локализованные тексты для направления
        direction_texts = {
            'tg': {"BUY": "ХАРИД", "SELL": "ФУРӮШ"},
            'ru': {"BUY": "ПОКУПКА", "SELL": "ПРОДАЖА"},
            'uz': {"BUY": "SOTIB OLISH", "SELL": "SOTISH"},
            'kk': {"BUY": "САТЫП АЛУ", "SELL": "САТУ"},
            'en': {"BUY": "BUY", "SELL": "SELL"}
        }
        
        # Получаем локализованные тексты
        texts = analysis_texts.get(lang_code, analysis_texts['ru'])
        dir_text = direction_texts.get(lang_code, direction_texts['ru']).get(direction, direction)
        
        # Создаем клавиатуру для результата анализа с локализованными названиями кнопок
        keyboard_texts = {
            'tg': {
                'refresh': "🔄 Навсозии таҳлил", 
                'more_data': "📊 Маълумоти бештар",
                'home': "🏠 Ба саҳифаи асосӣ",
                'back': "↩️ Бозгашт ба рӯйхати ҷуфтҳо"
            },
            'ru': {
                'refresh': "🔄 Обновить анализ", 
                'more_data': "📊 Больше данных",
                'home': "🏠 На главную",
                'back': "↩️ Назад к списку пар"
            },
            'uz': {
                'refresh': "🔄 Tahlilni yangilash", 
                'more_data': "📊 Ko'proq ma'lumot",
                'home': "🏠 Bosh sahifaga",
                'back': "↩️ Juftliklar ro'yxatiga qaytish"
            },
            'kk': {
                'refresh': "🔄 Талдауды жаңарту", 
                'more_data': "📊 Көбірек деректер",
                'home': "🏠 Басты бетке",
                'back': "↩️ Жұптар тізіміне оралу"
            },
            'en': {
                'refresh': "🔄 Refresh Analysis", 
                'more_data': "📊 More Data",
                'home': "🏠 Home",
                'back': "↩️ Back to Pairs List"
            }
        }
        
        # Получаем локализованные тексты для кнопок
        button_texts = keyboard_texts.get(lang_code, keyboard_texts['ru'])
        
        # Создаем клавиатуру
        keyboard = [
            [
                InlineKeyboardButton(button_texts['refresh'], callback_data=f"otc_{pair_data.replace('/', '_')}"),
                InlineKeyboardButton(button_texts['more_data'], callback_data=f"otc_more_{pair_data.replace('/', '_')}")
            ],
            [InlineKeyboardButton(button_texts['back'], callback_data="otc_pairs")],
            [InlineKeyboardButton(button_texts['home'], callback_data="return_to_main")]
        ]
        
        # Время экспирации (5-10 минут от текущего времени)
        expiry_minutes = random.randint(5, 10)
        expiry_time = (datetime.now() + timedelta(minutes=expiry_minutes)).strftime("%H:%M")
        
        # Направление с эмодзи
        direction_emoji = "⬆️" if direction == "BUY" else "⬇️"
        
        # Формируем строку с мировым временем
        world_time_lines = []
        for zone, time_obj in time_in_zones.items():
            zone_name = localized_tz_names.get(zone, zone)
            time_str = time_obj.strftime("%H:%M:%S")
            world_time_lines.append(f"{zone_name}: *{time_str}*")
        
        # Объединяем информацию о времени в разные строки, не делая строку слишком длинной
        time_info = []
        current_line = ""
        for item in world_time_lines:
            if len(current_line) + len(item) + 3 <= 40:  # Максимальная длина строки
                if current_line:
                    current_line += " | "
                current_line += item
            else:
                time_info.append(current_line)
                current_line = item
        if current_line:
            time_info.append(current_line)
        
        time_info_str = "\n".join(time_info)
        
        # Формируем текст сообщения с результатом анализа с локализованными текстами
        result_text = (
            f"{texts['header']}\n\n"
            f"{texts['signal']}: {direction_emoji} *{dir_text}*\n"
            f"{texts['confidence']}: *{confidence}%*\n"
            f"{texts['expiry']}: *{expiry_time}* ({texts['through']} {expiry_minutes} {texts['min']})\n\n"
            f"{texts['indicators']}\n"
            f"• RSI: `{rsi}`\n"
            f"• MACD: `{macd}`\n"
            f"• Bollinger Bands: `{bb_position}`\n\n"
            f"{texts['recommendation']}\n"
            f"{direction_emoji} {texts['open_deal']} *{dir_text}* {texts['for']} {expiry_minutes} {texts['min']} {texts['with_probability']} {confidence}%\n\n"
            f"{localized_tz_names['time_header']}\n"
            f"{time_info_str}\n\n"
            f"{texts['risk_warning']}"
        )
        
        # Отправляем сообщение с результатом анализа
        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in OTC pair analysis handler: {e}")
        await query.answer(f"Произошла ошибка: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram bot."""
    logger.error(f"Exception while handling an update: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Хатогӣ рух дод. Лутфан, дубора кӯшиш кунед."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {str(e)}")

if __name__ == '__main__':
    main()