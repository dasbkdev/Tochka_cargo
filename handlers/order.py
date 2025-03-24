import math
import logging
from aiogram import Router, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from utils import format_address, get_coordinates, calculate_distance, validate_phone
from keyboards import registered_menu_keyboard, order_confirm_keyboard, photo_prompt_keyboard
from database import add_order
import asyncio

router = Router()

order_state = {}

@router.callback_query(lambda c: c.data == "order")
async def order_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    order_state[user_id] = {"step": "phone_sender"}
    await callback.message.edit_text(
        "🚀 Оформление заказа:\nВведите номер телефона отправителя (например: +996123456789):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back")]
        ])
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "skip_photo")
async def skip_photo(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = order_state.get(user_id)
    if state and state.get("step") == "media_and_description":
        state["photo_id"] = None
        state["media_type"] = None
        state["step"] = "confirm"
        summary = (
            f"📦 Проверьте данные заказа:\n"
            f"Отправитель: {state.get('phone_sender')}\n"
            f"Адрес отправки: {state.get('pickup_address')}\n"
            f"Получатель: {state.get('phone_receiver')}\n"
            f"Адрес получения: {state.get('delivery_address')}\n"
            f"Расстояние: {state.get('distance', 0):.2f} км\n"
            f"Стоимость: {state.get('total_cost', 0)} сом\n"
            f"Описание: {state.get('description', 'Нет')}\n"
            f"Вес: {state.get('weight', 'Не указан')}\n"
            f"Если все верно, нажмите 'Все верно'."
        )
        await callback.message.edit_text(summary, reply_markup=order_confirm_keyboard())
    await callback.answer()

@router.callback_query(lambda c: c.data in ["order_confirm", "order_restart"])
async def order_confirmation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = order_state.get(user_id)
    if not state:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    if callback.data == "order_confirm":
        order_id = add_order(
            user_id,
            state.get("phone_sender"),
            state.get("phone_receiver"),
            state.get("pickup_address"),
            state.get("delivery_address"),
            state.get("distance"),
            state.get("total_cost"),
            state.get("photo_id"),
            state.get("media_type"),
            state.get("description", ""),
            state.get("weight", "")
        )
        summary = (
            f"📦 Новый заказ от пользователя {user_id} (Order ID: {order_id}):\n"
            f"Отправитель: {state.get('phone_sender')}\n"
            f"Адрес отправки: {state.get('pickup_address')}\n"
            f"Получатель: {state.get('phone_receiver')}\n"
            f"Адрес получения: {state.get('delivery_address')}\n"
            f"Расстояние: {state.get('distance'):.2f} км\n"
            f"Стоимость: {state.get('total_cost')} сом\n"
            f"Описание: {state.get('description', 'Нет')}\n"
            f"Вес: {state.get('weight', 'Не указан')}"
        )
        for admin_id in ADMIN_IDS:
            if state.get("photo_id"):
                if state.get("media_type") == "photo":
                    await callback.bot.send_photo(
                        chat_id=admin_id, 
                        photo=state["photo_id"], 
                        caption=summary
                    )
                elif state.get("media_type") == "document":
                    await callback.bot.send_document(
                        chat_id=admin_id, 
                        document=state["photo_id"], 
                        caption=summary
                    )
                else:
                    await callback.bot.send_message(chat_id=admin_id, text=summary)
            else:
                await callback.bot.send_message(chat_id=admin_id, text=summary)
        order_state.pop(user_id, None)
        await callback.message.edit_text(
            f"✅ Заказ #{order_id} оформлен! В течение 2 минут с вами свяжется курьер.",
            reply_markup=registered_menu_keyboard()
        )
    elif callback.data == "order_restart":
        order_state[user_id] = {"step": "phone_sender"}
        await callback.message.edit_text(
            "✏️ Заполните данные заново.\nВведите номер телефона отправителя (например: +996123456789):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back")]
            ])
        )
    await callback.answer()

@router.message(lambda message: message.from_user.id in order_state)
async def process_order(message: Message):
    user_id = message.from_user.id
    state = order_state.get(user_id)
    text = message.text.strip() if message.text else ""
    
    if state["step"] == "phone_sender":
        if not validate_phone(text):
            await message.answer("Неверный формат номера. Попробуйте снова:")
            return
        state["phone_sender"] = text
        state["step"] = "pickup_address"
        await message.answer(
            "Введите адрес отправки (например: Чуй 120). Город автоматически добавится (Бишкек):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back")]
            ])
        )
    elif state["step"] == "pickup_address":
        state["pickup_address"] = format_address(text)
        state["step"] = "phone_receiver"
        await message.answer(
            "Введите номер телефона получателя (например: +996987654321):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back")]
            ])
        )
    elif state["step"] == "phone_receiver":
        if not validate_phone(text):
            await message.answer("Неверный формат номера получателя. Попробуйте снова:")
            return
        state["phone_receiver"] = text
        state["step"] = "delivery_address"
        await message.answer(
            "Введите адрес получения (например: Ленина 5). Город автоматически добавится (Бишкек):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back")]
            ])
        )
    elif state["step"] == "delivery_address":
        state["delivery_address"] = format_address(text)
        lat1, lon1 = await get_coordinates(state["pickup_address"])
        lat2, lon2 = await get_coordinates(state["delivery_address"])
        if None in (lat1, lon1, lat2, lon2):
            await message.answer("Ошибка при определении координат. Проверьте адреса и введите их заново.")
            state["step"] = "pickup_address"
            return
        distance = calculate_distance(lat1, lon1, lat2, lon2)
        total_cost = math.ceil(48 + (12 * distance) + 60)
        state["distance"] = distance
        state["total_cost"] = total_cost
        state["step"] = "media_and_description"
        await message.answer(
            "Отправьте вместе фото товара, напишите описание и укажите примерный вес (через перенос строки):",
            reply_markup=photo_prompt_keyboard()
        )
    elif state["step"] == "media_and_description":
        lines = text.splitlines()
        if len(lines) >= 2:
            state["description"] = lines[0]
            state["weight"] = lines[1]
        else:
            state["description"] = text
            state["weight"] = "Не указан"
        state["step"] = "confirm"
        summary = (
            f"📦 Проверьте данные заказа:\n"
            f"Отправитель: {state.get('phone_sender')}\n"
            f"Адрес отправки: {state.get('pickup_address')}\n"
            f"Получатель: {state.get('phone_receiver')}\n"
            f"Адрес получения: {state.get('delivery_address')}\n"
            f"Расстояние: {state.get('distance', 0):.2f} км\n"
            f"Стоимость: {state.get('total_cost', 0)} сом\n"
            f"Описание: {state.get('description', 'Нет')}\n"
            f"Вес: {state.get('weight', 'Не указан')}\n"
            f"Если все верно, нажмите 'Все верно'."
        )
        await message.answer(summary, reply_markup=order_confirm_keyboard())
