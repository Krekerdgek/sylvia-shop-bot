# -*- coding: utf-8 -*-

"""
Функции валидации данных
"""

import re
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)

def validate_article(article: str, marketplace: str = 'wb') -> Tuple[bool, Optional[str]]:
    """
    Валидация артикула товара
    
    Args:
        article: Артикул для проверки
        marketplace: Маркетплейс ('wb' или 'ozon')
        
    Returns:
        (валиден ли, сообщение об ошибке)
    """
    if not article:
        return False, "Артикул не может быть пустым"
    
    # Удаляем пробелы
    article = article.strip()
    
    # Проверяем, что это число
    if not article.isdigit():
        return False, "Артикул должен содержать только цифры"
    
    # Проверяем длину в зависимости от маркетплейса
    if marketplace == 'wb':
        if len(article) < 5 or len(article) > 15:
            return False, "Артикул Wildberries обычно содержит от 5 до 15 цифр"
    elif marketplace == 'ozon':
        if len(article) < 5 or len(article) > 20:
            return False, "Артикул Ozon обычно содержит от 5 до 20 цифр"
    
    return True, None

def validate_articles_list(text: str) -> Tuple[bool, Optional[str], List[str]]:
    """
    Валидация списка артикулов
    
    Args:
        text: Текст с артикулами через запятую
        
    Returns:
        (валиден ли, сообщение об ошибке, список артикулов)
    """
    if not text:
        return False, "Список артикулов не может быть пустым", []
    
    # Разделяем по запятой
    parts = [p.strip() for p in text.split(',') if p.strip()]
    
    if len(parts) < 2:
        return False, "Введите минимум 2 артикула", []
    
    if len(parts) > 5:
        return False, "Максимум 5 артикулов в подборке", []
    
    # Проверяем каждый артикул
    articles = []
    invalid = []
    
    for part in parts:
        # Удаляем лишние символы
        article = ''.join(filter(str.isdigit, part))
        
        if not article:
            invalid.append(part)
        else:
            articles.append(article)
    
    if invalid:
        return False, f"Некорректные артикулы: {', '.join(invalid)}", articles
    
    return True, None, articles

def validate_shop_url(url: str, marketplace: str = 'wb') -> Tuple[bool, Optional[str]]:
    """
    Валидация URL магазина
    
    Args:
        url: URL для проверки
        marketplace: Маркетплейс
        
    Returns:
        (валиден ли, сообщение об ошибке)
    """
    if not url:
        return True, None  # URL может быть пустым
    
    url = url.strip()
    
    # Базовая проверка URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Проверяем домен в зависимости от маркетплейса
    if marketplace == 'wb':
        if 'wildberries.ru' not in url and 'wb.ru' not in url:
            return False, "URL должен вести на Wildberries (wildberries.ru или wb.ru)"
    elif marketplace == 'ozon':
        if 'ozon.ru' not in url:
            return False, "URL должен вести на Ozon (ozon.ru)"
    
    return True, None

def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация номера телефона
    
    Args:
        phone: Номер телефона
        
    Returns:
        (валиден ли, сообщение об ошибке)
    """
    if not phone:
        return True, None  # Телефон может быть пустым
    
    # Удаляем все кроме цифр
    digits = ''.join(filter(str.isdigit, phone))
    
    # Проверяем длину (Российские номера 10-11 цифр)
    if len(digits) < 10 or len(digits) > 12:
        return False, "Некорректная длина номера телефона"
    
    return True, None

def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация email
    
    Args:
        email: Email для проверки
        
    Returns:
        (валиден ли, сообщение об ошибке)
    """
    if not email:
        return True, None
    
    email = email.strip().lower()
    
    # Простая проверка формата
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Некорректный формат email"
    
    return True, None

def validate_template_id(template_id: int, available_templates: List[int]) -> Tuple[bool, Optional[str]]:
    """
    Валидация ID шаблона
    
    Args:
        template_id: ID шаблона
        available_templates: Список доступных ID
        
    Returns:
        (валиден ли, сообщение об ошибке)
    """
    if template_id not in available_templates:
        return False, "Выбранный шаблон недоступен"
    
    return True, None

def validate_referral_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация реферального кода
    
    Args:
        code: Реферальный код
        
    Returns:
        (валиден ли, сообщение об ошибке)
    """
    if not code:
        return False, "Реферальный код не может быть пустым"
    
    # Реферальный код - 8 символов (буквы и цифры)
    if not re.match(r'^[a-zA-Z0-9]{8}$', code):
        return False, "Некорректный формат реферального кода"
    
    return True, None

def validate_payment_amount(amount: int, min_amount: int = 1) -> Tuple[bool, Optional[str]]:
    """
    Валидация суммы платежа
    
    Args:
        amount: Сумма в звездах
        min_amount: Минимальная сумма
        
    Returns:
        (валиден ли, сообщение об ошибке)
    """
    if amount < min_amount:
        return False, f"Минимальная сумма платежа {min_amount} ⭐"
    
    if amount > 1000:
        return False, "Максимальная сумма платежа 1000 ⭐"
    
    return True, None

def sanitize_input(text: str) -> str:
    """
    Санитизация пользовательского ввода (удаление опасных символов)
    
    Args:
        text: Входной текст
        
    Returns:
        Очищенный текст
    """
    if not text:
        return ""
    
    # Удаляем потенциально опасные символы
    # (для Telegram ботов это не так критично, но для профилактики)
    dangerous = ['<', '>', '&', '"', "'", ';', '`', '$', '(', ')']
    
    for char in dangerous:
        text = text.replace(char, '')
    
    return text.strip()
