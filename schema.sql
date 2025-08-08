CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT UNIQUE NOT NULL,
    purpose TEXT NOT NULL,
    is_available BOOLEAN DEFAULT 1,
    current_load INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_ip TEXT NOT NULL,
    nickname TEXT NOT NULL,
    server_id INTEGER NOT NULL,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
    
);
-- Удаляем старую таблицу если есть
DROP TABLE IF EXISTS registration_limits;

-- Создаем новую с правильными типами
CREATE TABLE registration_limits (
    ip_address TEXT PRIMARY KEY,
    request_count INTEGER DEFAULT 1,
    first_request_time TEXT NOT NULL,
    last_request_time TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS server_load_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id INTEGER NOT NULL,
    load_value INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (server_id) REFERENCES servers (id) ON DELETE CASCADE
);
-- Начальные данные серверов
INSERT INTO servers (ip_address, purpose, is_available, current_load)
VALUES 
    ('192.168.1.10', 'Minecraft Creative', 1, 45),
    ('192.168.1.11', 'Minecraft Survival', 1, 65),
    ('192.168.1.12', 'CS:GO Competitive', 1, 30),
    ('192.168.1.13', 'Team Fortress 2', 0, 0);