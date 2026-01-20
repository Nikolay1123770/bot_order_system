from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
        "Отлично! Давайте оформим ваш заказ.\n\n"
        "<b>Шаг 1/5: Выберите тип услуги</b>\n\n"
        "🤖 <b>Telegram боты:</b>\n"
        "• Простой - 1,000 ₽\n"
        "• Средней сложности - 2,000 ₽\n"
        "• Сложный - 3,500 ₽\n\n"
        "🌐 <b>Веб-сайты:</b>\n"
        "• Любой сайт - 2,500 ₽\n\n"
        "🔌 <b>Дополнительно:</b>\n"
        "• API интеграция - от 500 ₽\n\n"
        "💡 API интеграции оплачиваются отдельно"
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
        
        "🎯 <b>Что входит в тариф:</b>\n"
    )
    
    for feature in tariff['features']:
        text += f"{feature}\n"
    
    text += (
        f"\n⏱ <b>Срок разработки:</b> {tariff['duration']}\n\n"
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
    
    tariff_key = context.user_data.get('tariff', '')
    tariff = TARIFFS.get(tariff_key, {})
    
    # Формируем подсказки в зависимости от типа услуги
    if tariff_key.startswith('bot_'):
        hints = (
            "• Какие команды и функции нужны?\n"
            "• Нужна ли база данных?\n"
            "• Нужна ли админ-панель?\n"
            "• Будут ли платежи?\n"
            "• Нужны ли интеграции с API?"
        )
    elif tariff_key == 'website':
        hints = (
            "• Тип сайта (лендинг, магазин, корпоративный)?\n"
            "• Сколько страниц?\n"
            "• Нужен ли блог/новости?\n"
            "• Форма обратной связи?\n"
            "• Нужны ли интеграции?"
        )
    elif tariff_key == 'api_integration':
        hints = (
            "• С каким API нужна интеграция?\n"
            "• Что должно делать?\n"
            "• Куда интегрировать (бот/сайт)?\n"
            "• Какие данные обрабатывать?"
        )
    else:
        hints = (
            "• Какие функции должны быть?\n"
            "• Для какой цели создаётся?\n"
            "• Есть ли примеры?\n"
            "• Особые требования?"
        )
    
    text = (
        f"✅ Отлично, <b>{name}</b>!\n\n"
        "<b>Шаг 3/5: Опишите ваш проект</b>\n\n"
        "Расскажите подробнее о проекте:\n\n"
        f"{hints}\n\n"
        "💡 <b>Совет:</b> Чем подробнее описание, тем точнее "
        "мы сможем оценить сроки и стоимость.\n\n"
        "📝 Минимум 20 символов"
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
    
    if len(description) < 20:
        await update.message.reply_text(
            "❌ Слишком короткое описание. Пожалуйста, опишите "
            "проект более подробно (минимум 20 символов).\n\n"
            "💡 Укажите основные функции и требования:"
        )
        return ENTER_DESCRIPTION
    
    if len(description) > 2000:
        await update.message.reply_text(
            "❌ Слишком длинное описание (максимум 2000 символов). "
            "Пожалуйста, сократите описание:"
        )
        return ENTER_DESCRIPTION
    
    context.user_data['description'] = description
    
    text = (
        "✅ Описание принято!\n\n"
        "<b>Шаг 4/5: Укажите ваш бюджет</b>\n\n"
        "Это поможет нам предложить оптимальное решение.\n"
        "Если нужны дополнительные функции (API интеграции и т.д.),\n"
        "итоговая стоимость может отличаться."
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
        'budget_1500': 'До 1,500 ₽',
        'budget_2500': '1,500 - 2,500 ₽',
        'budget_5000': '2,500 - 5,000 ₽',
        'budget_5000plus': '5,000+ ₽',
        'budget_unknown': 'Не определился'
    }
    
    budget = budget_map.get(query.data, 'Не указан')
    context.user_data['budget'] = budget
    
    text = (
        f"💰 Бюджет: <b>{budget}</b>\n\n"
        "<b>Шаг 5/5: Контактные данные</b>\n\n"
        "Укажите удобный способ связи для обсуждения проекта:\n\n"
        "📱 Telegram (@username или ссылка)\n"
        "📧 Email\n\n"
        "Можете указать несколько вариантов.\n\n"
        "💡 Мы свяжемся с вами в течение 1-2 часов"
    )
    
    await query.edit_message_text(text, parse_mode='HTML')
    
    return ENTER_CONTACT

async def enter_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Финальный шаг - получение контактов и создание заказа"""
    contact = update.message.text.strip()
    
    if len(contact) < 3:
        await update.message.reply_text(
            "❌ Слишком короткие контактные данные. "
            "Пожалуйста, укажите Telegram или Email:"
        )
        return ENTER_CONTACT
    
    if len(contact) > 200:
        await update.message.reply_text(
            "❌ Слишком длинные контактные данные (максимум 200 символов):"
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
        tariff = TARIFFS[user_data['tariff']]
        
        # Формируем подтверждение для клиента
        client_text = (
            "🎉 <b>Заказ успешно создан!</b>\n\n"
            f"📋 <b>Номер заказа:</b> #{order['order_number']}\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "📝 <b>Детали заказа:</b>\n\n"
            f"👤 <b>Имя:</b> {user_data['name']}\n"
            f"💎 <b>Тариф:</b> {tariff['name']}\n"
            f"💰 <b>Бюджет:</b> {user_data['budget']}\n"
            f"📞 <b>Контакт:</b> {user_data['contact']}\n"
            f"⏱ <b>Срок:</b> {tariff['duration']}\n\n"
            
            f"📄 <b>Описание:</b>\n<i>{user_data['description'][:300]}"
        )
        
        if len(user_data['description']) > 300:
            client_text += "...</i>\n\n"
        else:
            client_text += "</i>\n\n"
        
        client_text += (
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "⏱ <b>Что дальше?</b>\n\n"
            "1️⃣ Мы изучим ваш заказ (15-30 мин)\n"
            "2️⃣ Свяжемся для уточнения деталей\n"
            "3️⃣ Согласуем ТЗ и сроки\n"
            "4️⃣ Вы оплачиваете 50% (предоплата)\n"
            "5️⃣ Начинаем разработку\n"
            "6️⃣ Показываем результат\n"
            "7️⃣ Доработки (если нужны)\n"
            "8️⃣ Оплата оставшихся 50%\n"
            "9️⃣ Передача проекта + инструкция\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "📱 <b>Отслеживание заказа:</b>\n"
            "Следить за статусом можно в разделе\n"
            "«📦 Мои заказы». Вы получите уведомление\n"
            "при каждом изменении статуса.\n\n"
            
            "💬 <b>Вопросы?</b>\n"
            "Пишите в поддержку: @botfactory_support\n\n"
            
            "🎯 <b>Гарантии:</b>\n"
            "✅ Возврат предоплаты, если не устроит\n"
            "✅ Бесплатные правки в течение недели\n"
            "✅ Техподдержка 1 месяц бесплатно"
        )
        
        keyboard = [
            [InlineKeyboardButton("📦 Мои заказы", callback_data='my_orders')],
            [InlineKeyboardButton("💬 Поддержка", callback_data='support')],
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
            f"📋 <b>Заказ:</b> #{order['order_number']}\n"
            f"🆔 <b>ID:</b> {order_id}\n"
            f"🕐 <b>Время:</b> {order['created_at']}\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            f"👤 <b>КЛИЕНТ:</b>\n"
            f"   • Имя: {user_data['name']}\n"
            f"   • Username: @{user.username or 'не указан'}\n"
            f"   • User ID: <code>{user.id}</code>\n"
            f"   • Контакт: {user_data['contact']}\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            f"💎 <b>ЗАКАЗ:</b>\n"
            f"   • Тариф: {tariff['name']}\n"
            f"   • Стоимость: {tariff['price_text']}\n"
            f"   • Бюджет клиента: {user_data['budget']}\n"
            f"   • Срок: {tariff['duration']}\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            f"📝 <b>ОПИСАНИЕ ПРОЕКТА:</b>\n\n"
            f"{user_data['description']}\n\n"
            
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "⚡ <b>Действия:</b>\n"
            "1. Свяжитесь с клиентом\n"
            "2. Уточните детали\n"
            "3. Обновите статус заказа\n"
        )
        
        admin_keyboard = [
            [InlineKeyboardButton(
                "📋 Открыть заказ",
                callback_data=f'admin_order_{order_id}'
            )],
            [InlineKeyboardButton(
                "✏️ Изменить статус",
                callback_data=f'admin_status_{order_id}'
            )],
            [InlineKeyboardButton(
                "📊 Все заказы",
                callback_data='admin_orders'
            )]
        ]
        
        # Отправляем всем администраторам
        sent_count = 0
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_text,
                    reply_markup=InlineKeyboardMarkup(admin_keyboard),
                    parse_mode='HTML'
                )
                sent_count += 1
                logger.info(f"Уведомление отправлено админу {admin_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки админу {admin_id}: {e}")
        
        logger.info(
            f"Создан заказ #{order['order_number']} | "
            f"User: {user.id} | "
            f"Tariff: {tariff['name']} | "
            f"Уведомлено админов: {sent_count}/{len(ADMIN_IDS)}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания заказа: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ <b>Произошла ошибка при создании заказа</b>\n\n"
            "Пожалуйста, обратитесь в поддержку:\n"
            "@botfactory_support\n\n"
            "Или попробуйте создать заказ позже.",
            parse_mode='HTML'
        )
        context.user_data.clear()
        return ConversationHandler.END
    
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
        "Вы можете начать заново в любое время.\n\n"
        "💡 Если у вас есть вопросы, обращайтесь в поддержку!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛒 Начать заново", callback_data='order')],
        [InlineKeyboardButton("💬 Поддержка", callback_data='support')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='start')]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
    
    return ConversationHandler.END

async def timeout_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Таймаут оформления заказа (опционально)"""
    if update.message:
        text = (
            "⏱ <b>Время оформления заказа истекло</b>\n\n"
            "Вы можете начать заново, когда будете готовы."
        )
        
        keyboard = [
            [InlineKeyboardButton("🛒 Начать заново", callback_data='order')],
            [InlineKeyboardButton("🏠 Главное меню", callback_data='start')]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    context.user_data.clear()
    return ConversationHandler.END
