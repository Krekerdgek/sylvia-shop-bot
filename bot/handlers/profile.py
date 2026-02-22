# -*- coding: utf-8 -*-

"""
Обработчики профиля и статистики
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from datetime import datetime, timedelta

from bot.database.queries import (
    get_user_by_telegram_id, get_user_stats, get_user_cards,
    get_card_stats
)

logger = logging.getLogger(__name__)

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать профиль пользователя и общую статистику"""
    user = update.effective_user
    telegram_id = user.id
    
    # Получаем данные пользователя
    db_user = get_user_by_telegram_id(telegram_id)
    stats = get_user_stats(telegram_id)
    
    if not db_user or not stats:
        await update.message.reply_text("❌ Ошибка получения данных")
        return
    
    # Формируем текст профиля
    text = (
        f"👤 **Профиль пользователя**\n\n"
        f"**ID:** {telegram_id}\n"
        f"**Имя:** {db_user.first_name or 'Не указано'}\n"
        f"**Username:** @{db_user.username or 'Не указан'}\n"
        f"**Регистрация:** {db_user.registered_at.strftime('%d.%m.%Y')}\n\n"
        
        f"📊 **Статистика:**\n"
        f"• Создано визиток: **{stats['cards_created']}**\n"
        f"• Получено сканирований: **{stats['scans_received']}**\n"
        f"• Рефералов: **{stats['referrals_count']}**\n"
        f"• Потрачено звезд: **{stats['spent_stars']} ⭐**\n"
        f"• Бонусный баланс: **{stats['balance']} ⭐**\n\n"
        
        f"🏪 **Магазин:**\n"
        f"Название: {db_user.shop_name or 'Не указано'}\n"
        f"WB: {db_user.shop_url_wb or 'Не указан'}\n"
        f"OZON: {db_user.shop_url_ozon or 'Не указан'}\n\n"
        
        f"📌 **Команды:**\n"
        f"/stats - детальная статистика\n"
        f"/referral - реферальная программа\n"
        f"/edit_shop - изменить данные магазина"
    )
    
    # Кнопки действий
    keyboard = [
        [InlineKeyboardButton("📊 Детальная статистика", callback_data="profile_stats")],
        [InlineKeyboardButton("🛍 Мои визитки", callback_data="profile_cards")],
        [InlineKeyboardButton("🏪 Редактировать магазин", callback_data="profile_edit_shop")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если это callback (пришли из меню)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детальную статистику по визиткам"""
    telegram_id = update.effective_user.id
    
    # Получаем последние визитки
    cards = get_user_cards(telegram_id, limit=5)
    
    if not cards:
        await update.message.reply_text(
            "📊 У вас пока нет созданных визиток.\n"
            "Создайте первую визитку через /new"
        )
        return
    
    text = "📊 **Статистика по последним визиткам:**\n\n"
    
    keyboard = []
    
    for card in cards:
        # Получаем статистику по конкретной визитке
        card_stats = get_card_stats(card.id)
        
        # Определяем тип QR
        qr_types = {
            'product': '📦 Товар',
            'collection': '🛍 Подборка',
            'shop': '🏪 Магазин'
        }
        qr_type_name = qr_types.get(card.qr_type, card.qr_type)
        
        # Форматируем дату
        created = card.created_at.strftime('%d.%m.%Y')
        
        text += (
            f"**Визитка #{card.id}** ({created})\n"
            f"• Тип: {qr_type_name}\n"
            f"• Сканирований: **{card.scan_count}**\n"
        )
        
        if card.last_scan:
            last = card.last_scan.strftime('%d.%m.%Y %H:%M')
            text += f"• Последнее сканирование: {last}\n"
        
        text += "\n"
        
        # Добавляем кнопку для детального просмотра
        keyboard.append([
            InlineKeyboardButton(
                f"📊 Визитка #{card.id}", 
                callback_data=f"stats_card_{card.id}"
            )
        ])
    
    # Добавляем кнопку обновления
    keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="stats_refresh")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_stats_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора периода для статистики"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "stats_refresh":
        await show_stats(update, context)
        return
    
    if query.data.startswith("stats_card_"):
        card_id = int(query.data.replace("stats_card_", ""))
        await show_card_detail(update, context, card_id)

async def show_card_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, card_id):
    """Показать детальную статистику по конкретной визитке"""
    card_stats = get_card_stats(card_id)
    
    if not card_stats:
        await update.callback_query.edit_message_text("❌ Визитка не найдена")
        return
    
    # Формируем текст
    text = f"📊 **Детальная статистика визитки #{card_id}**\n\n"
    text += f"**Всего сканирований:** {card_stats['total']}\n"
    
    if card_stats['last_scan']:
        last = card_stats['last_scan'].strftime('%d.%m.%Y %H:%M')
        text += f"**Последнее сканирование:** {last}\n\n"
    else:
        text += "**Последнее сканирование:** еще не было\n\n"
    
    # Добавляем статистику по дням
    if card_stats['daily']:
        text += "**Сканирования по дням:**\n"
        for day in card_stats['daily'][:7]:  # Последние 7 дней
            text += f"• {day['date']}: {day['count']}\n"
    else:
        text += "Нет данных о сканированиях за последние 30 дней."
    
    # Кнопка "Назад"
    keyboard = [[InlineKeyboardButton("🔙 К списку визиток", callback_data="stats_refresh")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text, 
        reply_markup=reply_markup, 
        parse_mode='Markdown'
    )

async def edit_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование информации о магазине"""
    # Этот обработчик можно добавить позже
    await update.message.reply_text(
        "🛠 Функция редактирования магазина будет доступна позже."
    )
