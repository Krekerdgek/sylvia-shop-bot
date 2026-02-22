# -*- coding: utf-8 -*-

"""
Обработчики создания визиток
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import uuid
from datetime import datetime

from bot.database.queries import (
    get_user_by_telegram_id, create_business_card, 
    get_all_templates, get_template, add_favorite_article,
    get_favorite_articles, use_referral_balance
)
from bot.services.card_generator import BusinessCardGenerator
from bot.parsers.wildberries import WBParser
from bot.parsers.ozon import OzonParser
from bot.config import REDIRECT_BASE_URL, TEMPLATE_PRICES

logger = logging.getLogger(__name__)

# Инициализация сервисов
card_generator = BusinessCardGenerator()
wb_parser = WBParser()
ozon_parser = OzonParser()

# Состояния пользователей (хранятся в context.user_data)
STATES = {
    'SELECTING_TEMPLATE': 1,
    'SELECTING_QR_TYPE': 2,
    'ENTERING_ARTICLE': 3,
    'ENTERING_COLLECTION': 4,
    'CONFIRMING_PAYMENT': 5
}

async def new_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания новой визитки - выбор шаблона"""
    user = update.effective_user
    
    # Получаем все доступные шаблоны
    templates = get_all_templates(active_only=True)
    
    if not templates:
        await update.effective_message.reply_text(
            "❌ Временно нет доступных шаблонов. Попробуйте позже."
        )
        return
    
    # Создаем клавиатуру с шаблонами
    keyboard = []
    row = []
    
    for i, template in enumerate(templates):
        # Определяем цену
        price_info = ""
        if template.price > 0:
            price_info = f" ({template.price} ⭐)"
        else:
            price_info = " (бесплатно)"
        
        button = InlineKeyboardButton(
            f"{template.name}{price_info}", 
            callback_data=f"template_{template.id}"
        )
        row.append(button)
        
        # По 2 кнопки в ряд
        if (i + 1) % 2 == 0 or i == len(templates) - 1:
            keyboard.append(row)
            row = []
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Текст с описанием
    text = (
        "🎨 **Выберите шаблон для визитки**\n\n"
        "После выбора шаблона вы сможете настроить QR-код и создать визитку."
    )
    
    # Если это callback (пришли из меню), редактируем сообщение
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    context.user_data['state'] = STATES['SELECTING_TEMPLATE']

