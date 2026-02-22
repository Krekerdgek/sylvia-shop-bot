# -*- coding: utf-8 -*-

"""
Ротатор бесплатных прокси для парсеров
"""

import aiohttp
import asyncio
import random
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from bot.config import PROXY_LIST_URL

logger = logging.getLogger(__name__)

class ProxyRotator:
    """Ротатор бесплатных прокси"""
    
    def __init__(self):
        self.proxies: List[str] = []
        self.last_update = None
        self.update_interval = timedelta(hours=6)
        self.current_index = 0
    
    async def update_proxies(self):
        """Обновление списка прокси"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(PROXY_LIST_URL, timeout=10) as response:
                    if response.status == 200:
                        text = await response.text()
                        # Фильтруем только HTTP прокси
                        proxies = [line.strip() for line in text.split('\n') 
                                 if line.strip() and '://' in line]
                        
                        # Добавляем схему, если её нет
                        self.proxies = [f"http://{p}" if not p.startswith('http') else p 
                                      for p in proxies]
                        
                        self.last_update = datetime.now()
                        logger.info(f"Обновлено прокси: {len(self.proxies)} штук")
                    else:
                        logger.error(f"Ошибка загрузки прокси: {response.status}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении прокси: {e}")
            
            # Если список пуст, добавляем несколько рабочих по умолчанию
            if not self.proxies:
                self.proxies = [
                    "http://51.158.68.68:8811",
                    "http://51.158.120.36:8811",
                    "http://51.158.111.244:8811"
                ]
    
    async def get_proxy(self) -> Optional[str]:
        """Получение случайного прокси"""
        # Проверяем, нужно ли обновить список
        if (not self.proxies or 
            not self.last_update or 
            datetime.now() - self.last_update > self.update_interval):
            await self.update_proxies()
        
        if not self.proxies:
            return None
        
        # Возвращаем случайный прокси
        return random.choice(self.proxies)
    
    async def get_proxy_round_robin(self) -> Optional[str]:
        """Получение прокси по кругу (round-robin)"""
        if not self.proxies:
            await self.update_proxies()
        
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    async def test_proxy(self, proxy: str) -> bool:
        """Тестирование прокси"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://httpbin.org/ip", 
                    proxy=proxy, 
                    timeout=5
                ) as response:
                    return response.status == 200
        except:
            return False
    
    async def get_working_proxy(self) -> Optional[str]:
        """Получение рабочего прокси (с тестированием)"""
        for _ in range(5):  # Пробуем 5 раз
            proxy = await self.get_proxy()
            if not proxy:
                return None
            
            if await self.test_proxy(proxy):
                return proxy
            
            # Удаляем нерабочий прокси
            if proxy in self.proxies:
                self.proxies.remove(proxy)
        
        return None
