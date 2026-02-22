# -*- coding: utf-8 -*-

"""
Вспомогательные функции
"""

import re
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

def generate_token(prefix: str = "") -> str:
    """
    Генерация уникального токена
    
    Args:
        prefix: Префикс для токена
        
    Returns:
        Уникальный токен
    """
    token = str(uuid.uuid4()).replace('-', '')[:16]
    if prefix:
        token = f"{prefix}_{token}"
    return token

def format_price(price: float, currency: str = "₽") -> str:
    """
    Форматирование цены
    
    Args:
        price: Цена
        currency: Валюта
        
    Returns:
        Отформатированная цена
    """
    if price is None:
        return "0 ₽"
    
    if price >= 1000:
        return f"{price:,.0f}".replace(",", " ") + f" {currency}"
    else:
        return f"{price:.0f} {currency}"

def format_date(date: datetime, format: str = "%d.%m.%Y") -> str:
    """
    Форматирование даты
    
    Args:
        date: Дата
        format: Формат
        
    Returns:
        Отформатированная дата
    """
    if not date:
        return "неизвестно"
    return date.strftime(format)

def format_datetime(date: datetime) -> str:
    """
    Форматирование даты и времени
    """
    if not date:
        return "неизвестно"
    return date.strftime("%d.%m.%Y %H:%M")

def time_ago(date: datetime) -> str:
    """
    Относительное время (сколько времени прошло)
    
    Args:
        date: Дата в прошлом
        
    Returns:
        Строка вида "2 часа назад"
    """
    if not date:
        return "никогда"
    
    now = datetime.utcnow()
    diff = now - date
    
    if diff < timedelta(minutes=1):
        return "только что"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} мин. назад"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} ч. назад"
    elif diff < timedelta(days=30):
        days = diff.days
        return f"{days} дн. назад"
    elif diff < timedelta(days=365):
        months = int(diff.days / 30)
        return f"{months} мес. назад"
    else:
        years = int(diff.days / 365)
        return f"{years} г. назад"

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Обрезка текста
    
    Args:
        text: Текст
        max_length: Максимальная длина
        
    Returns:
        Обрезанный текст
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def extract_article_from_text(text: str) -> Optional[str]:
    """
    Извлечение артикула из текста
    
    Args:
        text: Текст, который может содержать артикул
        
    Returns:
        Артикул или None
    """
    if not text:
        return None
    
    # Ищем все цифры
    digits = re.findall(r'\b\d{5,15}\b', text)
    
    if digits:
        return digits[0]
    
    return None

def extract_articles_from_text(text: str) -> List[str]:
    """
    Извлечение всех артикулов из текста
    
    Args:
        text: Текст
        
    Returns:
        Список артикулов
    """
    if not text:
        return []
    
    # Ищем все числа длиной от 5 до 15 цифр
    return re.findall(r'\b\d{5,15}\b', text)

def generate_referral_code(user_id: int) -> str:
    """
    Генерация реферального кода
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Реферальный код
    """
    data = f"{user_id}_{datetime.now().timestamp()}"
    hash_obj = hashlib.md5(data.encode())
    return hash_obj.hexdigest()[:8]

def split_list(lst: List, chunk_size: int) -> List[List]:
    """
    Разделение списка на части
    
    Args:
        lst: Исходный список
        chunk_size: Размер части
        
    Returns:
        Список частей
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def safe_int(value, default: int = 0) -> int:
    """
    Безопасное преобразование в int
    
    Args:
        value: Значение
        default: Значение по умолчанию
        
    Returns:
        Целое число
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default: float = 0.0) -> float:
    """
    Безопасное преобразование в float
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def is_valid_url(url: str) -> bool:
    """
    Проверка валидности URL
    
    Args:
        url: URL для проверки
        
    Returns:
        True если URL валидный
    """
    if not url:
        return False
    
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// или https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # домен
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
        r'(?::\d+)?'  # порт
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return re.match(regex, url) is not None

def clean_text(text: str) -> str:
    """
    Очистка текста от лишних символов
    
    Args:
        text: Исходный текст
        
    Returns:
        Очищенный текст
    """
    if not text:
        return ""
    
    # Удаляем лишние пробелы
    text = re.sub(r'\s+', ' ', text)
    
    # Удаляем спецсимволы
    text = re.sub(r'[^\w\s\.\,\!\?\-\:\;\(\)]', '', text)
    
    return text.strip()
