from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from database import db
from config import ADMIN_IDS
import logging

logger = logging.getLogger(__name__)

def admin_only(func):
    """Декоратор для ограничения доступа только для администраторов"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Проверяем в конфиге и в БД
        if user_id not in ADMIN_IDS and not db.is_admin(user_id):
            logger.warning(f"Неавторизованный доступ к админ-функции: {user_id}")
            
            if update.callback_query:
                await update.callback_query.answer(
                    "❌ У вас нет прав администратора",
                    show_alert=True
                )
            else:
                await update.message.reply_text(
                    "❌ У вас нет прав для выполнения этой команды."
                )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

def track_activity(func):
    """Декоратор для отслеживания активности пользователей"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        
        # Обновляем информацию о пользователе
        if user:
            try:
                db.add_user(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
            except Exception as e:
                logger.error(f"Ошибка обновления пользователя: {e}")
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

def error_handler(func):
    """Декоратор для обработки ошибок"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
            
            error_text = (
                "❌ <b>Произошла ошибка</b>\n\n"
                "Пожалуйста, попробуйте позже или обратитесь в поддержку."
            )
            
            try:
                if update.callback_query:
                    await update.callback_query.answer(
                        "Произошла ошибка",
                        show_alert=True
                    )
                    await update.callback_query.message.reply_text(
                        error_text,
                        parse_mode='HTML'
                    )
                elif update.message:
                    await update.message.reply_text(
                        error_text,
                        parse_mode='HTML'
                    )
            except:
                pass
            
            raise
    
    return wrapper

def typing_action(func):
    """Показывает индикатор печати во время выполнения функции"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        chat_id = update.effective_chat.id
        
        # Запускаем индикатор печати
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

def log_command(func):
    """Логирование выполнения команд"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        command = func.__name__
        
        logger.info(
            f"Команда: {command} | "
            f"User: {user.id} (@{user.username}) | "
            f"Name: {user.first_name}"
        )
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper
