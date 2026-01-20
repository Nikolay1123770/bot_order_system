import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json

class Database:
    def __init__(self, db_name='bot_orders.db'):
        self.db_name = db_name
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_db(self):
        """Инициализация базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_admin INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица заказов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                order_number TEXT UNIQUE,
                name TEXT,
                contact TEXT,
                tariff TEXT,
                description TEXT,
                budget TEXT,
                status TEXT DEFAULT 'new',
                admin_comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        
        # Таблица истории статусов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                old_status TEXT,
                new_status TEXT,
                comment TEXT,
                changed_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        ''')
        
        # Таблица отзывов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                order_id INTEGER,
                rating INTEGER,
                text TEXT,
                is_published INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        ''')
        
        # Таблица статистики
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                event_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # ========== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ==========
    
    def add_user(self, user_id: int, username: str = None, 
                 first_name: str = None, last_name: str = None):
        """Добавить/обновить пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                last_activity = CURRENT_TIMESTAMP
        ''', (user_id, username, first_name, last_name))
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получить пользователя"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка прав администратора"""
        user = self.get_user(user_id)
        return user['is_admin'] == 1 if user else False
    
    def get_all_users(self) -> List[Dict]:
        """Получить всех пользователей"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ========== РАБОТА С ЗАКАЗАМИ ==========
    
    def create_order(self, user_id: int, name: str, contact: str,
                     tariff: str, description: str, budget: str) -> int:
        """Создать заказ"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Генерируем номер заказа
        cursor.execute('SELECT COUNT(*) FROM orders')
        count = cursor.fetchone()[0]
        order_number = f"BO-{count + 1:05d}"
        
        cursor.execute('''
            INSERT INTO orders (user_id, order_number, name, contact, 
                              tariff, description, budget)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, order_number, name, contact, tariff, description, budget))
        
        order_id = cursor.lastrowid
        
        # Добавляем в историю
        cursor.execute('''
            INSERT INTO order_history (order_id, new_status, changed_by)
            VALUES (?, 'new', ?)
        ''', (order_id, user_id))
        
        conn.commit()
        conn.close()
        
        return order_id
    
    def get_order(self, order_id: int) -> Optional[Dict]:
        """Получить заказ"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_user_orders(self, user_id: int) -> List[Dict]:
        """Получить заказы пользователя"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM orders 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_all_orders(self, status: str = None) -> List[Dict]:
        """Получить все заказы"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM orders 
                WHERE status = ? 
                ORDER BY created_at DESC
            ''', (status,))
        else:
            cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def update_order_status(self, order_id: int, new_status: str, 
                          admin_id: int, comment: str = None):
        """Обновить статус заказа"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Получаем старый статус
        cursor.execute('SELECT status FROM orders WHERE id = ?', (order_id,))
        old_status = cursor.fetchone()[0]
        
        # Обновляем статус
        cursor.execute('''
            UPDATE orders 
            SET status = ?, 
                updated_at = CURRENT_TIMESTAMP,
                admin_comment = ?
            WHERE id = ?
        ''', (new_status, comment, order_id))
        
        # Если завершён - ставим дату
        if new_status == 'completed':
            cursor.execute('''
                UPDATE orders 
                SET completed_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (order_id,))
        
        # Добавляем в историю
        cursor.execute('''
            INSERT INTO order_history 
            (order_id, old_status, new_status, comment, changed_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (order_id, old_status, new_status, comment, admin_id))
        
        conn.commit()
        conn.close()
    
    def get_order_history(self, order_id: int) -> List[Dict]:
        """Получить историю заказа"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM order_history 
            WHERE order_id = ? 
            ORDER BY created_at DESC
        ''', (order_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ========== СТАТИСТИКА ==========
    
    def get_statistics(self) -> Dict:
        """Получить статистику"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Всего пользователей
        cursor.execute('SELECT COUNT(*) FROM users')
        stats['total_users'] = cursor.fetchone()[0]
        
        # Всего заказов
        cursor.execute('SELECT COUNT(*) FROM orders')
        stats['total_orders'] = cursor.fetchone()[0]
        
        # Заказы по статусам
        cursor.execute('''
            SELECT status, COUNT(*) as count 
            FROM orders 
            GROUP BY status
        ''')
        stats['orders_by_status'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Заказы за сегодня
        cursor.execute('''
            SELECT COUNT(*) FROM orders 
            WHERE DATE(created_at) = DATE('now')
        ''')
        stats['orders_today'] = cursor.fetchone()[0]
        
        # Новые пользователи за неделю
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE created_at >= datetime('now', '-7 days')
        ''')
        stats['new_users_week'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    # ========== ОТЗЫВЫ ==========
    
    def add_review(self, user_id: int, order_id: int, 
                   rating: int, text: str) -> int:
        """Добавить отзыв"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reviews (user_id, order_id, rating, text)
            VALUES (?, ?, ?, ?)
        ''', (user_id, order_id, rating, text))
        
        review_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return review_id
    
    def get_published_reviews(self, limit: int = 10) -> List[Dict]:
        """Получить опубликованные отзывы"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.*, u.first_name, u.username 
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.is_published = 1
            ORDER BY r.created_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]

# Создаём экземпляр БД
db = Database()
