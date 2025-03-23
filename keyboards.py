from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Войти как администратор", callback_data="admin_login")],
        [InlineKeyboardButton(text="📝 Войти как магазин", callback_data="login_store")]
    ])

def registered_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Оформить заказ", callback_data="order")],
        [InlineKeyboardButton(text="📜 История заказов", callback_data="order_history")],
        [InlineKeyboardButton(text="💬 Как работает доставка", callback_data="delivery_info")],
        [InlineKeyboardButton(text="☎️ Связаться с диспетчером", callback_data="contact_dispatcher")]
    ])

def admin_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Список зарегистрированных магазинов", callback_data="admin_shop_list")],
        [InlineKeyboardButton(text="Список заказов", callback_data="admin_order_list")]
    ])

def order_confirm_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Все верно", callback_data="order_confirm")],
        [InlineKeyboardButton(text="✏️ Заполнить заново", callback_data="order_restart")]
    ])

def photo_prompt_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Пропустить", callback_data="skip_photo")]
    ])
