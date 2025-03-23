import logging
from aiogram import Router, types
from keyboards import registered_menu_keyboard
from database import get_orders_by_user
from config import DISPATCHER_PHONE

router = Router()

@router.callback_query(lambda c: c.data == "order_history")
async def order_history(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    orders = get_orders_by_user(user_id)
    if orders:
        lines = []
        for idx, order in enumerate(orders, start=1):
            lines.append(f"Заказ #{idx}: {order['order_date']} - {order['total_cost']} сом")
        text = "\n".join(lines)
    else:
        text = "Заказов не найдено."
    await callback.message.edit_text(text, reply_markup=registered_menu_keyboard())
    await callback.answer()

@router.callback_query(lambda c: c.data == "delivery_info")
async def delivery_info(callback: types.CallbackQuery):
    text = (
        "Информация о доставке:\n"
        "- Доставка осуществляется в течение 30 минут после оформления заказа.\n"
        "- Курьер связывается с вами для уточнения деталей."
    )
    await callback.message.edit_text(text, reply_markup=registered_menu_keyboard())
    await callback.answer()

@router.callback_query(lambda c: c.data == "contact_dispatcher")
async def contact_dispatcher(callback: types.CallbackQuery):
    # Если требуется перенаправить на WhatsApp, можно отправить ссылку:
    wa_link = f"https://wa.me/{DISPATCHER_PHONE.lstrip('+')}"
    text = f"Свяжитесь с диспетчером через WhatsApp:\n{wa_link}"
    await callback.message.edit_text(text, reply_markup=registered_menu_keyboard())
    await callback.answer()

@router.callback_query(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    # Возвращаем в меню магазина (можно адаптировать для разных сценариев)
    await callback.message.edit_text("Меню:", reply_markup=registered_menu_keyboard())
    await callback.answer()
