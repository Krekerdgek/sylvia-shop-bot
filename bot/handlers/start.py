# -*- coding: utf-8 -*-

"""
Обработчики команды /start и базовых команд
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from bot.database.queries import get_or_create_user, process_referral

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    telegram_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name
    
    # Проверяем, есть ли реферальный код в аргументах
    args = context.args
    referral_code = args[0] if args else None
    
    # Создаем или получаем пользователя
    db_user = get_or_create_user(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )
    
    # Если есть реферальный код и он не свой
    if referral_code and referral_code != db_user.referral_code:
        process_referral(referral_code, telegram_id)
        await update.message.reply_text(
            "🎉 Вас пригласил друг! Вам начислен бонус при регистрации."
        )
    
    # Приветственное сообщение
    welcome_text = (
        f"👋 Привет, {first_name}!\n\n"
        f"Я — **Sylvia Bot**, твой помощник в создании визиток для заказов на Wildberries и Ozon.\n\n"
        f"🎯 **Что я умею:**\n"
        f"• Создавать визитки с QR-кодами за 1 минуту\n"
        f"• Добавлять ссылки на товар, подборку или магазин\n"
        f"• Отслеживать статистику сканирований\n"
        f"• Помогать собирать отзывы и повышать повторные продажи\n\n"
        f"📌 **Начните прямо сейчас:**\n"
        f"👉 /new - создать новую визитку\n"
        f"👉 /profile - мой профиль и статистика\n"
        f"👉 /referral - реферальная программа\n"
        f"👉 /help - помощь"
    )
    
    # Клавиатура с основными действиями
    keyboard = [
        [InlineKeyboardButton("✨ Создать визитку", callback_data="new_card")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="show_stats")],
        [InlineKeyboardButton("🎁 Реферальная программа", callback_data="show_referral")],
        [InlineKeyboardButton("❓ Помощь", callback_data="show_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    logger.info(f"Пользователь {telegram_id} запустил бота")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "❓ **Помощь по Sylvia Bot**\n\n"
        "**Команды:**\n"
        "/start - перезапустить бота\n"
        "/new - создать новую визитку\n"
        "/profile - профиль и статистика\n"
        "/stats - детальная статистика\n"
        "/referral - реферальная программа\n"
        "/balance - баланс бонусов\n"
        "/buy - купить шаблоны\n"
        "/help - это сообщение\n\n"
        
        "**Как это работает:**\n"
        "1️⃣ Вы выбираете шаблон визитки\n"
        "2️⃣ Выбираете, куда будет вести QR-код\n"
        "3️⃣ Вводите артикул товара (если нужно)\n"
        "4️⃣ Бот генерирует визитку\n"
        "5️⃣ Вы печатаете и вкладываете в заказы\n"
        "6️⃣ Отслеживаете статистику в /profile\n\n"
        
        "**Типы QR-кодов:**\n"
        "📦 **На товар** - ссылка на конкретный товар (для отзывов)\n"
        "🛍 **На подборку** - несколько товаров для допродаж\n"
        "🏪 **На магазин** - ссылка на весь ваш магазин\n\n"
        
        "**Реферальная программа:**\n"
        "Приглашайте друзей и получайте бонусные визитки!\n"
        "Ваша ссылка: /referral"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов с главного меню"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "new_card":
        # Перенаправляем на создание визитки
        from bot.handlers.order import new_card
        await new_card(update, context)
    
    elif query.data == "show_stats":
        # Показываем статистику
        from bot.handlers.profile import show_profile
        await show_profile(update, context)
    
    elif query.data == "show_referral":
        # Показываем реферальную программу
        from bot.handlers.referral import show_referral
        await show_referral(update, context)
    
    elif query.data == "show_help":
        # Показываем помощь
        await help_command(update, context)
