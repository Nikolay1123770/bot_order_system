from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from keyboards import kb
from config import TARIFFS, ADMIN_IDS, ORDER_STATUSES
import logging

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
SELECT_TARIFF, ENTER_NAME, ENTER_DESCRIPTION, SELECT_BUDGET, ENTER_CONTACT = range(5)

async def start_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало оформления заказа - выбор тарифа"""
    query = update.callback_query
    await query.answer()
    
    text = (
        "🛒 <b>Оформление заказа</b>\n\n"
        "Шаг 1/5: Выберите подходящий тариф\n\n"
        "Если у вас индивидуальный проект, выберите тариф "
        "«Индивидуальный», и мы рассчитаем стоимость."
    )
    
    await query.edit_message_text(
        text,
        reply_markup=kb.tariff_selection(),
        parse_mode='HTML'
    )
    
    return SELECT_TARIFF

async def select_tariff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора тарифа"""
    query = update.callback_query
    await query.answer()
    
    tariff_key = query.data.replace('tariff_', '')
    
    if tariff_key not in TARIFFS:
        await query.edit_message_text("❌ Неверный тариф")
        return ConversationHandler.END
    
    # Сохраняем выбранный тариф
    context.user_data['tariff'] = tariff_key
    tariff = TARIFFS[tariff_key]
    
    text = (
        f"✅ Вы выбрали: <b>{tariff['name']}</b>\n"
        f"💰 Стоимость: {tariff['price_text']}\n\n"
        
        "🎯 <b>Что входит:</b>\n"
    )
    
    for feature in tariff['features']:
        text += f"{feature}\n"
    
    text += (
        f"\n⏱ Срок разработки: {tariff['duration']}\n\n"
        "─────────────────────────\n\n"
        "<b>Шаг 2/5: Как к вам обращаться?</b>\n"
        "Введите ваше имя или название компании:"
    )
    
    await query.edit_message_text(text, parse_mode='HTML')
    
    return ENTER_NAME

async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода имени"""
    name = update.message.text.strip()
    
    if len(name) < 2 or len(name) > 100:
        await update.message.reply_text(
            "❌ Имя должно быть от 2 до 100 символов. Попробуйте ещё раз:"
        )
        return ENTER_NAME
    
    context.user_data['name'] = name
    
    text = (
        f"✅ Отлично, <b>{name}</b>!\n\n"
        "<b>Шаг 3/5: Опишите ваш проект</b>\n\n"
        "Расскажите подробнее, что вы хотите:\n"
        "• Какие функции должны быть?\n"
        "• Для какой цели создаётся бот?\n"
        "• Есть ли примеры похожих ботов?\n"
        "• Особые требования или пожелания?\n\n"
        "💡 Чем подробнее описание, тем точнее мы "
        "сможем оценить проект и сроки."
    )
    
    await update.message.reply_text(
        text,
        reply_markup=kb.cancel_button(),
        parse_mode='HTML'
    )
    
    return ENTER_DESCRIPTION

async def enter_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания проекта"""
    description = update.message.text.strip()
    
    if len(description) < 10:
        await update.message.reply_text(
            "❌ Слишком короткое описание. Пожалуйста, опишите "
            "проект более подробно (минимум 10 символов):"
        )
        return ENTER_DESCRIPTION
    
    if len(description) > 2000:
        await update.message.reply_text(
            "❌ Слишком длинное описание (максимум 2000 символов). "
            "Пожалуйста, сократите:"
        )
        return ENTER_DESCRIPTION
    
    context.user_data['description'] = description
    
    text = (
        "✅ Описание принято!\n\n"
        "<b>Шаг 4/5: Укажите ваш бюджет</b>\n\n"
        "Это поможет нам предложить оптимальное решение:"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=kb.budget_selection(),
        parse_mode='HTML'
    )
    
    return SELECT_BUDGET

