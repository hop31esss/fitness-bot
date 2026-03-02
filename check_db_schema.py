import sqlite3

conn = sqlite3.connect('fitness_bot.db')
cursor = conn.cursor()

# Проверяем структуру таблицы users
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()

print("📊 Структура таблицы users:")
for col in columns:
    print(f"   {col[1]} - {col[2]}")

conn.close()