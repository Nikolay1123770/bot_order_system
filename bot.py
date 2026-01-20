#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)

# Импорты из проекта
from config import BOT_TOKEN, ADMIN_IDS
from database import db
from utils.decorators import admin_only, track_activity, error_handler, log_command

# Импорт обработчиков
from handlers.user import (
    start, show_tariffs, show_my_orders, show_order_detail,
    show_about, show_support, show_reviews, show_portfolio
)
from handlers.order import (
    start_order, select_tariff, enter_name, enter_description,
    select_budget, enter_contact, cancel_order,
    SELECT_TARIFF, ENTER_NAME, ENTER_DESCRIPTION, SELECT_BUDGET, ENTER_CONTACT
)
from handlers.admin import (
    admin_panel, admin_orders, admin_new_orders, admin_order_detail,
    admin_change_status_menu, admin_set_status, admin_save_status,
    admin_order_history, admin_users, admin_stats,
    admin_broadcast_start, admin_broadcast_send,
    ADMIN_COMMENT, ADMIN_BROADCAST_TEXT
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# ============= ОБРАБОТЧИКИ ОШИБОК =============

async def error_callback(update: object, context):
    """Глобальный обработчик ошибок"""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    try:
        if isinstance(update, Update):
            error_text = (
                "❌ <b>Произошла ошибка</b>\n\n"
                "Мы уже работаем над её исправлением.\n"
                "Пожалуйста, попробуйте позже."
            )
            
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    error_text,
                    parse_mode='HTML'
                )
            elif update.message:
                await update.message.reply_text(
                    error_text,
                    parse_mode='HTML'
                )
            
            # Уведомляем администраторов об ошибке
            admin_error_text = (
                f"🚨 <b>ОШИБКА В БОТЕ</b>\n\n"
                f"<code>{str(context.error)[:500]}</code>"
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=admin_error_text,
                        parse_mode='HTML'
                    )
                except:
                    pass
    except Exception as e:
        logger.error(f"Ошибка в error_callback: {e}")

# ============= ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ =============

@track_activity
@log_command
async def help_command(update: Update, context):
    """Команда /help"""
    text = (
        "❓ <b>Помощь</b>\n\n"
        
        "<b>Основные команды:</b>\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/orders - Мои заказы\n"
        "/support - Связаться с поддержкой\n\n"
        
        "<b>Как заказать бота:</b>\n"
        "1. Нажмите «🛒 Заказать бота»\n"
        "2. Выберите тариф\n"
        "3. Заполните информацию\n"
        "4. Дождитесь ответа менеджера\n\n"
        
        "<b>Отслеживание заказа:</b>\n"
        "Статус заказа можно посмотреть в разделе "
        "«📦 Мои заказы». Вы получите уведомление при "
        "каждом изменении статуса.\n\n"
        
        "Вопросы? Пишите в /support"
    )
    
    await update.message.reply_text(text, parse_mode='HTML')

@track_activity
@log_command
async def orders_command(update: Update, context):
    """Команда /orders - быстрый доступ к заказам"""
    # Имитируем нажатие на кнопку "Мои заказы"
    update.callback_query = type('obj', (object,), {
        'answer': lambda: None,
        'edit_message_text': update.message.reply_text
    })()
    await show_my_orders(update, context)

@admin_only
@log_command
async def admin_command(update: Update, context):
    """Команда /admin - быстрый доступ к админке"""
    update.callback_query = type('obj', (object,), {
        'answer': lambda: None,
        'edit_message_text': update.message.reply_text
    })()
    await admin_panel(update, context)

@admin_only
async def stats_command(update: Update, context):
    """Команда /stats - быстрая статистика"""
    stats = db.get_statistics()
    
    text = (
        "📊 <b>Быстрая статистика</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"📦 Заказов: {stats['total_orders']}\n"
        f"🆕 Сегодня: {stats['orders_today']}\n"
    )
    
    await update.message.reply_text(text, parse_mode='HTML')

# ============= НАСТРОЙКА БОТА =============