async def handle_template_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора шаблона"""
    query = update.callback_query
    await query.answer()
    
    template_id = int(query.data.split('_')[1])
    template = get_template(template_id)
    
    if not template:
        await query.edit_message_text("❌ Шаблон не найден")
        return
    
    # Сохраняем выбранный шаблон
    context.user_data['template_id'] = template_id
    context.user_data['template_price'] = template.price
    
    # Проверяем, платный ли шаблон
    user = get_user_by_telegram_id(update.effective_user.id)
    
    if template.price > 0 and user.referral_balance < template.price:
        # Не хватает бонусов - предлагаем купить
        keyboard = [
            [InlineKeyboardButton("💎 Купить шаблон", callback_data=f"buy_template_{template_id}")],
            [InlineKeyboardButton("🔙 Назад к шаблонам", callback_data="back_to_templates")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ У вас недостаточно бонусов для этого шаблона.\n\n"
            f"Стоимость: {template.price} ⭐\n"
            f"Ваш баланс: {user.referral_balance} ⭐\n\n"
            f"Вы можете купить шаблон за Telegram Stars или получить бонусы по реферальной программе.",
            reply_markup=reply_markup
        )
        return
    
    # Если бесплатный или хватает бонусов - показываем выбор типа QR
    await show_qr_type_selection(update, context, query)

async def show_qr_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    """Показ выбора типа QR-кода"""
    if not query:
        query = update.callback_query
        await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📦 На этот товар (для отзывов)", callback_data="qr_type_product")],
        [InlineKeyboardButton("🛍 На подборку товаров", callback_data="qr_type_collection")],
        [InlineKeyboardButton("🏪 На мой магазин", callback_data="qr_type_shop")],
        [InlineKeyboardButton("🔙 Назад к шаблонам", callback_data="back_to_templates")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔗 **Куда будет вести QR-код?**\n\n"
        "Выберите тип ссылки:\n\n"
        "📦 **На товар** - покупатель попадет на страницу этого товара (удобно для отзывов)\n"
        "🛍 **На подборку** - покажете покупателю сопутствующие товары\n"
        "🏪 **На магазин** - ссылка на весь ваш магазин",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    context.user_data['state'] = STATES['SELECTING_QR_TYPE']

async def handle_qr_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа QR"""
    query = update.callback_query
    await query.answer()
    
    qr_type = query.data.replace('qr_type_', '')
    context.user_data['qr_type'] = qr_type
    
    if qr_type == 'product':
        # Спрашиваем артикул товара
        await query.edit_message_text(
            "📦 Введите **артикул товара** на Wildberries или Ozon\n\n"
            "Например: `12345678`\n\n"
            "Я проверю, существует ли такой товар."
        )
        context.user_data['state'] = STATES['ENTERING_ARTICLE']
        context.user_data['awaiting'] = 'article'
        
    elif qr_type == 'collection':
        # Спрашиваем список артикулов
        await query.edit_message_text(
            "🛍 Введите **артикулы товаров** для подборки через запятую\n\n"
            "Например: `12345678, 87654321, 13579246`\n\n"
            "Минимум 2 артикула, максимум 5."
        )
        context.user_data['state'] = STATES['ENTERING_COLLECTION']
        context.user_data['awaiting'] = 'collection'
        
    elif qr_type == 'shop':
        # Сразу генерируем визитку со ссылкой на магазин
        await generate_card(update, context, query)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ввода (артикулы и т.д.)"""
    if 'state' not in context.user_data or 'awaiting' not in context.user_data:
        return
    
    user_input = update.message.text.strip()
    awaiting_type = context.user_data['awaiting']
    
    if awaiting_type == 'article':
        await handle_article_input(update, context, user_input)
    elif awaiting_type == 'collection':
        await handle_collection_input(update, context, user_input)

async def handle_article_input(update: Update, context: ContextTypes.DEFAULT_TYPE, article):
    """Обработка ввода артикула товара"""
    # Проверяем, что ввели только цифры
    if not article.isdigit():
        await update.message.reply_text(
            "❌ Артикул должен содержать только цифры. Попробуйте еще раз:"
        )
        return
    
    # Определяем маркетплейс по длине артикула (примерно)
    marketplace = 'wb'
    if len(article) > 10:
        marketplace = 'ozon'
    
    # Проверяем существование товара
    if marketplace == 'wb':
        product = wb_parser.get_product_info(article)
    else:
        product = ozon_parser.get_product_info(article)
    
    if not product:
        await update.message.reply_text(
            "❌ Товар с таким артикулом не найден. Проверьте артикул и попробуйте снова:"
        )
        return
    
    # Сохраняем данные
    context.user_data['article'] = article
    context.user_data['product_name'] = product['name']
    context.user_data['marketplace'] = marketplace
    
    # Спрашиваем, сохранить ли в избранное
    keyboard = [
        [InlineKeyboardButton("✅ Да, сохранить", callback_data="save_favorite")],
        [InlineKeyboardButton("⏭ Нет, продолжить", callback_data="continue_without_save")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ **Товар найден!**\n\n"
        f"**Название:** {product['name']}\n"
        f"**Цена:** {product['price']} ₽\n"
        f"**Рейтинг:** {product['rating']} ⭐\n"
        f"**Отзывы:** {product['reviews']}\n\n"
        f"Сохранить этот артикул в избранное для быстрого доступа?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    context.user_data['awaiting'] = 'favorite_choice'

async def handle_collection_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    """Обработка ввода подборки товаров"""
    # Разбираем артикулы
    articles = [a.strip() for a in text.split(',') if a.strip().isdigit()]
    
    if len(articles) < 2:
        await update.message.reply_text(
            "❌ Введите минимум 2 артикула через запятую. Попробуйте еще раз:"
        )
        return
    
    if len(articles) > 5:
        await update.message.reply_text(
            "❌ Максимум 5 артикулов в подборке. Попробуйте еще раз:"
        )
        return
    
    # Проверяем каждый артикул (первые 2 для скорости)
    valid_articles = []
    invalid_articles = []
    
    for article in articles[:3]:  # Проверяем только первые 3 для скорости
        product = wb_parser.get_product_info(article)
        if product:
            valid_articles.append(article)
        else:
            invalid_articles.append(article)
    
    if invalid_articles:
        await update.message.reply_text(
            f"❌ Не найдены товары с артикулами: {', '.join(invalid_articles)}\n"
            f"Проверьте артикулы и попробуйте снова:"
        )
        return
    
    # Сохраняем подборку
    context.user_data['collection'] = articles
    
    # Генерируем уникальный ID для подборки
    collection_id = str(uuid.uuid4())[:8]
    context.user_data['collection_id'] = collection_id
    
    await generate_card(update, context)

async def handle_favorite_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора - сохранять ли в избранное"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "save_favorite":
        # Сохраняем в избранное
        telegram_id = update.effective_user.id
        article = context.user_data.get('article')
        product_name = context.user_data.get('product_name')
        marketplace = context.user_data.get('marketplace', 'wb')
        
        add_favorite_article(telegram_id, article, product_name, marketplace)
        
        await query.edit_message_text(
            f"✅ Артикул сохранен в избранное!\n\n"
            f"Теперь вы можете быстро выбирать его при создании визиток."
        )
    
    # Генерируем визитку
    await generate_card(update, context, query)

async def generate_card(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    """Генерация финальной визитки"""
    user = update.effective_user
    telegram_id = user.id
    
    # Получаем данные из контекста
    template_id = context.user_data.get('template_id', 1)
    qr_type = context.user_data.get('qr_type', 'shop')
    template_price = context.user_data.get('template_price', 0)
    
    # Проверяем, нужно ли списать бонусы
    if template_price > 0:
        # Списываем бонусы
        if not use_referral_balance(telegram_id, template_price):
            if query:
                await query.edit_message_text(
                    "❌ Недостаточно бонусов для создания визитки."
                )
            else:
                await update.message.reply_text(
                    "❌ Недостаточно бонусов для создания визитки."
                )
            return
    
    # Генерируем уникальный токен для визитки
    token = str(uuid.uuid4())[:8]
    
    # Формируем данные для QR
    redirect_url = f"{REDIRECT_BASE_URL}/go/{token}"
    
    # Подготавливаем параметры для сохранения
    card_params = {
        'telegram_id': telegram_id,
        'template_id': template_id,
        'qr_type': qr_type,
        'token': token
    }
    
    # Добавляем специфичные параметры
    if qr_type == 'product':
        article = context.user_data.get('article')
        card_params['article'] = article
        card_text = f"Спасибо за покупку!\nОставьте отзыв на товар {article}"
        
    elif qr_type == 'collection':
        collection_id = context.user_data.get('collection_id')
        card_params['collection_id'] = collection_id
        card_text = "Спасибо за покупку!\nВам также может пригодиться:"
        
    else:  # shop
        card_text = f"Спасибо за покупку!\nВозвращайтесь снова!"
    
    # Сохраняем в БД
    card_id = create_business_card(**card_params)
    
    if not card_id:
        error_text = "❌ Ошибка при сохранении визитки. Попробуйте позже."
        if query:
            await query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)
        return
    
    # Генерируем изображение
    try:
        card_image = card_generator.generate_card(
            template_id=template_id,
            card_text=card_text,
            qr_data=redirect_url,
            article=context.user_data.get('article'),
            product_name=context.user_data.get('product_name')
        )
    except Exception as e:
        logger.error(f"Ошибка генерации визитки: {e}")
        error_text = "❌ Ошибка при создании изображения. Попробуйте другой шаблон."
        if query:
            await query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)
        return
    
    # Отправляем пользователю
    caption = (
        "✅ **Ваша визитка готова!**\n\n"
        f"📌 **Тип QR:** {get_qr_type_name(qr_type)}\n"
        f"🎨 **Шаблон:** {template_id}\n\n"
        "📥 Скачайте изображение и используйте для печати.\n"
        "📊 Статистика по визитке будет доступна в /profile"
    )
    
    if query:
        await query.edit_message_text("🔄 Генерация завершена, отправляю файл...")
        await query.message.reply_photo(
            photo=card_image,
            caption=caption,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_photo(
            photo=card_image,
            caption=caption,
            parse_mode='Markdown'
        )
    
    # Очищаем данные состояния
    context.user_data.clear()
    
    logger.info(f"Создана визитка {card_id} для пользователя {telegram_id}")

def get_qr_type_name(qr_type):
    """Получить название типа QR"""
    names = {
        'product': '📦 На товар',
        'collection': '🛍 На подборку',
        'shop': '🏪 На магазин'
    }
    return names.get(qr_type, qr_type)

async def back_to_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться к выбору шаблонов"""
    query = update.callback_query
    await query.answer()
    
    # Очищаем данные
    context.user_data.clear()
    
    # Возвращаемся к выбору шаблонов
    await new_card(update, context)
