from datetime import datetime, timedelta
from typing import List, Dict
import re

def format_datetime(dt_string: str, format_type: str = 'full') -> str:
    """Форматирование даты и времени"""
    try:
        dt = datetime.fromisoformat(dt_string)
        
        if format_type == 'full':
            return dt.strftime('%d.%m.%Y %H:%M')
        elif format_type == 'date':
            return dt.strftime('%d.%m.%Y')
        elif format_type == 'time':
            return dt.strftime('%H:%M')
        elif format_type == 'relative':
            return get_relative_time(dt)
        else:
            return dt_string
    except:
        return dt_string

def get_relative_time(dt: datetime) -> str:
    """Получить относительное время (например, '2 часа назад')"""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} {'год' if years == 1 else 'лет'} назад"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} {'месяц' if months == 1 else 'месяцев'} назад"
    elif diff.days > 0:
        return f"{diff.days} {'день' if diff.days == 1 else 'дней'} назад"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} {'час' if hours == 1 else 'часов'} назад"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} {'минуту' if minutes == 1 else 'минут'} назад"
    else:
        return "только что"

def validate_email(email: str) -> bool:
    """Валидация email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Валидация номера телефона"""
    # Удаляем все символы кроме цифр и +
    cleaned = re.sub(r'[^\d+]', '', phone)
    # Проверяем длину (от 10 до 15 цифр)
    return 10 <= len(cleaned) <= 15

def validate_telegram_username(username: str) -> bool:
    """Валидация Telegram username"""
    pattern = r'^@?[a-zA-Z0-9_]{5,32}$'
    return re.match(pattern, username) is not None

def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """Обрезать текст до определенной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def escape_html(text: str) -> str:
    """Экранирование HTML символов"""
    if not text:
        return text
    
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))

def format_price(price: int) -> str:
    """Форматирование цены"""
    return f"{price:,}".replace(',', ' ') + ' ₽'

def paginate_list(items: List, page: int = 0, per_page: int = 10) -> tuple:
    """Пагинация списка"""
    total_items = len(items)
    total_pages = (total_items + per_page - 1) // per_page
    
    start = page * per_page
    end = start + per_page
    
    paginated_items = items[start:end]
    
    return paginated_items, total_pages

def generate_order_report(order: Dict) -> str:
    """Генерация отчета по заказу"""
    from config import ORDER_STATUSES
    
    status = ORDER_STATUSES.get(order['status'], order['status'])
    
    report = f"""
📋 ОТЧЕТ ПО ЗАКАЗУ #{order['order_number']}

═══════════════════════════════

📊 ОСНОВНАЯ ИНФОРМАЦИЯ:
   ID заказа: {order['id']}
   Статус: {status}
   Тариф: {order['tariff']}
   Бюджет: {order['budget']}

👤 КЛИЕНТ:
   User ID: {order['user_id']}
   Имя: {order['name']}
   Контакт: {order['contact']}

📝 ОПИСАНИЕ ПРОЕКТА:
{order['description']}

📅 ДАТЫ:
   Создан: {format_datetime(order['created_at'])}
   Обновлён: {format_datetime(order['updated_at'])}
"""
    
    if order['completed_at']:
        report += f"   Завершён: {format_datetime(order['completed_at'])}\n"
    
    if order['admin_comment']:
        report += f"\n💬 КОММЕНТАРИЙ:\n{order['admin_comment']}\n"
    
    report += "\n═══════════════════════════════"
    
    return report

def calculate_order_duration(created_at: str, completed_at: str = None) -> str:
    """Подсчет длительности заказа"""
    try:
        start = datetime.fromisoformat(created_at)
        end = datetime.fromisoformat(completed_at) if completed_at else datetime.now()
        
        duration = end - start
        
        days = duration.days
        hours = duration.seconds // 3600
        
        if days > 0:
            return f"{days} дн. {hours} ч."
        else:
            return f"{hours} ч."
    except:
        return "н/д"

def get_status_emoji(status: str) -> str:
    """Получить эмодзи для статуса"""
    emoji_map = {
        'new': '🆕',
        'in_progress': '⚙️',
        'review': '👀',
        'revision': '🔄',
        'completed': '✅',
        'cancelled': '❌',
        'paid': '💳'
    }
    return emoji_map.get(status, '❓')

def create_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Создание прогресс-бара"""
    if total == 0:
        return '░' * length
    
    filled = int((current / total) * length)
    bar = '█' * filled + '░' * (length - filled)
    percentage = int((current / total) * 100)
    
    return f"{bar} {percentage}%"
