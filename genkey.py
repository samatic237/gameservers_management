import secrets
import uuid

def generate_api_key():
    return str(uuid.uuid4())

key = generate_api_key()+"-"+generate_api_key()
print(key)