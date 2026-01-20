from telegram import Update
from telegram.ext import ContextTypes
from database import db
from keyboards import kb
from config import TARIFFS, BUTTONS
import logging

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
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
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
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [InlineKeyboardButton(BUTTONS['order'], callback_data='order')],
            [InlineKeyboardButton(BUTTONS['back'], callback_data='start')]
        ]
    else:
        text = f"📦 <b>Ваши заказы ({len(orders)}):</b>\n\n"
        
        from config import ORDER_STATUSES
        
        for order in orders[:10]:  # Показываем последние 10
            status = ORDER_STATUSES.get(order['status'], order['status'])
            text += (
                f"🔹 <b>Заказ #{order['order_number']}</b>\n"
                f"   Тариф: {order['tariff']}\n"
                f"   Статус: {status}\n"
                f"   Дата: {order['created_at'][:10]}\n\n"
            )
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = []
        for order in orders[:10]:
            keyboard.append([InlineKeyboardButton(
                f"#{order['order_number']} - {ORDER_STATUSES.get(order['status'])}",
                callback_data=f"view_order_{order['id']}"
            )])
        keyboard.append([InlineKeyboardButton(BUTTONS['back'], callback_data='start')])
    
    from telegram import InlineKeyboardMarkup
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
    
    from config import ORDER_STATUSES
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
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton(BUTTONS['order'], callback_data='order')],
        [InlineKeyboardButton(BUTTONS['back'], callback_data='start')]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
