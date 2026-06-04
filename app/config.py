import os
from dotenv import load_dotenv

# Đọc các biến môi trường từ file .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")
PORT = int(os.getenv("PORT", 5000))
PROJECT_NAME = os.getenv("PROJECT_NAME", "ota-travel")
