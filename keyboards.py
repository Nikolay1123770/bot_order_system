from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import BUTTONS, ORDER_STATUSES, TARIFFS

class Keyboards:
    
    @staticmethod
    def main_menu(is_admin=False):
        """Главное меню"""
        keyboard = [
            [InlineKeyboardButton(BUTTONS['order'], callback_data='order')],
            [InlineKeyboardButton(BUTTONS['my_orders'], callback_data='my_orders')],
            [
                InlineKeyboardButton(BUTTONS['tariffs'], callback_data='tariffs'),
                InlineKeyboardButton(BUTTONS['portfolio'], callback_data='portfolio')
            ],
            [
                InlineKeyboardButton(BUTTONS['reviews'], callback_data='reviews'),
                InlineKeyboardButton("💬 Написать нам", callback_data='start_chat')  # Новая кнопка
            ],
            [InlineKeyboardButton(BUTTONS['about'], callback_data='about')]
        ]
        
        if is_admin:
            keyboard.append([InlineKeyboardButton(
                BUTTONS['admin'], 
                callback_data='admin_panel'
            )])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button():
        """Кнопка назад"""
        return InlineKeyboardMarkup([[
            InlineKeyboardButton(BUTTONS['back'], callback_data='start')
        ]])
    
    @staticmethod
    def cancel_button():
        """Кнопка отмены"""
        return InlineKeyboardMarkup([[
            InlineKeyboardButton(BUTTONS['cancel'], callback_data='cancel_order')
        ]])
    
    @staticmethod
    def tariff_selection():
        """Выбор тарифа"""
        keyboard = []
        
        # Боты
        keyboard.append([InlineKeyboardButton(
            "🤖 TELEGRAM БОТЫ",
            callback_data='category_bots'
        )])
        
        for key in ['bot_simple', 'bot_medium', 'bot_complex']:
            tariff = TARIFFS[key]
            button_text = f"{tariff['name'].split('-')[1].strip()} - {tariff['price_text']}"
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f'tariff_{key}'
            )])
        
        # Сайты
        keyboard.append([InlineKeyboardButton(
            "🌐 ВЕБ-САЙТЫ",
            callback_data='category_websites'
        )])
        
        tariff = TARIFFS['website']
        keyboard.append([InlineKeyboardButton(
            f"Любой сайт - {tariff['price_text']}",
            callback_data='tariff_website'
        )])
        
        # Дополнительно
        keyboard.append([InlineKeyboardButton(
            "🔌 API Интеграция - от 500 ₽",
            callback_data='tariff_api_integration'
        )])
        
        # Индивидуальный
        tariff = TARIFFS['custom']
        keyboard.append([InlineKeyboardButton(
            f"{tariff['name']}",
            callback_data='tariff_custom'
        )])
        
        keyboard.append([InlineKeyboardButton(
            BUTTONS['back'], 
            callback_data='start'
        )])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def budget_selection():
        """Выбор бюджета"""
        keyboard = [
            [InlineKeyboardButton("До 1,500 ₽", callback_data='budget_1500')],
            [InlineKeyboardButton("1,500 - 2,500 ₽", callback_data='budget_2500')],
            [InlineKeyboardButton("2,500 - 5,000 ₽", callback_data='budget_5000')],
            [InlineKeyboardButton("5,000+ ₽", callback_data='budget_5000plus')],
            [InlineKeyboardButton("Не определился", callback_data='budget_unknown')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def order_actions(order_id):
        """Действия с заказом (для пользователя)"""
        keyboard = [
            [InlineKeyboardButton("📝 Оставить отзыв", callback_data=f'review_{order_id}')],
            [InlineKeyboardButton("💬 Написать менеджеру", callback_data=f'chat_order_{order_id}')],  # Новая кнопка
            [InlineKeyboardButton(BUTTONS['back'], callback_data='my_orders')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_panel():
        """Админ-панель"""
        keyboard = [
            [InlineKeyboardButton("📋 Все заказы", callback_data='admin_orders')],
            [InlineKeyboardButton("🆕 Новые заказы", callback_data='admin_new_orders')],
            [
                InlineKeyboardButton("👥 Пользователи", callback_data='admin_users'),
                InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')
            ],
            [InlineKeyboardButton(BUTTONS['back'], callback_data='start')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_order_actions(order_id):
        """Действия с заказом (для админа)"""
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить статус", callback_data=f'admin_status_{order_id}')],
            [InlineKeyboardButton("💬 Написать клиенту", callback_data=f'admin_message_{order_id}')],
            [InlineKeyboardButton("📜 История чата", callback_data=f'admin_chat_{order_id}')],
            [InlineKeyboardButton("📋 История статусов", callback_data=f'admin_history_{order_id}')],
            [InlineKeyboardButton("◀️ К заказам", callback_data='admin_orders')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def status_selection(order_id):
        """Выбор статуса заказа"""
        keyboard = []
        for status_key, status_name in ORDER_STATUSES.items():
            keyboard.append([InlineKeyboardButton(
                status_name,
                callback_data=f'setstatus_{order_id}_{status_key}'
            )])
        keyboard.append([InlineKeyboardButton(
            BUTTONS['back'],
            callback_data=f'admin_order_{order_id}'
        )])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def pagination(current_page, total_pages, callback_prefix):
        """Пагинация"""
        keyboard = []
        buttons = []
        
        if current_page > 0:
            buttons.append(InlineKeyboardButton(
                "⬅️ Назад",
                callback_data=f'{callback_prefix}_{current_page - 1}'
            ))
        
        buttons.append(InlineKeyboardButton(
            f"{current_page + 1}/{total_pages}",
            callback_data='page_info'
        ))
        
        if current_page < total_pages - 1:
            buttons.append(InlineKeyboardButton(
                "Вперёд ➡️",
                callback_data=f'{callback_prefix}_{current_page + 1}'
            ))
        
        keyboard.append(buttons)
        keyboard.append([InlineKeyboardButton(
            BUTTONS['back'],
            callback_data='start'
        )])
        
        return InlineKeyboardMarkup(keyboard)

kb = Keyboards()
