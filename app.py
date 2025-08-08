from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import hashlib
import os
import json
from threading import Thread
from functools import wraps
from config import Config
import time
from datetime import datetime , timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# Хэширование пароля
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Доступ запрещен. Требуется авторизация.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def encrypt_data(data: dict) -> str:
    """Шифрование данных с использованием AES"""
    # Преобразуем словарь в строку JSON
    json_data = json.dumps(data)
    
    # Создаем ключ из секрета
    key = hashlib.sha256(app.config['SECRET_KEY'].encode()).digest()
    
    # Создаем объект шифрования
    cipher = AES.new(key, AES.MODE_CBC)
    
    # Шифруем данные с дополнением
    ct_bytes = cipher.encrypt(pad(json_data.encode(), AES.block_size))
    
    # Объединяем IV и зашифрованные данные
    iv = cipher.iv
    encrypted_data = iv + ct_bytes
    
    # Кодируем в base64 для передачи
    return base64.b64encode(encrypted_data).decode('utf-8')

def decrypt_data(encrypted_data: str) -> dict:
    """Дешифрование данных с использованием AES"""
    # Декодируем из base64
    encrypted_data = base64.b64decode(encrypted_data)
    
    # Извлекаем IV и зашифрованные данные
    iv = encrypted_data[:AES.block_size]
    ct = encrypted_data[AES.block_size:]
    
    # Создаем ключ из секрета
    key = hashlib.sha256(app.config['SECRET_KEY'].encode()).digest()
    
    # Создаем объект дешифрования
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    
    # Дешифруем данные и убираем дополнение
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    
    # Преобразуем JSON обратно в словарь
    return json.loads(pt.decode('utf-8'))



def get_db():
    """соединение с БД"""
    db = sqlite3.connect(app.config['DATABASE_PATH'])
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """инициализация БД"""
    try:
        db = get_db()
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read().decode('utf-8'))
        
        # Проверяем, есть ли уже администраторы
        admin_count = db.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0]
        
        if admin_count == 0:
            hashed_pw = hash_password(app.config['ADMIN_PASSWORD'])
            db.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                ('admin', hashed_pw, 1)
            )
            db.commit()
            print("Создан администратор по умолчанию: admin/"+app.config['ADMIN_PASSWORD'])
    except Exception as e:
        print(f"Ошибка инициализации БД: {e}")
        raise
    finally:
        if 'db' in locals():
            db.close()

