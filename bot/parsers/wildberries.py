# -*- coding: utf-8 -*-

"""
Парсер Wildberries для получения информации о товарах
"""

import requests
import aiohttp
import asyncio
import logging
import json
import random
from typing import Optional, Dict, List
from fake_useragent import UserAgent
from datetime import datetime

from bot.services.proxy_rotator import ProxyRotator

logger = logging.getLogger(__name__)

class WBParser:
    """Парсер Wildberries"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.proxy_rotator = ProxyRotator()
        self.base_url = "https://card.wb.ru/cards/detail"
        self.search_url = "https://search.wb.ru/exactmatch/ru/common/v4/search"
        
    def _get_headers(self) -> Dict:
        """Получение случайных заголовков"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Origin': 'https://www.wildberries.ru',
            'Referer': 'https://www.wildberries.ru/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
        }
    
    def get_product_info(self, article: str) -> Optional[Dict]:
        """
        Получение информации о товаре по артикулу
        
        Args:
            article: Артикул товара (число)
            
        Returns:
            Словарь с информацией о товаре или None
        """
        try:
            # Очищаем артикул от лишних символов
            article = ''.join(filter(str.isdigit, article))
            
            if not article:
                logger.warning(f"Пустой артикул")
                return None
            
            params = {
                'nm': article
            }
            
            headers = self._get_headers()
            
            # Пробуем без прокси сначала
            response = requests.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_product_response(data, article)
            else:
                logger.warning(f"Ошибка WB API: {response.status_code}")
                
                # Пробуем через прокси
                return self._get_product_with_proxy(article)
                
        except Exception as e:
            logger.error(f"Ошибка парсинга WB артикула {article}: {e}")
            return None
    
    async def get_product_info_async(self, article: str) -> Optional[Dict]:
        """Асинхронное получение информации о товаре"""
        try:
            article = ''.join(filter(str.isdigit, article))
            
            if not article:
                return None
            
            params = {'nm': article}
            headers = self._get_headers()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=10
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_product_response(data, article)
                    else:
                        logger.warning(f"Ошибка WB API: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Ошибка асинхронного парсинга WB: {e}")
            return None
    
    def _get_product_with_proxy(self, article: str) -> Optional[Dict]:
        """Получение товара через прокси"""
        try:
            # Получаем прокси
            proxy = asyncio.run(self.proxy_rotator.get_proxy())
            
            if not proxy:
                logger.warning("Нет доступных прокси")
                return None
            
            proxies = {
                'http': proxy,
                'https': proxy
            }
            
            params = {'nm': article}
            headers = self._get_headers()
            
            response = requests.get(
                self.base_url,
                params=params,
                headers=headers,
                proxies=proxies,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_product_response(data, article)
            else:
                logger.warning(f"Ошибка через прокси: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка запроса через прокси: {e}")
            return None
    
    def _parse_product_response(self, data: Dict, article: str) -> Optional[Dict]:
        """Парсинг ответа от API Wildberries"""
        try:
            products = data.get('data', {}).get('products', [])
            
            if not products:
                logger.info(f"Товар {article} не найден")
                return None
            
            product = products[0]
            
            # Извлекаем данные
            name = product.get('name', '')
            brand = product.get('brand', '')
            price = product.get('salePriceU', 0) / 100  # В копейках
            old_price = product.get('priceU', 0) / 100
            rating = product.get('rating', 0)
            reviews = product.get('feedbacks', 0)
            volume = product.get('volume', 0)
            
            # Скидка
            discount = 0
            if old_price > 0:
                discount = round((1 - price / old_price) * 100)
            
            # Формируем результат
            result = {
                'article': article,
                'name': name,
                'brand': brand,
                'price': price,
                'old_price': old_price,
                'discount': discount,
                'rating': rating,
                'reviews': reviews,
                'volume': volume,
                'url': f"https://www.wildberries.ru/catalog/{article}/detail.aspx",
                'marketplace': 'wb',
                'parsed_at': datetime.now().isoformat()
            }
            
            logger.info(f"Успешно спарсен товар WB: {article} - {name[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка парсинга ответа WB: {e}")
            return None
    
    def search_products(self, query: str, limit: int = 5) -> List[Dict]:
        """Поиск товаров по запросу"""
        try:
            params = {
                'query': query,
                'resultset': 'catalog',
                'sort': 'popular',
                'limit': limit
            }
            
            headers = self._get_headers()
            
            response = requests.get(
                self.search_url,
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('data', {}).get('products', [])
                
                results = []
                for product in products[:limit]:
                    results.append({
                        'article': product.get('id'),
                        'name': product.get('name'),
                        'brand': product.get('brand'),
                        'price': product.get('salePriceU', 0) / 100,
                        'rating': product.get('rating', 0),
                        'url': f"https://www.wildberries.ru/catalog/{product.get('id')}/detail.aspx"
                    })
                
                return results
            else:
                logger.warning(f"Ошибка поиска: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Ошибка поиска товаров: {e}")
            return []
    
    def validate_article(self, article: str) -> bool:
        """Проверка существования артикула"""
        info = self.get_product_info(article)
        return info is not None

## Файл: `bot/parsers/ozon.py`


# -*- coding: utf-8 -*-

"""
Парсер Ozon для получения информации о товарах
"""

import requests
import aiohttp
import logging
import json
import re
from typing import Optional, Dict, List
from fake_useragent import UserAgent
from datetime import datetime

logger = logging.getLogger(__name__)

class OzonParser:
    """Парсер Ozon"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.api_url = "https://api.ozon.ru/v1/product/info"
        self.card_url = "https://www.ozon.ru/product/{}/"
        
    def _get_headers(self) -> Dict:
        """Получение случайных заголовков"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/json',
            'Origin': 'https://www.ozon.ru',
            'Referer': 'https://www.ozon.ru/',
        }
    
    def get_product_info(self, article: str) -> Optional[Dict]:
        """
        Получение информации о товаре по артикулу Ozon
        
        Args:
            article: Артикул товара (число)
            
        Returns:
            Словарь с информацией о товаре или None
        """
        try:
            # Очищаем артикул
            article = ''.join(filter(str.isdigit, article))
            
            if not article:
                logger.warning(f"Пустой артикул")
                return None
            
            # Ozon API требует артикул в числовом формате
            product_id = int(article)
            
            headers = self._get_headers()
            
            # Пробуем через публичный API
            response = requests.get(
                f"https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2?url=/product/{product_id}/",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_product_response(data, article)
            else:
                logger.warning(f"Ошибка Ozon API: {response.status_code}")
                
                # Пробуем альтернативный метод
                return self._get_product_alternative(article)
                
        except Exception as e:
            logger.error(f"Ошибка парсинга Ozon артикула {article}: {e}")
            return None
    
    def _get_product_alternative(self, article: str) -> Optional[Dict]:
        """Альтернативный метод получения информации о товаре"""
        try:
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'ru-RU,ru;q=0.9',
            }
            
            url = f"https://www.ozon.ru/product/{article}/"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                html = response.text
                
                # Парсим название
                name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
                name = name_match.group(1).strip() if name_match else "Неизвестный товар"
                
                # Парсим цену
                price_match = re.search(r'"price":"(\d+)"', html)
                price = int(price_match.group(1)) / 100 if price_match else 0
                
                # Парсим бренд
                brand_match = re.search(r'"brand":"([^"]+)"', html)
                brand = brand_match.group(1) if brand_match else ""
                
                # Парсим рейтинг
                rating_match = re.search(r'"rating":([\d.]+)', html)
                rating = float(rating_match.group(1)) if rating_match else 0
                
                return {
                    'article': article,
                    'name': name,
                    'brand': brand,
                    'price': price,
                    'rating': rating,
                    'reviews': 0,  # Не парсим для простоты
                    'url': url,
                    'marketplace': 'ozon',
                    'parsed_at': datetime.now().isoformat()
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Ошибка альтернативного парсинга: {e}")
            return None
    
    def _parse_product_response(self, data: Dict, article: str) -> Optional[Dict]:
        """Парсинг ответа от Ozon"""
        try:
            # Извлекаем данные из сложной структуры Ozon
            widget_states = data.get('widgetStates', {})
            
            name = "Неизвестный товар"
            price = 0
            brand = ""
            rating = 0
            
            # Ищем информацию в разных виджетах
            for key, value in widget_states.items():
                if 'webProductHeading' in key:
                    try:
                        heading_data = json.loads(value)
                        name = heading_data.get('title', name)
                    except:
                        pass
                
                elif 'webPrice' in key:
                    try:
                        price_data = json.loads(value)
                        price = price_data.get('price', 0) / 100
                    except:
                        pass
                
                elif 'webProductRating' in key:
                    try:
                        rating_data = json.loads(value)
                        rating = rating_data.get('rating', 0)
                    except:
                        pass
            
            result = {
                'article': article,
                'name': name,
                'brand': brand,
                'price': price,
                'rating': rating,
                'reviews': 0,
                'url': f"https://www.ozon.ru/product/{article}/",
                'marketplace': 'ozon',
                'parsed_at': datetime.now().isoformat()
            }
            
            logger.info(f"Успешно спарсен товар Ozon: {article}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка парсинга ответа Ozon: {e}")
            return None
    
    async def get_product_info_async(self, article: str) -> Optional[Dict]:
        """Асинхронное получение информации о товаре"""
        try:
            article = ''.join(filter(str.isdigit, article))
            
            if not article:
                return None
            
            headers = self._get_headers()
            url = f"https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2?url=/product/{article}/"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_product_response(data, article)
                    else:
                        logger.warning(f"Ошибка Ozon API: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Ошибка асинхронного парсинга Ozon: {e}")
            return None
    
    def validate_article(self, article: str) -> bool:
        """Проверка существования артикула"""
        info = self.get_product_info(article)
        return info is not None
