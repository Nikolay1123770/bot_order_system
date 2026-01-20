from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from keyboards import kb
from config import TARIFFS, BUTTONS, ORDER_STATUSES, ADMIN_IDS
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовое сообщение"""
    user = update.effective_user
    
    # Регистрируем пользователя
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Проверяем, администратор ли
    is_admin = db.is_admin(user.id)
    
    text = (
        f"👋 <b>Добро пожаловать, {user.first_name}!</b>\n\n"
        "🤖 <b>BotFactory</b> — профессиональная разработка "
        "Telegram-ботов и веб-сайтов\n\n"
        "🎯 <b>Наши услуги:</b>\n"
        "• Telegram боты - от 1,000 ₽\n"
        "• Веб-сайты - от 2,500 ₽\n"
        "• API интеграции - от 500 ₽\n"
        "• Индивидуальные проекты\n\n"
        "💎 <b>Преимущества:</b>\n"
        "✅ Быстрая разработка\n"
        "✅ Доступные цены\n"
        "✅ Гарантия качества\n"
        "✅ Поддержка 24/7\n\n"
        "Выберите действие из меню:"
    )
    
    reply_markup = kb.main_menu(is_admin)
    
    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def show_tariffs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать тарифы"""
    query = update.callback_query
    await query.answer()
    
    text = "💰 <b>Наш прайс-лист:</b>\n\n"
    
    # Группируем по категориям
    text += "🤖 <b>TELEGRAM БОТЫ:</b>\n\n"
    
    # Боты
    for key in ['bot_simple', 'bot_medium', 'bot_complex']:
        tariff = TARIFFS[key]
        text += f"<b>{tariff['name']}</b>\n"
        text += f"💵 {tariff['price_text']}\n"
        for feature in tariff['features']:
            text += f"  {feature}\n"
        text += "\n"
    
    text += "─" * 30 + "\n\n"
    
    # Сайты
    text += "🌐 <b>ВЕБ-САЙТЫ:</b>\n\n"
    tariff = TARIFFS['website']
    text += f"<b>{tariff['name']}</b>\n"
    text += f"💵 {tariff['price_text']}\n"
    for feature in tariff['features']:
        text += f"  {feature}\n"
    text += "\n"
    
    text += "─" * 30 + "\n\n"
    
    # API
    text += "🔌 <b>ДОПОЛНИТЕЛЬНО:</b>\n\n"
    tariff = TARIFFS['api_integration']
    text += f"<b>{tariff['name']}</b>\n"
    text += f"💵 {tariff['price_text']}\n"
    for feature in tariff['features']:
        text += f"  {feature}\n"
    text += "\n"
    
    text += "─" * 30 + "\n\n"
    
    text += (
        "💡 <b>Важно:</b>\n"
        "• Цена финальная, без скрытых платежей\n"
        "• Подключение API оплачивается отдельно\n"
        "• Сложные интеграции обсуждаются индивидуально\n"
        "• Предоплата 50%, остаток после сдачи\n\n"
        "📞 Для заказа нажмите кнопку ниже"
    )
    
    keyboard = [
        [InlineKeyboardButton(BUTTONS['order'], callback_data='order')],
        [InlineKeyboardButton(BUTTONS['back'], callback_data='start')]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать заказы пользователя"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    orders = db.get_user_orders(user_id)
    
    if not orders:
        text = (
            "📦 <b>Ваши заказы</b>\n\n"
            "У вас пока нет заказов.\n\n"
            "Создайте первый заказ, чтобы начать работу с нами!"
        )
        keyboard = [
            [InlineKeyboardButton(BUTTONS['order'], callback_data='order')],
            [InlineKeyboardButton(BUTTONS['back'], callback_data='start')]
        ]
    else:
        text = f"📦 <b>Ваши заказы ({len(orders)}):</b>\n\n"
        
        for order in orders[:10]:  # Показываем последние 10
            status = ORDER_STATUSES.get(order['status'], order['status'])
            text += (
                f"🔹 <b>Заказ #{order['order_number']}</b>\n"
                f"   Тариф: {order['tariff']}\n"
                f"   Статус: {status}\n"
                f"   Дата: {order['created_at'][:10]}\n\n"
            )
        
        keyboard = []
        for order in orders[:10]:
            keyboard.append([InlineKeyboardButton(
                f"#{order['order_number']} - {ORDER_STATUSES.get(order['status'])}",
                callback_data=f"view_order_{order['id']}"
            )])
        keyboard.append([InlineKeyboardButton(BUTTONS['back'], callback_data='start')])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детали заказа"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    order = db.get_order(order_id)
    
    if not order:
        await query.edit_message_text("❌ Заказ не найден")
        return
    
    status = ORDER_STATUSES.get(order['status'], order['status'])
    
    text = (
        f"📋 <b>Заказ #{order['order_number']}</b>\n\n"
        f"<b>Статус:</b> {status}\n"
        f"<b>Тариф:</b> {order['tariff']}\n"
        f"<b>Бюджет:</b> {order['budget']}\n"
        f"<b>Дата создания:</b> {order['created_at'][:16]}\n"
        f"<b>Последнее обновление:</b> {order['updated_at'][:16]}\n\n"
        f"<b>Описание:</b>\n{order['description']}\n\n"
    )
    
    if order['admin_comment']:
        text += f"💬 <b>Комментарий:</b>\n{order['admin_comment']}\n\n"
    
    # Проверяем, есть ли сообщения
    messages = db.get_order_messages(order_id)
    if messages:
        text += f"💬 <b>Последние сообщения:</b> {len(messages)} шт.\n\n"
        # Показываем последнее сообщение
        last_msg = messages[0]
        sender = "👨‍💼 Менеджер" if last_msg['is_admin'] else "👤 Вы"
        text += f"{sender} ({last_msg['created_at'][:16]}):\n{last_msg['message'][:100]}"
        if len(last_msg['message']) > 100:
            text += "...\n\n"
        else:
            text += "\n\n"
    
    await query.edit_message_text(
        text,
        reply_markup=kb.order_actions(order_id),
        parse_mode='HTML'
    )

async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """О компании"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "<b>ℹ️ О BotFactory</b>\n\n"
        "Мы — команда профессиональных разработчиков, "
        "специализирующихся на создании Telegram-ботов и веб-сайтов.\n\n"
        "📊 <b>Наши достижения:</b>\n"
        "✅ 500+ выполненных проектов\n"
        "✅ 98% довольных клиентов\n"
        "✅ Работаем с 2021 года\n"
        "✅ Средний рейтинг 4.9/5.0\n\n"
        "🎯 <b>Специализация:</b>\n"
        "• Telegram боты любой сложности\n"
        "• Корпоративные сайты\n"
        "• Интернет-магазины\n"
        "• Landing Page\n"
        "• API интеграции\n"
        "• Автоматизация бизнеса\n\n"
        "💼 <b>Мы работаем с:</b>\n"
        "• Стартапами\n"
        "• Малым и средним бизнесом\n"
        "• Крупными компаниями\n"
        "• Частными лицами\n\n"
        "💰 <b>Ценовая политика:</b>\n"
        "• Честные цены без накруток\n"
        "• Оплата по факту выполнения\n"
        "• Возможна рассрочка\n"
        "• Бесплатные консультации\n"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=kb.back_button(),
        parse_mode='HTML'
    )

async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поддержка"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "<b>💬 Служба поддержки</b>\n\n"
        "Мы всегда на связи! Выберите удобный способ:\n\n"
        "📱 <b>Telegram:</b> @botfactory_support\n"
        "📧 <b>Email:</b> support@botfactory.ru\n\n"
        "⏰ <b>Режим работы:</b>\n"
        "Пн-Пт: 9:00 - 21:00 (МСК)\n"
        "Сб-Вс: 10:00 - 18:00 (МСК)\n\n"
        "⚡ Среднее время ответа: 15 минут\n"
        "🎯 В нерабочее время отвечаем до 2 часов\n\n"
        "💡 <b>Совет:</b> Для быстрого ответа пишите в Telegram"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=kb.back_button(),
        parse_mode='HTML'
    )

async def show_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать отзывы"""
    query = update.callback_query
    await query.answer()
    
    reviews = db.get_published_reviews(limit=5)
    
    if not reviews:
        text = "⭐ <b>Отзывы</b>\n\nОтзывов пока нет. Станьте первым!"
    else:
        text = "⭐ <b>Отзывы наших клиентов:</b>\n\n"
        
        for review in reviews:
            stars = "⭐" * review['rating']
            name = review['first_name'] or review['username'] or "Клиент"
            text += (
                f"{stars} <b>{name}</b>\n"
                f"{review['text']}\n"
                f"<i>{review['created_at'][:10]}</i>\n\n"
            )
    
    await query.edit_message_text(
        text,
        reply_markup=kb.back_button(),
        parse_mode='HTML'
    )

async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Портфолио"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "📊 <b>Наше портфолио</b>\n\n"
        "🎯 <b>Примеры выполненных проектов:</b>\n\n"
        
        "🤖 <b>TELEGRAM БОТЫ:</b>\n\n"
        
        "1️⃣ <b>@ShopBot</b> - Интернет-магазин\n"
        "   • Каталог товаров с фото\n"
        "   • Корзина и оформление заказа\n"
        "   • Админ-панель для управления\n"
        "   • Интеграция оплаты\n"
        "   💰 2,500 ₽\n\n"
        
        "2️⃣ <b>@BookingBot</b> - Запись клиентов\n"
        "   • Календарь свободных слотов\n"
        "   • Автоматические напоминания\n"
        "   • CRM для мастера\n"
        "   💰 2,000 ₽\n\n"
        
        "3️⃣ <b>@MenuBot</b> - Меню ресторана\n"
        "   • Красивый каталог блюд\n"
        "   • Онлайн заказ\n"
        "   • Уведомления кухне\n"
        "   💰 1,500 ₽\n\n"
        
        "🌐 <b>ВЕБ-САЙТЫ:</b>\n\n"
        
        "1️⃣ <b>Корпоративный сайт</b>\n"
        "   • 5 страниц + блог\n"
        "   • Адаптивный дизайн\n"
        "   • Форма обратной связи\n"
        "   💰 2,500 ₽\n\n"
        
        "2️⃣ <b>Landing Page</b>\n"
        "   • Продающий дизайн\n"
        "   • Интеграция с CRM\n"
        "   • SEO оптимизация\n"
        "   💰 2,500 ₽\n\n"
        
        "📸 <b>Больше примеров:</b>\n"
        "Telegram: @botfactory_portfolio\n"
        "GitHub: github.com/botfactory\n\n"
        "💡 Хотите так же? Жмите «Заказать»!"
    )
    
    keyboard = [
        [InlineKeyboardButton(BUTTONS['order'], callback_data='order')],
        [InlineKeyboardButton(BUTTONS['back'], callback_data='start')]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def process_user_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений пользователя"""
    message_text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Проверяем, инициирован ли чат
    active_chat = context.user_data.get('active_chat')
    
    if active_chat and active_chat.get('initiated'):
        # Если чат инициирован через кнопку, используем сохраненный order_id
        order_id = active_chat['order_id']
        order = db.get_order(order_id)
        
        if not order:
            await update.message.reply_text("❌ Заказ не найден. Пожалуйста, создайте новый.")
            context.user_data.pop('active_chat', None)
            return
    else:
        # Проверяем, есть ли активные заказы у пользователя
        user_orders = db.get_user_orders(user_id)
        
        if not user_orders:
            # Если нет заказов, считаем это обычным сообщением
            await update.message.reply_text(
                "Для начала общения с менеджером, пожалуйста, создайте заказ:\n\n"
                "/start → 🛒 Заказать"
            )
            return
        
        # Берем самый свежий заказ для ответа
        order = user_orders[0]
        order_id = order['id']
    
    try:
        # Сохраняем сообщение в БД
        db.add_message(
            order_id=order_id,
            user_id=user_id,
            message=message_text,
            is_admin=False
        )
        
        # Уведомляем пользователя о принятии сообщения
        reply_text = (
            "✅ <b>Сообщение отправлено</b>\n\n"
            f"Ваше сообщение по заказу #{order['order_number']} "
            "получено и будет передано менеджеру. "
            "Он ответит вам в ближайшее время."
        )
        
        keyboard = [
            [InlineKeyboardButton("👁 Посмотреть заказ", callback_data=f"view_order_{order_id}")],
            [InlineKeyboardButton("📦 Все заказы", callback_data="my_orders")]
        ]
        
        await update.message.reply_text(
            reply_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
        # Уведомляем всех админов
        admin_text = (
            f"📨 <b>НОВОЕ СООБЩЕНИЕ ОТ КЛИЕНТА</b>\n\n"
            f"👤 <b>Клиент:</b> {order['name']}\n"
            f"📋 <b>Заказ:</b> #{order['order_number']}\n"
            f"💬 <b>Сообщение:</b>\n\n"
            f"{message_text}\n\n"
            f"Отправлено: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        admin_keyboard = [
            [InlineKeyboardButton("✏️ Ответить", callback_data=f"admin_message_{order_id}")],
            [InlineKeyboardButton("📋 Открыть заказ", callback_data=f"admin_order_{order_id}")]
        ]
        
        # Отправляем всем админам
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    reply_markup=InlineKeyboardMarkup(admin_keyboard),
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления админа {admin_id}: {e}")
        
        logger.info(
            f"Пользователь {user_id} отправил сообщение по заказу #{order['order_number']}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения пользователя: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке сообщения. Попробуйте позже."
        )

async def start_direct_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало прямого чата с менеджером (без привязки к заказу)"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Проверяем, есть ли у пользователя заказы
    user_orders = db.get_user_orders(user.id)
    
    if not user_orders:
        # У пользователя нет заказов, предлагаем создать
        text = (
            "💬 <b>Чат с менеджером</b>\n\n"
            "Чтобы начать чат с менеджером, пожалуйста, "
            "сначала создайте заказ. Это поможет нам лучше "
            "понять ваши потребности.\n\n"
            "Вы можете создать заказ, нажав на кнопку ниже:"
        )
        
        keyboard = [
            [InlineKeyboardButton("🛒 Создать заказ", callback_data='order')],
            [InlineKeyboardButton("◀️ Назад", callback_data='start')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        return
    
    # Берем последний заказ пользователя
    latest_order = user_orders[0]
    order_id = latest_order['id']
    
    # Сохраняем ID заказа в контексте
    context.user_data['active_chat'] = {
        'order_id': order_id,
        'initiated': True
    }
    
    # Получаем историю сообщений
    messages = db.get_order_messages(order_id)
    
    text = (
        f"💬 <b>Чат с менеджером</b>\n\n"
        f"Вы можете написать сообщение по вашему заказу "
        f"<b>#{latest_order['order_number']}</b>\n\n"
    )
    
    if messages:
        text += "<b>Последние сообщения:</b>\n\n"
        # Показываем последние 3 сообщения в обратном порядке
        for msg in reversed(messages[:3]):
            sender = "👨‍💼 Менеджер" if msg['is_admin'] else "👤 Вы"
            text += f"{sender} ({msg['created_at'][:16]}):\n{msg['message']}\n\n"
    
    text += (
        "Просто отправьте сообщение, и наш менеджер "
        "получит его и ответит вам в ближайшее время."
    )
    
    keyboard = [
        [InlineKeyboardButton("👁 Открыть заказ", callback_data=f"view_order_{order_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="start")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def start_order_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало чата по конкретному заказу"""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID заказа из callback_data: chat_order_ORDER_ID
    order_id = int(query.data.split('_')[2])
    order = db.get_order(order_id)
    
    if not order:
        await query.edit_message_text("❌ Заказ не найден")
        return
    
    # Сохраняем ID заказа в контексте
    context.user_data['active_chat'] = {
        'order_id': order_id,
        'initiated': True
    }
    
    # Получаем историю сообщений
    messages = db.get_order_messages(order_id)
    
    text = (
        f"💬 <b>Чат по заказу #{order['order_number']}</b>\n\n"
        f"Здесь вы можете обсудить детали заказа с менеджером.\n\n"
    )
    
    if messages:
        text += "<b>История сообщений:</b>\n\n"
        # Показываем последние 3 сообщения в обратном порядке
        for msg in reversed(messages[:3]):
            sender = "👨‍💼 Менеджер" if msg['is_admin'] else "👤 Вы"
            text += f"{sender} ({msg['created_at'][:16]}):\n{msg['message']}\n\n"
    
    text += (
        "Просто отправьте сообщение, и наш менеджер "
        "получит его и ответит вам в ближайшее время."
    )
    
    keyboard = [
        [InlineKeyboardButton("📋 Детали заказа", callback_data=f"view_order_{order_id}")],
        [InlineKeyboardButton("◀️ К заказам", callback_data="my_orders")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
