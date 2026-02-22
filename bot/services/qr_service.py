# -*- coding: utf-8 -*-

"""
Сервис для работы с QR-кодами и генерации ссылок
"""

import qrcode
from io import BytesIO
import hashlib
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class QRService:
    """Сервис для работы с QR-кодами"""
    
    def __init__(self, base_url):
        self.base_url = base_url
    
    def generate_qr_image(self, data: str, size=300) -> BytesIO:
        """Генерация изображения QR-кода"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size, size))
        
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return img_io
    
    def generate_tracking_url(self, card_id: int, token: str, qr_type: str, 
                              article=None, collection_id=None) -> str:
        """
        Генерация URL для отслеживания
        
        Args:
            card_id: ID визитки
            token: Уникальный токен
            qr_type: Тип QR (product, collection, shop)
            article: Артикул товара
            collection_id: ID подборки
        
        Returns:
            Полный URL для редиректа
        """
        return f"{self.base_url}/go/{token}"
    
    def generate_tracking_token(self, user_id: int, card_id: int) -> str:
        """Генерация уникального токена для отслеживания"""
        data = f"{user_id}_{card_id}_{datetime.now().timestamp()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def decode_token(self, token: str) -> dict:
        """Декодирование токена (заглушка, реальная логика в БД)"""
        # В реальности данные хранятся в БД
        return {'token': token}
