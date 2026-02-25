# bot/parsers/ozon.py
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class OzonParser:
    """Парсер Ozon (временная заглушка)"""
    
    def get_product_info(self, article: str) -> Optional[Dict]:
        """
        Заглушка для получения информации о товаре
        """
        logger.info(f"Запрос информации по артикулу Ozon: {article}")
        
        # Простая проверка формата
        if not article or not article.isdigit():
            return None
            
        # Возвращаем тестовые данные
        return {
            'article': article,
            'name': f'Товар {article}',
            'brand': 'Ozon Brand',
            'price': 999,
            'rating': 4.5,
            'reviews': 100,
            'url': f'https://www.ozon.ru/product/{article}',
            'marketplace': 'ozon'
        }
    
    def validate_article(self, article: str) -> bool:
        """Проверка существования артикула"""
        return self.get_product_info(article) is not None