async def select_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора бюджета"""
    query = update.callback_query
    await query.answer()
    
    budget_map = {
        'budget_5000': 'До 5,000 ₽',
        'budget_15000': '5,000 - 15,000 ₽',
        'budget_30000': '15,000 - 30,000 ₽',
        'budget_30000plus': '30,000+ ₽',
        'budget_unknown': 'Не определился'
    }
    
    budget = budget_map.get(query.data, 'Не указан')
    context.user_data['budget'] = budget
    
    text = (
        f"💰 Бюджет: <b>{budget}</b>\n\n"
        "<b>Шаг 5/5: Контактные данные</b>\n\n"
        "Укажите удобный способ связи:\n"
        "• Telegram (@username)\n"
        "• Email\n"
        "• Телефон\n"
        "• WhatsApp\n\n"
        "Можете указать несколько вариантов."
    )
    
    await query.edit_message_text(text, parse_mode='HTML')
    
    return ENTER_CONTACT

async def enter_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Финальный шаг - получение контактов и создание заказа"""
    contact = update.message.text.strip()
    
    if len(contact) < 3:
        await update.message.reply_text(
            "❌ Слишком короткие контактные данные. Попробуйте ещё раз:"
        )
        return ENTER_CONTACT
    
    context.user_data['contact'] = contact
    
    # Создаём заказ в базе данных
    user = update.effective_user
    user_data = context.user_data
    
    try:
        order_id = db.create_order(
            user_id=user.id,
            name=user_data['name'],
            contact=user_data['contact'],
            tariff=TARIFFS[user_data['tariff']]['name'],
            description=user_data['description'],
            budget=user_data['budget']
        )
        
        order = db.get_order(order_id)
        
        # Формируем подтверждение для клиента
        tariff = TARIFFS[user_data['tariff']]
        
        client_text = (
            "🎉 <b>Заказ успешно создан!</b>\n\n"
            f"📋 Номер заказа: <b>#{order['order_number']}</b>\n\n"
            
            "📝 <b>Детали заказа:</b>\n"
            f"👤 Имя: {user_data['name']}\n"
            f"💎 Тариф: {tariff['name']}\n"
            f"💰 Бюджет: {user_data['budget']}\n"
            f"📞 Контакт: {user_data['contact']}\n\n"
            
            f"📄 <b>Описание:</b>\n{user_data['description'][:200]}...\n\n"
            
            "⏱ <b>Что дальше?</b>\n"
            "1️⃣ Мы изучим ваш заказ (15-30 мин)\n"
            "2️⃣ Свяжемся для уточнения деталей\n"
            "3️⃣ Составим ТЗ и договор\n"
            "4️⃣ Начнём разработку после оплаты\n\n"
            
            "📱 Следить за статусом можно в разделе\n"
            "«📦 Мои заказы»\n\n"
            
            "💬 Вопросы? Пишите в поддержку!"
        )
        
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = [
            [InlineKeyboardButton("📦 Мои заказы", callback_data='my_orders')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='start')]
        ]
        
        await update.message.reply_text(
            client_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        
        # Уведомление для администраторов
        admin_text = (
            "🔔 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
            f"📋 Заказ: <b>#{order['order_number']}</b>\n"
            f"🆔 ID: {order_id}\n\n"
            
            f"👤 <b>Клиент:</b>\n"
            f"   Имя: {user_data['name']}\n"
            f"   Username: @{user.username or 'не указан'}\n"
            f"   User ID: <code>{user.id}</code>\n\n"
            
            f"💎 <b>Тариф:</b> {tariff['name']}\n"
            f"💰 <b>Бюджет:</b> {user_data['budget']}\n"
            f"📞 <b>Контакт:</b> {user_data['contact']}\n\n"
            
            f"📝 <b>Описание проекта:</b>\n{user_data['description']}\n\n"
            
            f"⏰ Создан: {order['created_at']}"
        )
        
        admin_keyboard = [
            [InlineKeyboardButton(
                "📋 Открыть заказ",
                callback_data=f'admin_order_{order_id}'
            )],
            [InlineKeyboardButton(
                "✏️ Изменить статус",
                callback_data=f'admin_status_{order_id}'
            )]
        ]
        
        # Отправляем всем администраторам
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    reply_markup=InlineKeyboardMarkup(admin_keyboard),
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Ошибка отправки админу {admin_id}: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка создания заказа: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при создании заказа. "
            "Пожалуйста, обратитесь в поддержку."
        )
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return ConversationHandler.END

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена оформления заказа"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.clear()
    
    text = (
        "❌ <b>Оформление заказа отменено</b>\n\n"
        "Вы можете начать заново в любое время."
    )
    
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = [
        [InlineKeyboardButton("🛒 Начать заново", callback_data='order')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='start')]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    return ConversationHandler.END
