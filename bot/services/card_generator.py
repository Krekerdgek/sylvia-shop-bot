# -*- coding: utf-8 -*-

"""
Генератор визиток с QR-кодами
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import qrcode
from io import BytesIO
import os
import logging
import textwrap

logger = logging.getLogger(__name__)

class BusinessCardGenerator:
    """Генератор визиток"""
    
    def __init__(self):
        self.templates_path = "templates/"
        self.fonts_path = "fonts/"
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Создание необходимых папок"""
        os.makedirs(self.templates_path, exist_ok=True)
        os.makedirs(self.fonts_path, exist_ok=True)
    
    def _get_font(self, size, bold=False):
        """Получение шрифта"""
        try:
            if bold:
                font_path = os.path.join(self.fonts_path, "Inter-Bold.ttf")
            else:
                font_path = os.path.join(self.fonts_path, "Inter-Regular.ttf")
            
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except Exception as e:
            logger.warning(f"Не удалось загрузить шрифт: {e}")
        
        # Шрифт по умолчанию
        return ImageFont.load_default()
    
    def generate_qr(self, data: str, size=300) -> Image:
        """Генерация QR-кода"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,  # Высокая коррекция для красивых QR
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Создаем изображение QR
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Изменяем размер
        qr_image = qr_image.resize((size, size), Image.Resampling.LANCZOS)
        
        return qr_image
    
    def generate_card(self, template_id: int, card_text: str, qr_data: str, 
                     article=None, product_name=None) -> BytesIO:
        """
        Генерация визитки
        
        Args:
            template_id: ID шаблона (1, 2, 3)
            card_text: Текст на визитке
            qr_data: Данные для QR-кода
            article: Артикул товара (опционально)
            product_name: Название товара (опционально)
        
        Returns:
            BytesIO с изображением
        """
        try:
            # Загружаем шаблон
            template_path = os.path.join(self.templates_path, f"template_{template_id}.png")
            
            if not os.path.exists(template_path):
                # Если шаблон не найден, создаем базовый
                template = self._create_default_template()
            else:
                template = Image.open(template_path).convert("RGBA")
            
            # Создаем копию для работы
            card = template.copy()
            draw = ImageDraw.Draw(card)
            
            # Генерируем QR
            qr_image = self.generate_qr(qr_data)
            
            # Размещаем QR на визитке (зависит от шаблона)
            if template_id == 1:
                # Шаблон 1: QR слева, текст справа
                card.paste(qr_image, (50, 200), qr_image if qr_image.mode == 'RGBA' else None)
                text_x, text_y = 400, 250
                max_width = 350
            elif template_id == 2:
                # Шаблон 2: QR сверху, текст снизу
                card.paste(qr_image, (250, 100), qr_image if qr_image.mode == 'RGBA' else None)
                text_x, text_y = 200, 450
                max_width = 400
            elif template_id == 3:
                # Шаблон 3: QR по центру, текст по краям
                card.paste(qr_image, (150, 150), qr_image if qr_image.mode == 'RGBA' else None)
                text_x, text_y = 50, 500
                max_width = 500
            else:
                # По умолчанию
                card.paste(qr_image, (50, 200))
                text_x, text_y = 400, 250
                max_width = 350
            
            # Добавляем текст
            font_large = self._get_font(32, bold=True)
            font_medium = self._get_font(24)
            font_small = self._get_font(18)
            
            # Основной текст с переносом
            wrapped_text = textwrap.fill(card_text, width=30)
            draw.text((text_x, text_y), wrapped_text, font=font_medium, fill="#333333")
            
            # Добавляем информацию о товаре, если есть
            if article and product_name:
                y_offset = text_y + 100
                draw.text((text_x, y_offset), f"Артикул: {article}", font=font_small, fill="#666666")
                y_offset += 30
                product_short = textwrap.shorten(product_name, width=30, placeholder="...")
                draw.text((text_x, y_offset), product_short, font=font_small, fill="#666666")
            
            # Добавляем призыв к действию
            y_bottom = 550
            draw.text((text_x, y_bottom), "Отсканируйте QR-код", font=font_small, fill="#0066CC")
            
            # Сохраняем в BytesIO
            img_io = BytesIO()
            card.save(img_io, 'PNG', quality=95)
            img_io.seek(0)
            
            return img_io
            
        except Exception as e:
            logger.error(f"Ошибка генерации визитки: {e}")
            # Возвращаем простую заглушку
            return self._create_fallback_card(qr_data)
    
    def _create_default_template(self) -> Image:
        """Создание шаблона по умолчанию"""
        # Создаем белое полотно
        img = Image.new('RGBA', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        # Рисуем рамку
        draw.rectangle([10, 10, 790, 590], outline="#0066CC", width=3)
        
        # Добавляем градиентный фон
        for i in range(600):
            alpha = int(20 * (1 - i/600))
            color = (230, 240, 255, alpha)
            draw.line([(0, i), (800, i)], fill=color)
        
        return img
    
    def _create_fallback_card(self, qr_data) -> BytesIO:
        """Создание простой визитки при ошибке"""
        # Генерируем QR
        qr_image = self.generate_qr(qr_data, size=200)
        
        # Создаем простое изображение
        img = Image.new('RGB', (600, 400), color='white')
        draw = ImageDraw.Draw(img)
        
        # Размещаем QR
        img.paste(qr_image, (200, 100))
        
        # Добавляем текст
        font = self._get_font(20)
        draw.text((200, 320), "Спасибо за покупку!", font=font, fill="black")
        
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return img_io
