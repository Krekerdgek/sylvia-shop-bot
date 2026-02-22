# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env файле")

# База данных
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///sylvia.db')

# URL для редиректов
REDIRECT_BASE_URL = os.getenv('REDIRECT_BASE_URL', 'http://localhost:5000')

# Прокси
PROXY_LIST_URL = os.getenv('PROXY_LIST_URL', 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt')

# Администраторы
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# Платежи
PAYMENT_TOKEN = os.getenv('PAYMENT_TOKEN')

# Настройки
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
BACKUP_DIR = os.getenv('BACKUP_DIR', 'backups')
TEMPLATES_DIR = os.getenv('TEMPLATES_DIR', 'templates')

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен")

# Стоимость шаблонов (в звездах)
TEMPLATE_PRICES = {
    1: 10,  # Бесплатный
    2: 50,  # Платный
    3: 100, # Премиум
}
