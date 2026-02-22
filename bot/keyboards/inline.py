# -*- coding: utf-8 -*-

"""
Инлайн-клавиатуры для бота
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu_keyboard():
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("✨ Создать визитку", callback_data="new_card")],
        [InlineKeyboardButton("📊 Моя статистика", callback_data="show_stats")],
        [InlineKeyboardButton("🎁 Реферальная программа", callback_data="show_referral")],
        [InlineKeyboardButton("❓ Помощь", callback_data="show_help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def templates_keyboard(templates):
    """Клавиатура выбора шаблонов"""
    keyboard = []
    row = []
    
    for i, template in enumerate(templates):
        # Определяем цену
        price_info = ""
        if template.price > 0:
            price_info = f" ({template.price}⭐)"
        
        button = InlineKeyboardButton(
            f"{template.name}{price_info}", 
            callback_data=f"template_{template.id}"
        )
        row.append(button)
        
        # По 2 кнопки в ряд
        if (i + 1) % 2 == 0 or i == len(templates) - 1:
            keyboard.append(row)
            row = []
    
    return InlineKeyboardMarkup(keyboard)

def qr_type_keyboard():
    """Клавиатура выбора типа QR"""
    keyboard = [
        [InlineKeyboardButton("📦 На этот товар (для отзывов)", callback_data="qr_type_product")],
        [InlineKeyboardButton("🛍 На подборку товаров", callback_data="qr_type_collection")],
        [InlineKeyboardButton("🏪 На мой магазин", callback_data="qr_type_shop")],
        [InlineKeyboardButton("🔙 Назад к шаблонам", callback_data="back_to_templates")]
    ]
    return InlineKeyboardMarkup(keyboard)

def favorite_choice_keyboard():
    """Клавиатура выбора сохранения в избранное"""
    keyboard = [
        [InlineKeyboardButton("✅ Да, сохранить", callback_data="save_favorite")],
        [InlineKeyboardButton("⏭ Нет, продолжить", callback_data="continue_without_save")],
    ]
    return InlineKeyboardMarkup(keyboard)

def payment_keyboard(template_id, template_name, price):
    """Клавиатура подтверждения платежа"""
    keyboard = [
        [InlineKeyboardButton(f"✅ Оплатить {price} ⭐", callback_data="confirm_payment")],
        [InlineKeyboardButton("🔙 Отмена", callback_data="cancel_payment")]
    ]
    return InlineKeyboardMarkup(keyboard)

def profile_keyboard():
    """Клавиатура профиля"""
    keyboard = [
        [InlineKeyboardButton("📊 Детальная статистика", callback_data="profile_stats")],
        [InlineKeyboardButton("🛍 Мои визитки", callback_data="profile_cards")],
        [InlineKeyboardButton("🏪 Редактировать магазин", callback_data="profile_edit_shop")]
    ]
    return InlineKeyboardMarkup(keyboard)

def stats_keyboard(cards):
    """Клавиатура статистики по визиткам"""
    keyboard = []
    
    for card in cards[:5]:  # Максимум 5 визиток
        keyboard.append([
            InlineKeyboardButton(
                f"📊 Визитка #{card.id} ({card.scan_count} сканирований)", 
                callback_data=f"stats_card_{card.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="stats_refresh")])
    
    return InlineKeyboardMarkup(keyboard)

def back_button(callback_data="back"):
    """Кнопка назад"""
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)

def admin_main_keyboard():
    """Главное меню админки"""
    keyboard = [
        [InlineKeyboardButton("👥 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton("🎨 Управление шаблонами", callback_data="admin_templates")],
        [InlineKeyboardButton("📊 Детальная статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔄 Обновить", callback_data="admin_refresh")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_users_keyboard(users):
    """Клавиатура списка пользователей для админки"""
    keyboard = []
    
    for user in users[:10]:
        username = user.username or f"id{user.telegram_id}"
        keyboard.append([
            InlineKeyboardButton(
                f"👤 @{username} ({user.cards_created} визиток)", 
                callback_data=f"admin_user_{user.telegram_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_refresh")])
    
    return InlineKeyboardMarkup(keyboard)

def admin_templates_keyboard(templates):
    """Клавиатура управления шаблонами"""
    keyboard = []
    
    for template in templates:
        status = "✅" if template.is_active else "❌"
        row = [
            InlineKeyboardButton(
                f"{status} {template.name}", 
                callback_data=f"admin_template_view_{template.id}"
            ),
            InlineKeyboardButton(
                f"✏️", 
                callback_data=f"admin_template_edit_{template.id}"
            )
        ]
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("➕ Добавить шаблон", callback_data="admin_template_add")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_refresh")])
    
    return InlineKeyboardMarkup(keyboard)

def referral_keyboard(referral_link):
    """Клавиатура реферальной программы"""
    keyboard = [
        [InlineKeyboardButton("📤 Поделиться ссылкой", switch_inline_query=referral_link)],
        [InlineKeyboardButton("🔄 Обновить статистику", callback_data="ref_refresh")]
    ]
    return InlineKeyboardMarkup(keyboard)
