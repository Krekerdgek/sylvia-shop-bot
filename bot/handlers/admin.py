# -*- coding: utf-8 -*-

"""
Административные команды и панель управления
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging

from bot.config import ADMIN_IDS
from bot.database.queries import get_admin_stats, get_all_users
from bot.database.db import session_scope
from bot.database.models import User, Template

logger = logging.getLogger(__name__)

def is_admin(telegram_id):
    """Проверка, является ли пользователь администратором"""
    return telegram_id in ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Панель администратора"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет прав доступа к этой команде.")
        return
    
    # Получаем статистику
    stats = get_admin_stats()
    
    text = (
        "👑 **Админ-панель Sylvia Bot**\n\n"
        f"📊 **Статистика:**\n"
        f"• Всего пользователей: **{stats['users']['total']}**\n"
        f"• Активных сегодня: **{stats['users']['active_today']}**\n"
        f"• Создано визиток: **{stats['cards']['total']}**\n"
        f"• Всего сканирований: **{stats['scans']['total']}**\n"
        f"• Сканирований сегодня: **{stats['scans']['today']}**\n"
        f"• Выручка: **{stats['revenue']} ⭐**\n\n"
        
        f"🏆 **Топ пользователей:**\n"
    )
    
    for i, user in enumerate(stats['top_users'], 1):
        username = user['username'] or f"id{user['telegram_id']}"
        text += f"{i}. @{username} — {user['cards']} визиток\n"
    
    # Кнопки управления
    keyboard = [
        [InlineKeyboardButton("👥 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton("🎨 Управление шаблонами", callback_data="admin_templates")],
        [InlineKeyboardButton("📊 Детальная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_refresh")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback-запросов от админ-панели"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔ Доступ запрещен.")
        return
    
    if query.data == "admin_refresh":
        await admin_panel(update, context)
    
    elif query.data == "admin_users":
        await show_users_list(update, context)
    
    elif query.data == "admin_templates":
        await manage_templates(update, context)
    
    elif query.data == "admin_stats":
        await show_detailed_stats(update, context)
    
    elif query.data == "admin_broadcast":
        await start_broadcast(update, context)
    
    elif query.data.startswith("admin_user_"):
        user_id = int(query.data.replace("admin_user_", ""))
        await show_user_detail(update, context, user_id)

async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список пользователей"""
    users = get_all_users(active_only=True)
    
    text = "👥 **Список пользователей**\n\n"
    
    keyboard = []
    
    for user in users[:10]:  # Показываем только первых 10
        username = user.username or f"id{user.telegram_id}"
        text += f"• @{username} — {user.cards_created} визиток\n"
        
        # Добавляем кнопку для каждого пользователя
        keyboard.append([
            InlineKeyboardButton(
                f"👤 @{username}", 
                callback_data=f"admin_user_{user.telegram_id}"
            )
        ])
    
    if len(users) > 10:
        text += f"\n... и еще {len(users) - 10} пользователей"
    
    text += f"\n\nВсего: {len(users)} активных пользователей"
    
    # Кнопка "Назад"
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_refresh")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text, 
        reply_markup=reply_markup, 
        parse_mode='Markdown'
    )

async def show_user_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, telegram_id):
    """Показать детальную информацию о пользователе"""
    from bot.database.queries import get_user_by_telegram_id, get_user_stats
    
    user = get_user_by_telegram_id(telegram_id)
    stats = get_user_stats(telegram_id)
    
    if not user:
        await update.callback_query.edit_message_text("❌ Пользователь не найден")
        return
    
    text = (
        f"👤 **Детальная информация о пользователе**\n\n"
        f"**Telegram ID:** {telegram_id}\n"
        f"**Username:** @{user.username or 'Нет'}\n"
        f"**Имя:** {user.first_name or 'Нет'}\n"
        f"**Регистрация:** {user.registered_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"**Последняя активность:** {user.last_activity.strftime('%d.%m.%Y %H:%M')}\n"
        f"**Админ:** {'Да' if user.is_admin else 'Нет'}\n\n"
        
        f"📊 **Статистика:**\n"
        f"• Визиток: {stats['cards_created']}\n"
        f"• Сканирований: {stats['scans_received']}\n"
        f"• Рефералов: {stats['referrals_count']}\n"
        f"• Потрачено звезд: {stats['spent_stars']}\n"
        f"• Баланс: {stats['balance']}\n\n"
        
        f"🏪 **Магазин:**\n"
        f"Название: {user.shop_name or 'Не указано'}\n"
        f"WB: {user.shop_url_wb or 'Не указан'}\n"
        f"OZON: {user.shop_url_ozon or 'Не указан'}\n"
    )
    
    # Кнопки действий
    keyboard = [
        [InlineKeyboardButton("🔙 К списку", callback_data="admin_users")],
        [InlineKeyboardButton("🔄 Обновить", callback_data=f"admin_user_{telegram_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text, 
        reply_markup=reply_markup, 
        parse_mode='Markdown'
    )

async def manage_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление шаблонами"""
    from bot.database.queries import get_all_templates
    
    templates = get_all_templates(active_only=False)
    
    text = "🎨 **Управление шаблонами**\n\n"
    
    keyboard = []
    
    for template in templates:
        status = "✅" if template.is_active else "❌"
        price_info = f"{template.price} ⭐" if template.price > 0 else "Бесплатный"
        
        text += f"{status} **{template.name}** — {price_info}\n"
        text += f"   ID: {template.id} | Категория: {template.category}\n"
        
        # Кнопки для каждого шаблона
        row = [
            InlineKeyboardButton(
                f"{'✅' if template.is_active else '❌'} Вкл/Выкл", 
                callback_data=f"admin_template_toggle_{template.id}"
            ),
            InlineKeyboardButton(
                f"✏️ Редакт", 
                callback_data=f"admin_template_edit_{template.id}"
            )
        ]
        keyboard.append(row)
    
    # Кнопка добавления нового шаблона
    keyboard.append([InlineKeyboardButton("➕ Добавить шаблон", callback_data="admin_template_add")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_refresh")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text, 
        reply_markup=reply_markup, 
        parse_mode='Markdown'
    )

async def show_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать детальную статистику"""
    # Здесь можно добавить графики и более подробную статистику
    await update.callback_query.edit_message_text(
        "📊 Функция детальной статистики в разработке.\n\n"
        "Скоро здесь будут графики и аналитика.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад", callback_data="admin_refresh")
        ]])
    )

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начать рассылку"""
    await update.callback_query.edit_message_text(
        "📢 Функция рассылки в разработке.\n\n"
        "Скоро вы сможете отправлять сообщения всем пользователям.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад", callback_data="admin_refresh")
        ]])
    )
