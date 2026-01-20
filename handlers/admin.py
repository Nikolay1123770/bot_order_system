from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from keyboards import kb
from config import ORDER_STATUSES, ITEMS_PER_PAGE, ADMIN_IDS
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Состояния для админа
ADMIN_COMMENT, ADMIN_MESSAGE = range(2)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главная админ-панель"""
    query = update.callback_query
    await query.answer()
    
    stats = db.get_statistics()
    
    text = (
        "👨‍💼 <b>Панель администратора</b>\n\n"
        
        "📊 <b>Статистика:</b>\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"📦 Всего заказов: {stats['total_orders']}\n"
        f"🆕 Заказов сегодня: {stats['orders_today']}\n"
        f"👤 Новых за неделю: {stats['new_users_week']}\n\n"
        
        "📋 <b>Заказы по статусам:</b>\n"
    )
    
    for status_key, status_name in ORDER_STATUSES.items():
        count = stats['orders_by_status'].get(status_key, 0)
        if count > 0:
            text += f"{status_name}: {count}\n"
    
    text += "\nВыберите действие:"
    
    await query.edit_message_text(
        text,
        reply_markup=kb.admin_panel(),
        parse_mode='HTML'
    )

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список всех заказов"""
    query = update.callback_query
    await query.answer()
    
    orders = db.get_all_orders()
    
    if not orders:
        text = "📋 Заказов пока нет"
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='admin_panel')]]
    else:
        text = f"📋 <b>Все заказы ({len(orders)}):</b>\n\n"
        
        keyboard = []
        for order in orders[:20]:  # Показываем первые 20
            status = ORDER_STATUSES.get(order['status'], order['status'])
            button_text = (
                f"#{order['order_number']} | {status} | "
                f"{order['created_at'][:10]}"
            )
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"admin_order_{order['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            "◀️ Назад",
            callback_data='admin_panel'
        )])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def admin_new_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Новые заказы"""
    query = update.callback_query
    await query.answer()
    
    orders = db.get_all_orders(status='new')
    
    if not orders:
        text = "🆕 Новых заказов нет"
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='admin_panel')]]
    else:
        text = f"🆕 <b>Новые заказы ({len(orders)}):</b>\n\n"
        
        keyboard = []
        for order in orders:
            button_text = (
                f"#{order['order_number']} | {order['name']} | "
                f"{order['created_at'][:10]}"
            )
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"admin_order_{order['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton(
            "◀️ Назад",
            callback_data='admin_panel'
        )])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def admin_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детальная информация о заказе"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    order = db.get_order(order_id)
    
    if not order:
        await query.edit_message_text("❌ Заказ не найден")
        return
    
    # Получаем информацию о пользователе
    user = db.get_user(order['user_id'])
    
    status = ORDER_STATUSES.get(order['status'], order['status'])
    
    text = (
        f"📋 <b>ЗАКАЗ #{order['order_number']}</b>\n"
        f"🆔 ID: {order['id']}\n\n"
        
        f"👤 <b>Клиент:</b>\n"
        f"   ID: <code>{order['user_id']}</code>\n"
        f"   Имя: {order['name']}\n"
    )
    
    if user:
        text += f"   Username: @{user['username'] or 'нет'}\n"
        text += f"   Telegram: {user['first_name'] or ''} {user['last_name'] or ''}\n"
    
    text += (
        f"\n📞 <b>Контакт:</b> {order['contact']}\n"
        f"💎 <b>Тариф:</b> {order['tariff']}\n"
        f"💰 <b>Бюджет:</b> {order['budget']}\n"
        f"📊 <b>Статус:</b> {status}\n\n"
        
        f"📝 <b>Описание:</b>\n{order['description']}\n\n"
    )
    
    if order['admin_comment']:
        text += f"💬 <b>Комментарий:</b>\n{order['admin_comment']}\n\n"
    
    text += (
        f"📅 <b>Создан:</b> {order['created_at']}\n"
        f"🔄 <b>Обновлён:</b> {order['updated_at']}\n"
    )
    
    if order['completed_at']:
        text += f"✅ <b>Завершён:</b> {order['completed_at']}\n"
    
    await query.edit_message_text(
        text,
        reply_markup=kb.admin_order_actions(order_id),
        parse_mode='HTML'
    )

async def admin_change_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню изменения статуса"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    order = db.get_order(order_id)
    
    if not order:
        await query.edit_message_text("❌ Заказ не найден")
        return
    
    current_status = ORDER_STATUSES.get(order['status'], order['status'])
    
    text = (
        f"✏️ <b>Изменение статуса</b>\n\n"
        f"Заказ: #{order['order_number']}\n"
        f"Текущий статус: {current_status}\n\n"
        "Выберите новый статус:"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=kb.status_selection(order_id),
        parse_mode='HTML'
    )

async def admin_set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка нового статуса"""
    query = update.callback_query
    await query.answer()
    
    # Парсим данные: setstatus_ORDER_ID_STATUS
    parts = query.data.split('_')
    order_id = int(parts[1])
    new_status = parts[2]
    
    # Запрашиваем комментарий
    context.user_data['pending_status_change'] = {
        'order_id': order_id,
        'new_status': new_status
    }
    
    text = (
        "💬 <b>Добавьте комментарий к изменению статуса</b>\n\n"
        "Это сообщение увидит клиент.\n"
        "Или отправьте '-' чтобы пропустить."
    )
    
    await query.edit_message_text(text, parse_mode='HTML')
    
    return ADMIN_COMMENT