def check_db_exists():
    if not os.path.exists(app.config['DATABASE_PATH']):
        return False
    
    try:
        db = get_db()
        tables = db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name IN ('servers', 'registrations', 'server_load_history', 'users')
        """).fetchall()
        return len(tables) == 4
    except:
        return False
    finally:
        db.close()

def background_updater():
    """Фоновая задача для периодического обновления"""
    while True:
        try:
            db = get_db()
            # Можно добавить дополнительную логику проверки
            db.close()
        except Exception as e:
            print(f"Background error: {e}")
        time.sleep(5)
def reset_limits_task():
    """Фоновая задача для сброса лимитов"""
    while True:
        try:
            with app.app_context():
                db = get_db()
                # Удаляем записи старше 24 часов
                db.execute("""
                    DROP TABLE IF EXISTS registration_limits
                """)
                db.execute("""CREATE TABLE registration_limits (
                    ip_address TEXT PRIMARY KEY,
                    request_count INTEGER DEFAULT 1,
                    first_request_time TEXT NOT NULL,
                    last_request_time TEXT NOT NULL
                    )""")
                db.commit()
                app.logger.info("Старые лимиты очищены")
        except Exception as e:
            app.logger.error(f"Ошибка сброса лимитов: {str(e)}", exc_info=True)
        finally:
            if db:
                db.close()
            time.sleep(3600*24)  # Проверяем каждый час*24

@app.before_request
def ensure_db_exists():
    if not check_db_exists():
        os.makedirs(os.path.dirname(app.config['DATABASE_PATH']), exist_ok=True)
        init_db()
def block_suspicious_ips():
    if request.endpoint == 'register':
        ip = request.remote_addr
        db = get_db()
        suspicious = db.execute(
            "SELECT 1 FROM registration_limits WHERE ip_address = ? AND request_count > ?",
            (ip, app.config['REGISTRATION_LIMITS']['MAX_REQUESTS_PER_DAY'] * 2)
        ).fetchone()
        if suspicious:
            return "Превышен лимит запросов", 429

@app.route('/api/update_load', methods=['POST'])
def update_load():
    """API для обновления нагрузки с автоматической чисткой старых данных"""
    try:
        # Получаем и дешифруем данные
        encrypted_data = request.json.get('data')
        if not encrypted_data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        data = decrypt_data(encrypted_data)
        
        db = get_db()
        try:
            # Обновляем текущую нагрузку
            db.execute(
                "UPDATE servers SET current_load = ? WHERE id = ?",
                (data['load'], data['server_id'])
            )
            
            # Добавляем новое значение в историю
            db.execute(
                """INSERT INTO server_load_history 
                (server_id, load_value, timestamp) 
                VALUES (?, ?, ?)""",
                (data['server_id'], data['load'], data['timestamp'])
            )
            
            # Чистим старые данные
            db.execute("""
                DELETE FROM server_load_history 
                WHERE id NOT IN (
                    SELECT id FROM server_load_history 
                    WHERE server_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 40
                ) AND server_id = ?
            """, (data['server_id'], data['server_id']))
            
            db.commit()
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
        finally:
            db.close()
    except Exception as e:
        return jsonify({"status": "error", "message": "Decryption failed"}), 400

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Заполните все поля', 'danger')
            return redirect(url_for('login'))
        
        try:
            db = get_db()
            user = db.execute(
                "SELECT id, username, password_hash, is_admin FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            
            if user and user['password_hash'] == hash_password(password):
                # Успешная авторизация
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = bool(user['is_admin'])
                session['is_authenticated'] = True
                
                next_page = request.args.get('next') or url_for('admin')
                flash('Вы успешно авторизовались', 'success')
                return redirect(next_page)
            else:
                flash('Неверные учетные данные', 'danger')
        except Exception as e:
            flash('Ошибка авторизации', 'danger')
            print(f"Ошибка: {e}")
        finally:
            if 'db' in locals():
                db.close()
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    db = get_db()
    servers = db.execute("SELECT * FROM servers").fetchall()
    registrations = db.execute("""
        SELECT r.id, r.nickname, r.request_ip, r.registration_date, 
               s.ip_address, s.purpose 
        FROM registrations r 
        JOIN servers s ON r.server_id = s.id
        ORDER BY r.registration_date DESC
    """).fetchall()
    db.close()
    
    return render_template('admin.html', servers=servers, registrations=registrations)
   
@app.route('/admin/update_load', methods=['POST'])
@login_required
def update_server_load():  # Переименовал для соответствия
    db = get_db()
    try:
        server_id = request.form['server_id']
        load_value = int(request.form['load_value'])
        
        db.execute(
            "UPDATE servers SET current_load = ? WHERE id = ?",
            (load_value, server_id)
        )
        db.commit()
        flash('Нагрузка сервера обновлена', 'success')
    except (ValueError, KeyError):
        flash('Некорректные данные', 'danger')
    except sqlite3.Error as e:
        flash('Ошибка базы данных', 'danger')
        print(f"Database error: {e}")
    finally:
        db.close()
    
    return redirect(url_for('admin'))

@app.route('/admin/delete_server/<int:server_id>', methods=['POST'])
@login_required
def delete_server(server_id):
    db = get_db()
    try:
        # Проверяем существование сервера
        server = db.execute(
            "SELECT id FROM servers WHERE id = ?", 
            (server_id,)
        ).fetchone()
        
        if not server:
            flash('Сервер не найден', 'danger')
            return redirect(url_for('admin'))
        
        # Проверяем есть ли активные регистрации
        registrations_count = db.execute(
            "SELECT COUNT(*) FROM registrations WHERE server_id = ?",
            (server_id,)
        ).fetchone()[0]
        
        if registrations_count > 0:
            flash('Нельзя удалить сервер с активными регистрациями', 'danger')
            return redirect(url_for('admin'))
        
        # Удаляем историю нагрузки
        db.execute(
            "DELETE FROM server_load_history WHERE server_id = ?",
            (server_id,)
        )
        
        # Удаляем сам сервер
        db.execute(
            "DELETE FROM servers WHERE id = ?",
            (server_id,)
        )
        
        db.commit()
        flash('Сервер успешно удален', 'success')
    except sqlite3.Error as e:
        db.rollback()
        flash(f'Ошибка при удалении сервера: {str(e)}', 'danger')
    finally:
        db.close()
    
    return redirect(url_for('admin'))


@app.route('/admin/add_server', methods=['POST'])
@login_required
def add_server():
    ip = request.form.get('ip_address', '').strip()
    purpose = request.form.get('purpose', '').strip()
    is_available = request.form.get('is_available') == 'on'
    
    if not ip or not purpose:
        flash('Заполните все обязательные поля', 'danger')
        return redirect(url_for('admin'))
    
    try:
        db = get_db()
        db.execute(
            "INSERT INTO servers (ip_address, purpose, is_available) VALUES (?, ?, ?)",
            (ip, purpose, is_available)
        )
        db.commit()
        flash('Сервер успешно добавлен', 'success')
    except sqlite3.IntegrityError:
        flash('Сервер с таким IP уже существует', 'danger')
    except Exception as e:
        flash(f'Ошибка при добавлении сервера: {str(e)}', 'danger')
    finally:
        db.close()
    
    return redirect(url_for('admin'))

@app.route('/')
def index():
    db = get_db()
    try:
        servers = db.execute("SELECT * FROM servers").fetchall()
        return render_template('index.html', servers=servers)
    finally:
        db.close()
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/get_chart_data/<int:server_id>')
def get_chart_data(server_id):
    db = get_db()
    try:
        history = db.execute("""
            SELECT load_value, strftime('%H:%M', timestamp) as time
            FROM server_load_history
            WHERE server_id = ? AND timestamp >= datetime('now', '-1 day')
            ORDER BY timestamp
        """, (server_id,)).fetchall()
        
        chart_data = {
            'labels': [row['time'] for row in history],
            'data': [row['load_value'] for row in history]
        }
        return json.dumps(chart_data)
    finally:
        db.close()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        ip = request.remote_addr
        nickname = request.form.get('nickname', '').strip()
        server_id = request.form.get('server_id', '')
        
        # Валидация входных данных
        if not nickname or not server_id:
            flash('Заполните все поля', 'danger')
            return redirect(url_for('register'))
            
        try:
            db = get_db()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Проверка лимитов
            limit = db.execute(
                """SELECT request_count, 
                          julianday('now') - julianday(first_request_time) as days_passed
                   FROM registration_limits 
                   WHERE ip_address = ?""",
                (ip,)
            ).fetchone()
            
            if limit:
                if limit['days_passed'] < 1 and \
                   limit['request_count'] >= app.config['REGISTRATION_LIMITS']['MAX_REQUESTS_PER_DAY']:
                    flash('Превышен лимит заявок за сутки', 'danger')
                    return redirect(url_for('register'))
                
                # Обновляем счетчик
                db.execute(
                    """UPDATE registration_limits 
                    SET request_count = request_count + 1, 
                        last_request_time = ? 
                    WHERE ip_address = ?""",
                    (now, ip)
                )
            else:
                # Новая запись
                db.execute(
                    """INSERT INTO registration_limits 
                    (ip_address, first_request_time, last_request_time) 
                    VALUES (?, ?, ?)""",
                    (ip, now, now)
                )
            
            # Проверка ника
            if len(nickname) < 3 or len(nickname) > 80:
                flash('Никнейм должен быть от 3 до 80 символов', 'danger')
                return redirect(url_for('register'))
            
            # Проверка сервера
            server = db.execute(
                "SELECT id FROM servers WHERE id = ? AND is_available = 1",
                (server_id,)
            ).fetchone()
            
            if not server:
                flash('Выбранный сервер недоступен', 'danger')
                return redirect(url_for('register'))
            
            # Создаем заявку
            db.execute(
                "INSERT INTO registrations (request_ip, nickname, server_id) VALUES (?, ?, ?)",
                (ip, nickname, server_id)
            )
            
            db.commit()
            flash('Заявка успешно отправлена!', 'success')
            return redirect(url_for('register'))
            
        except sqlite3.Error as e:
            db.rollback()
            flash('Ошибка базы данных при обработке заявки', 'danger')
            app.logger.error(f"DB error in registration: {str(e)}", exc_info=True)
        except Exception as e:
            flash('Неожиданная ошибка', 'danger')
            app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        finally:
            if db:
                db.close()
    
    # GET запрос
    try:
        db = get_db()
        servers = db.execute("SELECT * FROM servers WHERE is_available = 1").fetchall()
        return render_template('register.html', servers=servers)
    except Exception as e:
        flash('Ошибка загрузки списка серверов', 'danger')
        app.logger.error(f"Server list error: {str(e)}", exc_info=True)
        return redirect(url_for('index'))
    finally:
        if db:
            db.close()

@app.route('/admin/toggle_server/<int:server_id>', methods=['POST'])
@login_required
def toggle_server(server_id):
    db = get_db()
    try:
        server = db.execute(
            "SELECT is_available FROM servers WHERE id = ?",
            (server_id,)
        ).fetchone()
        
        if server:
            new_status = not server['is_available']
            db.execute(
                "UPDATE servers SET is_available = ? WHERE id = ?",
                (new_status, server_id)
            )
            db.commit()
            flash('Статус сервера обновлен', 'success')
    except sqlite3.Error as e:
        flash('Ошибка при изменении статуса сервера', 'error')
        print(f"Database error: {e}")
    finally:
        db.close()
    return redirect(url_for('admin'))

@app.route('/admin/delete_registration/<int:reg_id>', methods=['POST'])
@login_required
def delete_registration(reg_id):
    db = get_db()
    try:
        db.execute("DELETE FROM registrations WHERE id = ?", (reg_id,))
        db.commit()
        flash('Заявка успешно удалена', 'success')
    except sqlite3.Error as e:
        flash('Ошибка при удалении заявки', 'error')
        print(f"Database error: {e}")
    finally:
        db.close()
    return redirect(url_for('admin'))




if __name__ == '__main__':
    os.makedirs(os.path.dirname(app.config['DATABASE_PATH']), exist_ok=True)
    if not check_db_exists():
        print("Инициализация новой БД...")
        init_db()
    Thread(target=reset_limits_task, daemon=True).start()
    Thread(target=background_updater, daemon=True).start()
    app.run(host='0.0.0.0',debug=False,port=app.config["PORT"])