def main():
    """Запуск бота"""
    
    # Проверка токена
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN':
        logger.error("❌ Токен бота не установлен! Проверьте файл .env")
        sys.exit(1)
    
    # Проверка админов
    if not ADMIN_IDS or ADMIN_IDS == [123456789]:
        logger.warning("⚠️ ID администраторов не настроены!")
    
    logger.info("🤖 Запуск бота...")
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ============= ОБРАБОТЧИК ЗАКАЗОВ =============
    order_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_order, pattern='^order$')
        ],
        states={
            SELECT_TARIFF: [
                CallbackQueryHandler(select_tariff, pattern='^tariff_')
            ],
            ENTER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)
            ],
            ENTER_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)
            ],
            SELECT_BUDGET: [
                CallbackQueryHandler(select_budget, pattern='^budget_')
            ],
            ENTER_CONTACT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_contact)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_order, pattern='^cancel_order$'),
            CommandHandler('start', start)
        ],
        name="order_conversation",
        persistent=False
    )
    
    # ============= ОБРАБОТЧИК ИЗМЕНЕНИЯ СТАТУСА =============
    status_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_set_status, pattern='^setstatus_')
        ],
        states={
            ADMIN_COMMENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_save_status)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(admin_panel, pattern='^admin_panel$')
        ],
        name="status_conversation",
        persistent=False
    )
    
    # ============= ОБРАБОТЧИК РАССЫЛКИ =============
    broadcast_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_broadcast_start, pattern='^admin_broadcast$')
        ],
        states={
            ADMIN_BROADCAST_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_send)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(admin_panel, pattern='^admin_panel$')
        ],
        name="broadcast_conversation",
        persistent=False
    )
    
    # ============= КОМАНДЫ =============
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("orders", orders_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # ============= CONVERSATION HANDLERS =============
    application.add_handler(order_conversation)
    application.add_handler(status_conversation)
    application.add_handler(broadcast_conversation)
    
    # ============= CALLBACK HANDLERS - ПОЛЬЗОВАТЕЛИ =============
    application.add_handler(CallbackQueryHandler(start, pattern='^start$'))
    application.add_handler(CallbackQueryHandler(show_tariffs, pattern='^tariffs$'))
    application.add_handler(CallbackQueryHandler(show_my_orders, pattern='^my_orders$'))
    application.add_handler(CallbackQueryHandler(show_order_detail, pattern='^view_order_'))
    application.add_handler(CallbackQueryHandler(show_about, pattern='^about$'))
    application.add_handler(CallbackQueryHandler(show_support, pattern='^support$'))
    application.add_handler(CallbackQueryHandler(show_reviews, pattern='^reviews$'))
    application.add_handler(CallbackQueryHandler(show_portfolio, pattern='^portfolio$'))
    
    # ============= CALLBACK HANDLERS - АДМИН =============
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_orders, pattern='^admin_orders$'))
    application.add_handler(CallbackQueryHandler(admin_new_orders, pattern='^admin_new_orders$'))
    application.add_handler(CallbackQueryHandler(admin_order_detail, pattern='^admin_order_'))
    application.add_handler(CallbackQueryHandler(admin_change_status_menu, pattern='^admin_status_'))
    application.add_handler(CallbackQueryHandler(admin_order_history, pattern='^admin_history_'))
    application.add_handler(CallbackQueryHandler(admin_users, pattern='^admin_users$'))
    application.add_handler(CallbackQueryHandler(admin_stats, pattern='^admin_stats$'))
    
    # ============= ОБРАБОТЧИК ОШИБОК =============
    application.add_error_handler(error_callback)
    
    # ============= ЗАПУСК =============
    logger.info("✅ Бот успешно запущен!")
    logger.info(f"👨‍💼 Администраторы: {ADMIN_IDS}")
    
    # Уведомляем администраторов о запуске
    async def post_init(application):
        for admin_id in ADMIN_IDS:
            try:
                await application.bot.send_message(
                    chat_id=admin_id,
                    text="✅ <b>Бот успешно запущен!</b>",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.warning(f"Не удалось уведомить админа {admin_id}: {e}")
    
    application.post_init = post_init
    
    # Запуск polling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
