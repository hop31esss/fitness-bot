from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta
import secrets
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Конфигурация
ADMIN_PASSWORD = "Tima79022"  # Измените на свой пароль!
DB_PATH = "fitness_bot.db"

def get_db():
    """Подключение к базе данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Неверный пароль")
    return render_template('login.html')

@app.route('/')
def dashboard():
    """Главная админ-панель"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    conn = get_db()
    
    # Статистика
    users = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()['count']
    workouts = conn.execute("SELECT COUNT(*) as count FROM workouts").fetchone()['count']
    premium = conn.execute("SELECT COUNT(*) as count FROM users WHERE is_subscribed=1").fetchone()['count']
    
    # Активные сегодня
    today = datetime.now().date().isoformat()
    active_today = conn.execute(
        "SELECT COUNT(DISTINCT user_id) as count FROM workouts WHERE date(created_at)=?",
        (today,)
    ).fetchone()['count']
    
    # Рост пользователей
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    new_users = conn.execute(
        "SELECT COUNT(*) as count FROM users WHERE created_at > ?",
        (week_ago,)
    ).fetchone()['count']
    
    conn.close()
    
    return render_template('dashboard.html', 
                         users=users, 
                         workouts=workouts, 
                         premium=premium,
                         active_today=active_today,
                         new_users=new_users)

@app.route('/users')
def users():
    """Список пользователей"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    conn = get_db()
    
    users_list = conn.execute("""
        SELECT user_id, username, first_name, created_at, is_subscribed,
               subscription_until
        FROM users
        ORDER BY created_at DESC
        LIMIT 100
    """).fetchall()
    
    conn.close()
    
    return render_template('users.html', users=users_list)

@app.route('/backup')
def backup():
    """Создание бэкапа"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    import shutil
    from datetime import datetime
    import os
    
    # Создаем папку если её нет
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Имя файла с датой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, filename)
    
    # Копируем базу
    shutil.copy2('fitness_bot.db', backup_path)
    
    # Размер файла
    size = os.path.getsize(backup_path) / 1024 / 1024  # в MB
    
    # Сообщение об успехе
    success_msg = f"✅ Бэкап создан: {filename} ({size:.2f} MB)"
    
    return f"""
    <html>
    <head>
        <title>Бэкап создан</title>
        <meta http-equiv="refresh" content="3;url=/" />
        <style>
            body {{ font-family: Arial; text-align: center; padding: 50px; background: #f5f5f5; }}
            .message {{ background: #d4edda; color: #155724; padding: 20px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="message">
            <h2>{success_msg}</h2>
            <p>Через 3 секунды вы вернетесь на главную...</p>
        </div>
    </body>
    </html>
    """

@app.route('/backups')
def backups_list():
    """Список всех бэкапов"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    import os
    from datetime import datetime
    
    backup_dir = "backups"
    backups = []
    
    if os.path.exists(backup_dir):
        for file in os.listdir(backup_dir):
            if file.endswith('.db'):
                filepath = os.path.join(backup_dir, file)
                size = os.path.getsize(filepath) / 1024 / 1024
                modified = datetime.fromtimestamp(os.path.getmtime(filepath))
                backups.append({
                    'name': file,
                    'size': f"{size:.2f} MB",
                    'date': modified.strftime("%Y-%m-%d %H:%M:%S")
                })
    
    # Сортируем по дате (новые сверху)
    backups.sort(key=lambda x: x['date'], reverse=True)
    
    html = """
    <html>
    <head>
        <title>Бэкапы</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f5f5f5; }
            table { width: 100%; background: white; border-collapse: collapse; }
            th { background: #2c3e50; color: white; padding: 10px; }
            td { padding: 10px; border-bottom: 1px solid #ddd; }
            .nav { margin-bottom: 20px; }
            .nav a { margin-right: 15px; color: #3498db; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="nav">
            <a href="/">Главная</a>
            <a href="/users">Пользователи</a>
            <a href="/backup">Создать бэкап</a>
            <a href="/backups">Все бэкапы</a>
            <a href="/logout">Выйти</a>
        </div>
        
        <h2>📦 Все резервные копии</h2>
        
        <table>
            <tr>
                <th>Файл</th>
                <th>Дата создания</th>
                <th>Размер</th>
            </tr>
    """
    
    for b in backups:
        html += f"""
            <tr>
                <td>{b['name']}</td>
                <td>{b['date']}</td>
                <td>{b['size']}</td>
            </tr>
        """
    
    html += """
        </table>
    </body>
    </html>
    """
    
    return html    

@app.route('/logout')
def logout():
    """Выход"""
    session.pop('admin', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)