# bot/handlers/start.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    telegram_id = user.id
    
    # Приветственное сообщение
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я — **Sylvia Bot**, твой помощник в создании визиток для заказов на Wildberries и Ozon.\n\n"
        f"📌 **Начните прямо сейчас:**\n"
        f"👉 /new - создать новую визитку\n"
        f"👉 /profile - мой профиль и статистика\n"
        f"👉 /referral - реферальная программа\n"
        f"👉 /help - помощь"
    )
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "❓ **Помощь по Sylvia Bot**\n\n"
        "/new - создать новую визитку\n"
        "/profile - профиль и статистика\n"
        "/referral - реферальная программа\n"
        "/buy - купить шаблоны\n"
        "/help - это сообщение"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')
