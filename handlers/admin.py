import logging
from aiogram import Router, types
from aiogram.filters import Command
from database import get_all_users, get_all_orders
from keyboards import admin_menu_keyboard
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query(lambda c: c.data == "admin_login")
async def admin_login(callback: CallbackQuery):
    user_id = callback.from_user.id
    # Проверяем права в обработчике /start уже, здесь просто переключаем меню
    await callback.message.edit_text("✅ Вы успешно вошли как администратор!", reply_markup=admin_menu_keyboard())
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_shop_list")
async def admin_shop_list(callback: CallbackQuery):
    users = get_all_users()
    if not users:
        text = "Нет зарегистрированных магазинов."
    else:
        lines = []
        for user in users:
            lines.append(f"ID: {user['user_id']}, Магазин: {user['shop_name']}, Телефон: {user['contact']}")
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=admin_menu_keyboard())
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_order_list")
async def admin_order_list(callback: CallbackQuery):
    orders = get_all_orders()
    if not orders:
        text = "Нет заказов."
    else:
        lines = []
        for idx, order in enumerate(orders, start=1):
            lines.append(
                f"#{idx} - {order['order_date']}:\n"
                f"Отправитель: {order['phone_sender']}, Получатель: {order['phone_receiver']}, Стоимость: {order['total_cost']} сом"
            )
        text = "\n\n".join(lines)
    await callback.message.edit_text(text, reply_markup=admin_menu_keyboard())
    await callback.answer()