async def admin_save_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение статуса с комментарием"""
    comment = update.message.text.strip()
    
    if comment == '-':
        comment = None
    
    change_data = context.user_data.get('pending_status_change')
    
    if not change_data:
        await update.message.reply_text("❌ Ошибка: данные не найдены")
        return ConversationHandler.END
    
    order_id = change_data['order_id']
    new_status = change_data['new_status']
    admin_id = update.effective_user.id
    
    try:
        # Обновляем статус
        db.update_order_status(order_id, new_status, admin_id, comment)
        
        order = db.get_order(order_id)
        # Получаем полное название статуса из словаря
        status_name = ORDER_STATUSES.get(new_status, new_status)
        
        # Уведомляем администратора
        text = (
            f"✅ Статус заказа #{order['order_number']} "
            f"изменён на: {status_name}"
        )
        
        keyboard = [
            [InlineKeyboardButton(
                "📋 Открыть заказ",
                callback_data=f'admin_order_{order_id}'
            )],
            [InlineKeyboardButton(
                "◀️ К заказам",
                callback_data='admin_orders'
            )]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Уведомляем клиента - Используем полное название статуса!
        user_text = (
            f"🔔 <b>Обновление заказа #{order['order_number']}</b>\n\n"
            f"Статус изменён: {status_name}\n"
        )
        
        if comment:
            user_text += f"\n💬 Комментарий:\n{comment}\n"
        
        user_text += (
            f"\n📋 Подробности: /start → Мои заказы"
        )
        
        user_keyboard = [
            [InlineKeyboardButton(
                "📦 Мои заказы",
                callback_data='my_orders'
            )]
        ]
        
        try:
            await context.bot.send_message(
                chat_id=order['user_id'],
                text=user_text,
                reply_markup=InlineKeyboardMarkup(user_keyboard),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления клиента: {e}")
        
    except Exception as e:
        logger.error(f"Ошибка изменения статуса: {e}")
        await update.message.reply_text(
            "❌ Ошибка при изменении статуса"
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def admin_order_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """История изменений заказа"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    order = db.get_order(order_id)
    history = db.get_order_history(order_id)
    
    if not order:
        await query.edit_message_text("❌ Заказ не найден")
        return
    
    text = f"📜 <b>История заказа #{order['order_number']}</b>\n\n"
    
    if not history:
        text += "История пуста"
    else:
        for entry in history:
            old = ORDER_STATUSES.get(entry['old_status'], entry['old_status'])
            new = ORDER_STATUSES.get(entry['new_status'], entry['new_status'])
            
            text += f"🕐 {entry['created_at'][:16]}\n"
            
            if entry['old_status']:
                text += f"   {old} → {new}\n"
            else:
                text += f"   Создан: {new}\n"
            
            if entry['comment']:
                text += f"   💬 {entry['comment']}\n"
            
            text += "\n"
    
    keyboard = [[InlineKeyboardButton(
        "◀️ Назад",
        callback_data=f'admin_order_{order_id}'
    )]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список пользователей"""
    query = update.callback_query
    await query.answer()
    
    users = db.get_all_users()
    
    text = f"👥 <b>Пользователи ({len(users)}):</b>\n\n"
    
    for user in users[:15]:  # Первые 15
        username = f"@{user['username']}" if user['username'] else "без username"
        text += (
            f"👤 {user['first_name'] or 'Имя не указано'}\n"
            f"   ID: <code>{user['user_id']}</code>\n"
            f"   {username}\n"
            f"   Регистрация: {user['created_at'][:10]}\n\n"
        )
    
    keyboard = [[InlineKeyboardButton(
        "◀️ Назад",
        callback_data='admin_panel'
    )]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подробная статистика"""
    query = update.callback_query
    await query.answer()
    
    stats = db.get_statistics()
    
    text = (
        "📊 <b>Детальная статистика</b>\n\n"
        
        "👥 <b>Пользователи:</b>\n"
        f"   Всего: {stats['total_users']}\n"
        f"   За неделю: {stats['new_users_week']}\n\n"
        
        "📦 <b>Заказы:</b>\n"
        f"   Всего: {stats['total_orders']}\n"
        f"   Сегодня: {stats['orders_today']}\n\n"
        
        "📋 <b>По статусам:</b>\n"
    )
    
    for status_key, status_name in ORDER_STATUSES.items():
        count = stats['orders_by_status'].get(status_key, 0)
        text += f"   {status_name}: {count}\n"
    
    keyboard = [[InlineKeyboardButton(
        "◀️ Назад",
        callback_data='admin_panel'
    )]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

# Новые функции для работы с сообщениями

async def admin_message_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало отправки сообщения пользователю"""
    query = update.callback_query
    await query.answer()
    
    # Парсим данные: admin_message_ORDER_ID
    order_id = int(query.data.split('_')[2])
    order = db.get_order(order_id)
    
    if not order:
        await query.edit_message_text("❌ Заказ не найден")
        return ConversationHandler.END
    
    # Сохраняем ID заказа и пользователя в контексте
    context.user_data['chat_with'] = {
        'order_id': order_id,
        'user_id': order['user_id']
    }
    
    # Получаем историю сообщений
    messages = db.get_order_messages(order_id)
    
    text = (
        f"💬 <b>Чат с клиентом</b>\n\n"
        f"Заказ: <b>#{order['order_number']}</b>\n"
        f"Клиент: {order['name']}\n\n"
    )
    
    if messages:
        text += "<b>История сообщений:</b>\n\n"
        # Показываем последние 5 сообщений в обратном порядке (новые внизу)
        for msg in reversed(messages[:5]):
            sender = "👨‍💼 Вы" if msg['is_admin'] else "👤 Клиент"
            text += f"{sender} ({msg['created_at'][:16]}):\n{msg['message']}\n\n"
    else:
        text += "История сообщений пуста.\n\n"
    
    text += "✏️ <b>Напишите ваше сообщение:</b>"
    
    await query.edit_message_text(text, parse_mode='HTML')
    
    return ADMIN_MESSAGE

async def admin_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка сообщения пользователю"""
    message_text = update.message.text.strip()
    
    if not message_text:
        await update.message.reply_text(
            "❌ Сообщение не может быть пустым. Попробуйте ещё раз:"
        )
        return ADMIN_MESSAGE
    
    chat_data = context.user_data.get('chat_with')
    if not chat_data:
        await update.message.reply_text(
            "❌ Ошибка: данные чата не найдены"
        )
        return ConversationHandler.END
    
    order_id = chat_data['order_id']
    user_id = chat_data['user_id']
    admin_id = update.effective_user.id
    
    try:
        order = db.get_order(order_id)
        if not order:
            await update.message.reply_text("❌ Заказ не найден")
            return ConversationHandler.END
        
        # Сохраняем сообщение в БД
        db.add_message(
            order_id=order_id,
            user_id=user_id,
            message=message_text,
            is_admin=True,
            admin_id=admin_id
        )
        
        # Отправляем сообщение пользователю
        user_text = (
            f"💬 <b>Сообщение от менеджера</b>\n"
            f"По заказу <b>#{order['order_number']}</b>:\n\n"
            f"{message_text}\n\n"
            f"Вы можете ответить на это сообщение."
        )
        
        # Клавиатура для пользователя
        user_keyboard = [
            [InlineKeyboardButton("👁 Посмотреть заказ", callback_data=f"view_order_{order_id}")],
            [InlineKeyboardButton("📦 Все заказы", callback_data="my_orders")]
        ]
        
        # Отправляем пользователю
        sent_message = await context.bot.send_message(
            chat_id=user_id,
            text=user_text,
            reply_markup=InlineKeyboardMarkup(user_keyboard),
            parse_mode='HTML'
        )
        
        # Уведомляем админа об успешной отправке
        admin_text = (
            f"✅ <b>Сообщение отправлено клиенту</b>\n\n"
            f"Заказ: <b>#{order['order_number']}</b>\n"
            f"Клиент получит уведомление и сможет ответить.\n\n"
            f"Когда клиент ответит, вы получите уведомление."
        )
        
        admin_keyboard = [
            [InlineKeyboardButton("📋 К заказу", callback_data=f"admin_order_{order_id}")],
            [InlineKeyboardButton("📨 Написать ещё", callback_data=f"admin_message_{order_id}")]
        ]
        
        await update.message.reply_text(
            admin_text,
            reply_markup=InlineKeyboardMarkup(admin_keyboard),
            parse_mode='HTML'
        )
        
        logger.info(
            f"Администратор {admin_id} отправил сообщение клиенту {user_id} "
            f"по заказу #{order['order_number']}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        await update.message.reply_text(
            "❌ Ошибка при отправке сообщения. Попробуйте позже."
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def show_order_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать историю сообщений по заказу"""
    query = update.callback_query
    await query.answer()
    
    order_id = int(query.data.split('_')[2])
    order = db.get_order(order_id)
    
    if not order:
        await query.edit_message_text("❌ Заказ не найден")
        return
    
    messages = db.get_order_messages(order_id)
    
    text = (
        f"💬 <b>Переписка по заказу #{order['order_number']}</b>\n\n"
    )
    
    if not messages:
        text += "Сообщений пока нет"
    else:
        for msg in reversed(messages):
            sender = "👨‍💼 Менеджер" if msg['is_admin'] else f"👤 {order['name']}"
            text += f"{sender} ({msg['created_at'][:16]}):\n{msg['message']}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("✏️ Написать", callback_data=f"admin_message_{order_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data=f"admin_order_{order_id}")]
    ]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )
