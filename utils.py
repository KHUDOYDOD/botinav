from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CURRENCY_PAIRS, LANGUAGES, MESSAGES, forex_pairs, crypto_pairs

def get_language_keyboard():
    keyboard = []
    for i in range(0, len(LANGUAGES), 2):
        row = []
        for lang_code in list(LANGUAGES.keys())[i:i+2]:
            lang_name = LANGUAGES[lang_code]
            row.append(InlineKeyboardButton(lang_name, callback_data=f"lang_{lang_code}"))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def get_currency_keyboard(current_lang='tg', user_data=None):
    """Create keyboard with currency pairs and language change button
    Adds admin/moderator buttons if the user has appropriate permissions"""
    keyboard = []
    row = []
    
    # Add admin/moderator panel buttons if the user has appropriate permissions
    if user_data:
        admin_buttons = []
        if user_data.get('is_admin'):
            admin_buttons.append(InlineKeyboardButton("👑 Панель администратора", callback_data="admin_panel"))
        if user_data.get('is_moderator'):
            admin_buttons.append(InlineKeyboardButton("🛡️ Панель модератора", callback_data="moderator_panel"))
        
        if admin_buttons:
            # Add admin/moderator buttons at the top
            for button in admin_buttons:
                keyboard.append([button])

    # Add regular currency pairs button first
    keyboard.append([InlineKeyboardButton("💱 Все валютные пары", callback_data="regular_pairs")])

    # Add language change button
    lang_button_text = {
        'tg': '🔄 Забон / Язык / Language',
        'ru': '🔄 Язык / Language / Забон',
        'uz': '🔄 Til / Language / Забон',
        'kk': '🔄 Тіл / Language / Забон',
        'en': '🔄 Language / Забон / Язык'
    }

    # Return to main button text
    return_button_text = {
        'tg': '🏠 Ба саҳифаи аввал',
        'ru': '🏠 На главную',
        'uz': '🏠 Bosh sahifaga',
        'kk': '🏠 Басты бетке',
        'en': '🏠 Return to Main'
    }

    # Add OTC Pocket Option section
    otc_button_text = {
        'tg': '📱 OTC Pocket Option',
        'ru': '📱 OTC Pocket Option',
        'uz': '📱 OTC Pocket Option',
        'kk': '📱 OTC Pocket Option',
        'en': '📱 OTC Pocket Option'
    }
    
    # Add OTC button
    keyboard.append([
        InlineKeyboardButton(
            otc_button_text.get(current_lang, otc_button_text['tg']),
            callback_data="otc_pairs"
        )
    ])
    
    # Add Trading Education section with header
    trading_education_header = {
        'tg': '📚 Омӯзиши трейдинг',
        'ru': '📚 Обучение трейдингу',
        'uz': '📚 Treyding ta\'limi',
        'kk': '📚 Трейдинг бойынша біліктілік',
        'en': '📚 Trading Education'
    }
    keyboard.append([
        InlineKeyboardButton(
            trading_education_header.get(current_lang, trading_education_header['ru']),
            callback_data="trading_education"
        )
    ])
    
    # Trading books button text
    trading_books_text = {
        'tg': '📚 Китобҳо барои трейдинг',
        'ru': '📚 Книги по трейдингу',
        'uz': '📚 Treyding bo\'yicha kitoblar',
        'kk': '📚 Трейдинг бойынша кітаптар',
        'en': '📚 Trading Books'
    }
    
    # Learning trading from scratch button text
    trading_beginner_text = {
        'tg': '🔰 Омӯзиши трейдинг аз сифр',
        'ru': '🔰 Обучение трейдингу с нуля',
        'uz': '🔰 Treyding bo\'yicha boshlang\'ich ta\'lim',
        'kk': '🔰 Трейдингті нөлден үйрену',
        'en': '🔰 Trading for Beginners'
    }
    
    # Add Trading Education first row
    keyboard.append([
        InlineKeyboardButton(
            trading_books_text.get(current_lang, trading_books_text['tg']),
            callback_data="trading_books"
        ),
        InlineKeyboardButton(
            trading_beginner_text.get(current_lang, trading_beginner_text['tg']),
            callback_data="trading_beginner"
        )
    ])
    
    # Trading strategies button text
    trading_strategies_text = {
        'tg': '📈 Стратегияҳои трейдинг',
        'ru': '📈 Стратегии трейдинга',
        'uz': '📈 Treyding strategiyalari',
        'kk': '📈 Трейдинг стратегиялары',
        'en': '📈 Trading Strategies'
    }
    
    # Trading tools button text
    trading_tools_text = {
        'tg': '🧰 Абзорҳои трейдинг',
        'ru': '🧰 Инструменты трейдинга',
        'uz': '🧰 Treyding vositalari',
        'kk': '🧰 Трейдинг құралдары',
        'en': '🧰 Trading Tools'
    }
    
    # Add Trading Education second row
    keyboard.append([
        InlineKeyboardButton(
            trading_strategies_text.get(current_lang, trading_strategies_text['tg']),
            callback_data="trading_strategies"
        ),
        InlineKeyboardButton(
            trading_tools_text.get(current_lang, trading_tools_text['tg']),
            callback_data="trading_tools"
        )
    ])
    
    # Add language and return buttons
    keyboard.append([
        InlineKeyboardButton(
            lang_button_text.get(current_lang, lang_button_text['tg']),
            callback_data="change_language"
        )
    ])
    keyboard.append([
        InlineKeyboardButton(
            return_button_text.get(current_lang, return_button_text['tg']),
            callback_data="return_to_main"
        )
    ])

    return InlineKeyboardMarkup(keyboard)

def escape_markdown(text):
    special_chars = ['_', '*', '`', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_signal_message(pair, analysis_result, lang_code='tg'):
    messages = MESSAGES.get(lang_code, MESSAGES['tg'])
    if 'error' in analysis_result:
        return analysis_result['error']

    current_price = analysis_result.get('current_price')
    timeframes = analysis_result.get('timeframes', {})

    result_parts = [
        f"💎 {messages['PAIR_HEADER'].format(escape_markdown(pair))}",
        f"⌚ {escape_markdown(datetime.now().strftime('%H:%M:%S'))}",
        f"💵 {escape_markdown(messages['CURRENT_PRICE'])}: `{current_price:.4f}`\n"
    ]

    for minutes, data in sorted(timeframes.items()):
        if not data or not isinstance(data, dict):
            continue

        signal = data.get('signal', 'NEUTRAL')
        change = data.get('change', 0)
        indicators = data.get('indicators', {})
        confidence = indicators.get('confidence', 50)
        expiration = indicators.get('expiration', minutes)
        rsi = indicators.get('rsi', 0)
        macd = indicators.get('macd', 0)
        bb_position = indicators.get('bb_position', 'normal')

        signal_text = messages['SIGNALS'][signal]
        bb_emoji = '↘️' if bb_position == 'oversold' else '↗️' if bb_position == 'overbought' else '↔️'

        timeframe_text = f"""
📊 {escape_markdown(messages['TIMEFRAME'].format(minutes))}
{signal_text}

{'🟢' if change > 0 else '🔴' if change < 0 else '⚪'} _Изменение:_ `{abs(change):.2f}%`
⏰ {escape_markdown(messages['EXPIRATION'])}: `{expiration} {escape_markdown(messages['MINUTES'])}`
📈 {escape_markdown(messages['CONFIDENCE'])}: `{confidence}%`

📉 RSI: `{rsi:.1f}`
📊 MACD: `{macd:.4f}`
{bb_emoji} BB: `{bb_position}`
"""
        result_parts.append(timeframe_text)

    return "\n".join(result_parts)