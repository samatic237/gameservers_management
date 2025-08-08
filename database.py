import sqlite3
import contextlib
from config import Config

def get_db():
    """Получение соединения с БД"""
    db = sqlite3.connect(Config.DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db

@contextlib.contextmanager
def db_connection():
    """Контекстный менеджер для работы с БД"""
    db = get_db()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Инициализация БД"""
    with db_connection() as db, open(Config.SCHEMA_PATH) as f:
        db.executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    """Выполнение запроса к БД"""
    with db_connection() as db:
        cur = db.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Выполнение запроса без возврата данных"""
    with db_connection() as db:
        db.execute(query, args)
        db.commit()