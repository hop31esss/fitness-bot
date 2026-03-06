import sqlite3
import os

print("🔧 Принудительное создание таблицы workout_templates")
print("-" * 50)

# Проверяем текущую директорию
print(f"📁 Текущая директория: {os.getcwd()}")

# Путь к базе данных
db_path = 'fitness_bot.db'
print(f"📁 Путь к БД: {os.path.abspath(db_path)}")

# Проверяем существует ли файл БД
if os.path.exists(db_path):
    size = os.path.getsize(db_path)
    print(f"✅ Файл БД найден, размер: {size} байт")
else:
    print(f"❌ Файл БД НЕ найден, будет создан новый")
    print(f"   Создаём новый файл...")

try:
    # Подключаемся
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("✅ Подключение к БД успешно")
    
    # Смотрим существующие таблицы
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"📊 Существующие таблицы: {[t[0] for t in tables]}")
    
    # Создаём таблицу
    print("🔄 Создаём таблицу workout_templates...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            exercises TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    print("✅ Запрос выполнен")
    
    # Проверяем, создалась ли
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workout_templates'")
    if cursor.fetchone():
        print("✅ Таблица workout_templates успешно создана и найдена!")
    else:
        print("❌ Таблица workout_templates НЕ найдена после создания")
    
    # Показываем структуру
    cursor.execute("PRAGMA table_info(workout_templates)")
    columns = cursor.fetchall()
    if columns:
        print("📋 Структура таблицы:")
        for col in columns:
            print(f"   {col[1]} - {col[2]}")
    else:
        print("❌ Не удалось получить структуру таблицы")
    
    conn.close()
    
except Exception as e:
    print(f"❌ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()

print("-" * 50)
print("✅ Скрипт завершён")