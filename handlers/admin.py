import logging
from aiogram import Router, types
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
    InputMediaDocument
)
from database import get_all_users, get_all_orders
from keyboards import admin_menu_keyboard
from config import ADMIN_IDS
from aiogram.exceptions import TelegramBadRequest

router = Router()

# Глобальное состояние для пагинации заказов админа
admin_order_state = {}
# Глобальное состояние для пагинации зарегистрированных магазинов
admin_shop_state = {}

@router.callback_query(lambda c: c.data == "admin_login")
async def admin_login(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in ADMIN_IDS:
        await callback.message.edit_text("✅ Вы успешно вошли как администратор!", reply_markup=admin_menu_keyboard())
    else:
        await callback.message.edit_text("У вас нет прав администратора.")
    await callback.answer()

#########################
# Список зарегистрированных магазинов
#########################
@router.callback_query(lambda c: c.data == "admin_shop_list")
async def admin_shop_list(callback: CallbackQuery):
    logging.info(f"admin_shop_list callback received from user: {callback.from_user.id}")
    users = get_all_users()
    if not users:
        await callback.message.edit_text("Нет зарегистрированных магазинов.", reply_markup=admin_menu_keyboard())
        await callback.answer()
        return
    user_id = callback.from_user.id
    # Сохраняем состояние для данного администратора
    admin_shop_state[user_id] = {"shops": users, "index": 0}
    await show_shop(callback, user_id)

async def show_shop(callback: CallbackQuery, user_id: int):
    state = admin_shop_state.get(user_id)
    if not state:
        await callback.answer("Состояние магазинов не найдено.", show_alert=True)
        return
    shops = state["shops"]
    index = state["index"]
    shop = dict(shops[index])
    text = (
        f"Магазин: {shop.get('shop_name')}\n"
        f"ID пользователя: {shop.get('user_id')}\n"
        f"Контакт: {shop.get('contact')}\n"
        f"Дата регистрации: {shop.get('registration_date')}"
    )
    buttons = []
    if index > 0:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_shop_prev"))
    if index < len(shops) - 1:
        buttons.append(InlineKeyboardButton(text="Далее ➡️", callback_data="admin_shop_next"))
    buttons.append(InlineKeyboardButton(text="В меню", callback_data="admin_menu_back"))
    markup = InlineKeyboardMarkup(inline_keyboard=[buttons])
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        logging.exception("Ошибка редактирования текста магазина: %s", e)
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()

@router.callback_query(lambda c: c.data in ["admin_shop_next", "admin_shop_prev"])
async def admin_shop_navigation(callback: CallbackQuery):
    user_id = callback.from_user.id
    state = admin_shop_state.get(user_id)
    if not state:
        await callback.answer("Нет магазинов для отображения.", show_alert=True)
        return
    if callback.data == "admin_shop_next":
        state["index"] += 1
    elif callback.data == "admin_shop_prev":
        state["index"] -= 1
    await show_shop(callback, user_id)

#########################
# Список заказов
#########################
@router.callback_query(lambda c: c.data == "admin_order_list")
async def admin_order_list(callback: CallbackQuery):
    orders = get_all_orders()
    if not orders:
        await callback.message.edit_text("Нет заказов.", reply_markup=admin_menu_keyboard())
        await callback.answer()
        return
    user_id = callback.from_user.id
    admin_order_state[user_id] = {"orders": orders, "index": 0}
    await show_order(callback, user_id)

async def show_order(callback: CallbackQuery, user_id: int):
    state = admin_order_state.get(user_id)
    if not state:
        await callback.answer("Состояние заказов не найдено.", show_alert=True)
        return
    orders = state["orders"]
    index = state["index"]
    order = dict(orders[index])
    text = (
        f"Заказ #{order.get('id')}\n"
        f"Дата: {order.get('order_date')}\n"
        f"Отправитель: {order.get('phone_sender')}\n"
        f"Получатель: {order.get('phone_receiver')}\n"
        f"Адрес отправки: {order.get('pickup_address')}\n"
        f"Адрес доставки: {order.get('delivery_address')}\n"
        f"Расстояние: {order.get('distance', 0):.2f} км\n"
        f"Стоимость: {order.get('total_cost')} сом\n"
        f"Описание: {order.get('description')}\n"
        f"Вес: {order.get('weight')}\n"
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
            except TelegramBadRequest as e:
                if "there is no text" in str(e):
                    try:
                        await callback.message.edit_caption(caption=text, reply_markup=markup)
                    except TelegramBadRequest as e2:
                        logging.exception("Ошибка редактирования подписи: %s", e2)
                        await callback.message.answer(text, reply_markup=markup)
                else:
                    logging.exception("Ошибка редактирования медиа: %s", e)
                    await callback.message.answer(text, reply_markup=markup)
        else:
            await callback.message.edit_text(text, reply_markup=markup)
    else:
        await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()

@router.callback_query(lambda c: c.data in ["admin_order_next", "admin_order_prev"])
async def admin_order_navigation(callback: CallbackQuery):
    user_id = callback.from_user.id
    state = admin_order_state.get(user_id)
    if not state:
        await callback.answer("Нет заказов для отображения.", show_alert=True)
        return
    if callback.data == "admin_order_next":
        state["index"] += 1
    elif callback.data == "admin_order_prev":
        state["index"] -= 1
    await show_order(callback, user_id)

@router.callback_query(lambda c: c.data == "admin_menu_back")
async def admin_menu_back(callback: CallbackQuery):
    await callback.message.edit_text("Админ меню:", reply_markup=admin_menu_keyboard())
    await callback.answer()
