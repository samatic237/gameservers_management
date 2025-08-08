import requests
import psutil  # Для получения нагрузки
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import hashlib
import json
from datetime import datetime

SERVER_ID = 1  # Уникальный ID каждого сервера
CENTRAL_SERVER_URL = "http://127.0.0.1:5000/api/update_load"
SECRET_KEY = "secret-key"

def encrypt_data(data: dict) -> str:
    """Шифрование данных с использованием AES"""
    # Преобразуем словарь в строку JSON
    json_data = json.dumps(data)
    
    # Создаем ключ из секрета
    key = hashlib.sha256(SECRET_KEY.encode()).digest()
    
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
    key = hashlib.sha256(SECRET_KEY.encode()).digest()
    
    # Создаем объект дешифрования
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    
    # Дешифруем данные и убираем дополнение
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    
    # Преобразуем JSON обратно в словарь
    return json.loads(pt.decode('utf-8'))

def get_server_load():
    """Получаем текущую нагрузку сервера"""
    cpu_load = psutil.cpu_percent(interval=1)
    ram_load = psutil.virtual_memory().percent
    return round((cpu_load))

def send_load_to_central():
    while True:
        try:
            load = get_server_load()
            data = {
                "server_id": SERVER_ID,
                "load": load,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Шифруем данные перед отправкой
            encrypted_data = encrypt_data(data)
            
            # Отправляем зашифрованные данные
            response = requests.post(
                CENTRAL_SERVER_URL,
                json={"data": encrypted_data},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                print(f"Ошибка отправки: {response.text}")
            else:
                print("SENDED LOAD "+str(load)+"%")
        except Exception as e:
            print(f"Ошибка: {str(e)}")
        
        time.sleep(5)

if __name__ == "__main__":
    send_load_to_central()