import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database():
    """Обновление схемы базы данных"""
    conn = sqlite3.connect('fitness_bot.db')
    cursor = conn.cursor()
    
    # 1. Таблица тренировок (сессий)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            start_time TIME,
            end_time TIME,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    logger.info("✅ Таблица workout_sessions создана")
    
    # 2. Таблица упражнений в тренировке (БЕЗ created_at)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            exercise_type TEXT DEFAULT 'strength',
            sets INTEGER,
            reps INTEGER,
            weight REAL,
            duration INTEGER,
            distance REAL,
            pace TEXT,
            speed REAL,
            notes TEXT,
            order_num INTEGER,
            FOREIGN KEY (session_id) REFERENCES workout_sessions (id)
        )
    """)
    logger.info("✅ Таблица workout_exercises создана")
    
    # 3. Обновляем старую таблицу workouts (переносим данные)
    cursor.execute("SELECT COUNT(*) FROM workouts")
    if cursor.fetchone()[0] > 0:
        logger.info("🔄 Переносим старые данные...")
        
        # Получаем все старые тренировки
        cursor.execute("""
            SELECT user_id, date(created_at) as workout_date, 
                   exercise_name, sets, reps, weight, created_at
            FROM workouts
            ORDER BY user_id, created_at
        """)
        old_workouts = cursor.fetchall()
        
        # Группируем по пользователю и дате
        sessions = {}
        for w in old_workouts:
            key = (w[0], w[1])  # (user_id, date)
            if key not in sessions:
                sessions[key] = []
            sessions[key].append(w)
        
        # Создаем сессии и добавляем упражнения
        for (user_id, date), exercises in sessions.items():
            # Создаем сессию
            cursor.execute("""
                INSERT INTO workout_sessions (user_id, date, created_at)
                VALUES (?, ?, ?)
            """, (user_id, date, exercises[0][6]))  # берем время первого упражнения
            
            session_id = cursor.lastrowid
            
            # Добавляем упражнения
            for ex in exercises:
                cursor.execute("""
                    INSERT INTO workout_exercises 
                    (session_id, exercise_name, sets, reps, weight, order_num)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (session_id, ex[2], ex[3], ex[4], ex[5], exercises.index(ex) + 1))
        
        logger.info(f"✅ Перенесено {len(sessions)} тренировок")
    
    conn.commit()
    conn.close()
    logger.info("🎉 База данных обновлена!")

if __name__ == "__main__":
    update_database()