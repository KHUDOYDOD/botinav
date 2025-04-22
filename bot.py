import logging
import hashlib
import time
import os
import sys
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
                          "🔹 *Торговый Аналитический Бот* - ваш профессиональный помощник в мире финансовых рынков.\n\n" \
                          "✅ Более 30+ валютных пар и криптовалют\n" \
                          "✅ Высокоточные торговые сигналы\n" \
                          "✅ Профессиональные графики и индикаторы\n" \
                          "✅ Аналитика на различных таймфреймах\n\n" \
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
        
        # Аналитические функции и настройки
        [InlineKeyboardButton("📊 Статистика бота", callback_data="admin_stats")],
        [
            InlineKeyboardButton("📈 Анализ активности", callback_data="admin_activity"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")
        ],
        
        # Дополнительные функции управления
        [
            InlineKeyboardButton("📊 Управление сигналами", callback_data="admin_signals"),
            InlineKeyboardButton("👤 Аналитика пользователей", callback_data="admin_user_analytics")
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
        
        # Безопасность и обслуживание
        [
            InlineKeyboardButton("🔐 Сменить пароль", callback_data="admin_change_password"),
            InlineKeyboardButton("🔄 Обновить БД", callback_data="admin_update_db")
        ],
        
        # Разное
        [
            InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language"),
            InlineKeyboardButton("ℹ️ О боте", callback_data="admin_about")
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
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_message_to_user),
                        CallbackQueryHandler(admin_send_message_to_user)
                    ]
                },
                fallbacks=[CommandHandler("start", start)]
            )
            application.add_handler(admin_conv_handler)
            
            # Обработчик кнопок действий с пользователями
            application.add_handler(CallbackQueryHandler(handle_admin_action, pattern=r"^(approve|reject)_\d+$"))
            
            # Обработчик текстовых сообщений
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
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