import logging
from aiogram import Router, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaDocument
from database import get_all_users, get_all_orders
from keyboards import admin_menu_keyboard
from config import ADMIN_IDS

router = Router()

@router.callback_query(lambda c: c.data == "admin_shop_list")
async def admin_shop_list(callback: CallbackQuery):
    logging.info(f"admin_shop_list callback received from user: {callback.from_user.id}")
    users = get_all_users()
    if not users:
        text = "Нет зарегистрированных магазинов."
    else:
        lines = [
            f"ID: {user['user_id']}, Магазин: {user['shop_name']}, Телефон: {user['contact']}"
            for user in users
        ]
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=admin_menu_keyboard())
    await callback.answer()

# Остальные обработчики остаются без изменений
@router.callback_query(lambda c: c.data == "admin_login")
async def admin_login(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in ADMIN_IDS:
        await callback.message.edit_text("✅ Вы успешно вошли как администратор!", reply_markup=admin_menu_keyboard())
    else:
        await callback.message.edit_text("У вас нет прав администратора.")
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_order_list")
async def admin_order_list(callback: CallbackQuery):
    orders = get_all_orders()
    if not orders:
        await callback.message.edit_text("Нет заказов.", reply_markup=admin_menu_keyboard())
        await callback.answer()
        return
    user_id = callback.from_user.id
    admin_view_state = {"orders": orders, "index": 0}
    await show_order(callback, user_id, admin_view_state)

async def show_order(callback: CallbackQuery, user_id: int, state: dict):
    orders = state["orders"]
    index = state["index"]
    order = orders[index]
    text = (
        f"Заказ #{order['id']}\n"
        f"Дата: {order['order_date']}\n"
        f"Отправитель: {order['phone_sender']}\n"
        f"Получатель: {order['phone_receiver']}\n"
        f"Адрес отправки: {order['pickup_address']}\n"
        f"Адрес доставки: {order['delivery_address']}\n"
        f"Расстояние: {order['distance']:.2f} км\n"
        f"Стоимость: {order['total_cost']} сом\n"
        f"Описание: {order['description']}\n"
        f"Вес: {order['weight']}\n"
    )
    buttons = []
    if index > 0:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_order_prev"))
    if index < len(orders) - 1:
        buttons.append(InlineKeyboardButton(text="Далее ➡️", callback_data="admin_order_next"))
    buttons.append(InlineKeyboardButton(text="В меню", callback_data="admin_menu_back"))
    markup = InlineKeyboardMarkup(inline_keyboard=[buttons])
    if order.get("photo_file_id"):
        media_type = order.get("media_type", "photo")
        if media_type == "photo":
            media = InputMediaPhoto(media=order["photo_file_id"], caption=text)
        elif media_type == "document":
            media = InputMediaDocument(media=order["photo_file_id"], caption=text)
        else:
            media = None
        if media:
            try:
                await callback.message.edit_media(media=media, reply_markup=markup)
            except Exception as e:
                logging.exception("Ошибка редактирования медиа: %s", e)
                await callback.message.edit_text(text, reply_markup=markup)
        else:
            await callback.message.edit_text(text, reply_markup=markup)
    else:
        await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()

@router.callback_query(lambda c: c.data in ["admin_order_next", "admin_order_prev"])
async def admin_order_navigation(callback: CallbackQuery):
    # Пример обработки навигации по заказам (код не изменялся)
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_menu_back")
async def admin_menu_back(callback: CallbackQuery):
    await callback.message.edit_text("Админ меню:", reply_markup=admin_menu_keyboard())
    await callback.answer()
