# -*- coding: utf-8 -*-

"""
Обработчики реферальной программы
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from bot.database.queries import get_user_by_telegram_id, get_referral_stats
from bot.config import REDIRECT_BASE_URL

logger = logging.getLogger(__name__)

async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о реферальной программе"""
    user = update.effective_user
    telegram_id = user.id
    
    # Получаем статистику
    stats = get_referral_stats(telegram_id)
    
    if not stats:
        await update.message.reply_text(
            "❌ Ошибка получения данных. Попробуйте позже."
        )
        return
    
    # Формируем реферальную ссылку
    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={stats['code']}"
    
    text = (
        "🎁 **Реферальная программа**\n\n"
        "Приглашайте друзей и получайте бонусы!\n\n"
        "**Как это работает:**\n"
        "1️⃣ Отправьте другу вашу реферальную ссылку\n"
        "2️⃣ Друг переходит по ссылке и запускает бота\n"
        "3️⃣ Вы получаете **1 бонусную визитку**\n"
        "4️⃣ Друг тоже получает приветственный бонус\n\n"
        "📊 **Ваша статистика:**\n"
        f"• Приглашено друзей: **{stats['total']}**\n"
        f"• За последние 30 дней: **{stats['recent']}**\n"
        f"• Бонусный баланс: **{stats['balance']} ⭐**\n\n"
        "🔗 **Ваша реферальная ссылка:**\n"
        f"`{referral_link}`\n\n"
        "Нажмите на ссылку чтобы скопировать."
    )
    
    # Кнопки для действий
    keyboard = [
        [InlineKeyboardButton("📤 Поделиться ссылкой", switch_inline_query=referral_link)],
        [InlineKeyboardButton("🔄 Обновить статистику", callback_data="ref_refresh")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Если это callback (обновление)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущий баланс бонусов"""
    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)
    
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    text = (
        f"💰 **Ваш баланс**\n\n"
        f"Бонусные визитки: **{user.referral_balance} ⭐**\n\n"
        f"1 ⭐ = 1 платный шаблон или 1 визитка\n\n"
        f"Чтобы получить больше бонусов:\n"
        f"• Приглашайте друзей (/referral)\n"
        f"• Покупайте шаблоны (/buy)"
    )
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def handle_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов реферальной программы"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "ref_refresh":
        # Обновляем статистику
        await show_referral(update, context)
