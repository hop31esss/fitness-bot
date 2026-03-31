from flask import Flask, request, jsonify
import sqlite3
import logging
from datetime import datetime
import requests
import json
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Токен бота (должен быть в переменных окружения)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
    raise ValueError("BOT_TOKEN обязателен для работы webhook сервера")

# ========== БАЗА ДАННЫХ ==========

def get_db():
    """Получение соединения с БД"""
    conn = sqlite3.connect('fitness_bot.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Создание таблицы для health данных"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data_type TEXT NOT NULL,
            value TEXT,
            raw_data TEXT,
            source TEXT DEFAULT 'apple_health',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_webhooks (
            user_id INTEGER PRIMARY KEY,
            webhook_key TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("✅ Таблицы для вебхуков созданы")

# Инициализация при запуске
init_db()

# ========== ВЕБХУК ЭНДПОИНТ ==========

@app.route('/webhook/<webhook_key>', methods=['POST'])
def handle_webhook(webhook_key):
    """
    Эндпоинт для приёма данных из IFTTT
    URL: https://ваш-домен.com/webhook/уникальный_ключ
    """
    try:
        # Ограничиваем размер тела запроса (например, до 100 КБ)
        content_length = request.content_length or 0
        if content_length > 100 * 1024:
            logger.warning(f"❌ Слишком большой запрос: {content_length} байт, ключ {webhook_key}")
            return jsonify({"error": "Payload too large"}), 413

        # Получаем данные из запроса
        data = request.get_json(silent=True)
        logger.info(f"📡 Получен вебхук с ключом {webhook_key}, размер={content_length} байт")
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Ищем пользователя по ключу
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT user_id FROM user_webhooks WHERE webhook_key = ?",
            (webhook_key,)
        )
        result = cursor.fetchone()
        
        if not result:
            logger.warning(f"❌ Неверный ключ вебхука: {webhook_key}")
            return jsonify({"error": "Invalid webhook key"}), 403
        
        user_id = result['user_id']
        
        # Определяем тип данных
        data_type = data.get('type', 'unknown')
        
        # Сохраняем в БД
        cursor.execute("""
            INSERT INTO health_data (user_id, data_type, value, raw_data)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            data_type,
            json.dumps(data),
            json.dumps(data)
        ))
        
        conn.commit()
        
        # Формируем сообщение для Telegram в зависимости от типа данных
        message = format_health_message(data, data_type)
        
        if message:
            # Отправляем сообщение пользователю в Telegram
            send_telegram_message(user_id, message)
        
        conn.close()
        
        return jsonify({"status": "success", "message": "Data received"}), 200
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки вебхука: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/webhook/<webhook_key>', methods=['GET'])
def test_webhook(webhook_key):
    """GET запрос для проверки работы вебхука"""
    return jsonify({
        "status": "active",
        "webhook_key": webhook_key,
        "message": "Вебхук работает! Отправьте POST запрос с данными."
    }), 200

# ========== ГЕНЕРАЦИЯ КЛЮЧА ==========

@app.route('/generate_key/<int:user_id>', methods=['GET'])
def generate_key(user_id):
    """Генерация нового ключа для пользователя (для админки)"""
    import secrets
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже ключ
    cursor.execute(
        "SELECT webhook_key FROM user_webhooks WHERE user_id = ?",
        (user_id,)
    )
    existing = cursor.fetchone()
    
    if existing:
        return jsonify({
            "user_id": user_id,
            "webhook_key": existing['webhook_key']
        }), 200
    
    # Генерируем новый ключ
    webhook_key = secrets.token_urlsafe(16)
    
    cursor.execute(
        "INSERT INTO user_webhooks (user_id, webhook_key) VALUES (?, ?)",
        (user_id, webhook_key)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        "user_id": user_id,
        "webhook_key": webhook_key
    }), 201

# ========== ФОРМАТИРОВАНИЕ СООБЩЕНИЙ ==========

def format_health_message(data, data_type):
    """Форматирует данные из Apple Health в сообщение для Telegram"""
    
    if data_type == 'workout' or 'Workout' in str(data):
        activity = data.get('Activity', 'Тренировка')
        duration = data.get('Duration', '0')
        calories = data.get('Calories', '0')
        date = data.get('Date', datetime.now().strftime('%Y-%m-%d'))
        
        return (
            f"🏋️ *Новая тренировка из Apple Health*\n\n"
            f"🔥 Тип: {activity}\n"
            f"⏱️ Длительность: {duration} мин\n"
            f"⚡ Калории: {calories} ккал\n"
            f"📅 Дата: {date}\n\n"
            f"✅ Синхронизировано автоматически!"
        )
    
    elif data_type == 'weight' or 'Weight' in str(data):
        weight = data.get('Weight', data.get('value', '0'))
        date = data.get('Date', datetime.now().strftime('%Y-%m-%d'))
        
        return (
            f"⚖️ *Новая запись веса*\n\n"
            f"Вес: {weight} кг\n"
            f"📅 Дата: {date}\n\n"
            f"✅ Данные синхронизированы с Apple Health"
        )
    
    elif data_type == 'steps' or 'Step' in str(data):
        steps = data.get('Steps', data.get('value', '0'))
        date = data.get('Date', datetime.now().strftime('%Y-%m-%d'))
        
        return (
            f"👣 *Новая запись шагов*\n\n"
            f"Шаги: {steps}\n"
            f"📅 Дата: {date}\n\n"
            f"✅ Данные синхронизированы с Apple Health"
        )
    
    elif data_type == 'sleep' or 'Sleep' in str(data):
        hours = data.get('Hours', data.get('value', '0'))
        quality = data.get('Quality', 'не указано')
        date = data.get('Date', datetime.now().strftime('%Y-%m-%d'))
        
        return (
            f"😴 *Новая запись сна*\n\n"
            f"Длительность: {hours} ч\n"
            f"Качество: {quality}\n"
            f"📅 Дата: {date}\n\n"
            f"✅ Данные синхронизированы с Apple Health"
        )
    
    return None

# ========== ОТПРАВКА В TELEGRAM ==========

def send_telegram_message(chat_id, text):
    """Отправляет сообщение пользователю в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info(f"✅ Сообщение отправлено пользователю {chat_id}")
        else:
            logger.error(f"❌ Ошибка отправки: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка отправки в Telegram: {e}")

# ========== СТАТИСТИКА ==========

@app.route('/health_stats/<int:user_id>', methods=['GET'])
def health_stats(user_id):
    """Получение статистики по здоровью пользователя"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Последние 10 записей
    cursor.execute("""
        SELECT data_type, value, created_at 
        FROM health_data 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 20
    """, (user_id,))
    
    entries = cursor.fetchall()
    conn.close()
    
    return jsonify({
        "user_id": user_id,
        "entries": [dict(entry) for entry in entries]
    }), 200

# ========== ЗАПУСК ==========

if __name__ == '__main__':
    logger.info("🚀 Вебхук-сервер запускается на порту 5000")
    app.run(host='0.0.0.0', port=5000, debug=False)