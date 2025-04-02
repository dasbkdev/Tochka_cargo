import math
import logging
import asyncio
from aiogram import Router, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ContentType
from utils import format_address, get_coordinates, calculate_distance, validate_phone, validate_address
from keyboards import registered_menu_keyboard, order_confirm_keyboard, photo_prompt_keyboard
from database import add_order
from config import ADMIN_IDS

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

@router.message(lambda message: message.from_user.id in order_state and order_state[message.from_user.id]["step"] == "phone_sender")
async def process_phone_sender(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    if not validate_phone(text):
        await message.answer("Неверный формат номера. Попробуйте снова (пример: +996123456789):")
        return
    order_state[user_id]["phone_sender"] = text
    order_state[user_id]["step"] = "pickup_address"
    await message.answer(
        "Введите адрес отправки (например: Ленина 5). Город автоматически добавится (Бишкек):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back")]
        ])
    )

@router.message(lambda message: message.from_user.id in order_state and order_state[message.from_user.id]["step"] == "pickup_address")
async def process_pickup_address(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    if not validate_address(text):
        await message.answer("Неверный формат адреса. Введите в формате: Улица 5")
        return
    order_state[user_id]["pickup_address"] = format_address(text)
    order_state[user_id]["step"] = "phone_receiver"
    await message.answer(
        "Введите номер телефона получателя (например: +996987654321):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back")]
        ])
    )

@router.message(lambda message: message.from_user.id in order_state and order_state[message.from_user.id]["step"] == "phone_receiver")
async def process_phone_receiver(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    if not validate_phone(text):
        await message.answer("Неверный формат номера получателя. Попробуйте снова (пример: +996987654321):")
        return
    order_state[user_id]["phone_receiver"] = text
    order_state[user_id]["step"] = "delivery_address"
    await message.answer(
        "Введите адрес получения (например: Ленина 5). Город автоматически добавится (Бишкек):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back")]
        ])
    )

@router.message(lambda message: message.from_user.id in order_state and order_state[message.from_user.id]["step"] == "delivery_address")
async def process_delivery_address(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    if not validate_address(text):
        await message.answer("Неверный формат адреса. Введите в формате: Улица 5")
        return
    order_state[user_id]["delivery_address"] = format_address(text)
    lat1, lon1 = await get_coordinates(order_state[user_id]["pickup_address"])
    lat2, lon2 = await get_coordinates(order_state[user_id]["delivery_address"])
    if None in (lat1, lon1, lat2, lon2):
        await message.answer("Ошибка при определении координат. Проверьте адреса и введите их заново.")
        order_state[user_id]["step"] = "pickup_address"
        return
    distance = calculate_distance(lat1, lon1, lat2, lon2)
    total_cost = math.ceil(48 + (12 * distance) + 60)
    order_state[user_id]["distance"] = distance
    order_state[user_id]["total_cost"] = total_cost
    order_state[user_id]["step"] = "photo"
    await message.answer(
        "Отправьте фото товара или нажмите 'Пропустить':",
        reply_markup=photo_prompt_keyboard()
    )

@router.callback_query(lambda c: c.data == "skip_photo")
async def skip_photo(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in order_state:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    order_state[user_id]["photo_id"] = None
    order_state[user_id]["media_type"] = None
    order_state[user_id]["step"] = "description"
    await callback.message.edit_text(
        "Введите описание товара:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back")]
        ])
    )
    await callback.answer()

@router.message(lambda message: message.from_user.id in order_state and order_state[message.from_user.id]["step"] == "photo" and message.content_type in {ContentType.PHOTO, ContentType.DOCUMENT})
async def process_photo(message: Message):
    user_id = message.from_user.id
    if message.photo:
        photo = message.photo[-1]
        order_state[user_id]["photo_id"] = photo.file_id
        order_state[user_id]["media_type"] = "photo"
    elif message.document:
        order_state[user_id]["photo_id"] = message.document.file_id
        order_state[user_id]["media_type"] = "document"
    order_state[user_id]["step"] = "description"
    await message.answer(
        "Фото получено.\nВведите описание товара:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back")]
        ])
    )

@router.message(lambda message: message.from_user.id in order_state and order_state[message.from_user.id]["step"] == "description")
async def process_description(message: Message):
    user_id = message.from_user.id
    order_state[user_id]["description"] = message.text.strip()
    order_state[user_id]["step"] = "weight"
    await message.answer(
        "Введите вес товара (например: 2 кг):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Назад", callback_data="back")]
        ])
    )

@router.message(lambda message: message.from_user.id in order_state and order_state[message.from_user.id]["step"] == "weight")
async def process_weight(message: Message):
    user_id = message.from_user.id
    order_state[user_id]["weight"] = message.text.strip()
    order_state[user_id]["step"] = "confirm"
    summary = (
        f"📦 Проверьте данные заказа:\n"
        f"Отправитель: {order_state[user_id].get('phone_sender')}\n"
        f"Адрес отправки: {order_state[user_id].get('pickup_address')}\n"
        f"Получатель: {order_state[user_id].get('phone_receiver')}\n"
        f"Адрес получения: {order_state[user_id].get('delivery_address')}\n"
        f"Расстояние: {order_state[user_id].get('distance', 0):.2f} км\n"
        f"Стоимость: {order_state[user_id].get('total_cost', 0)} сом\n"
        f"Описание: {order_state[user_id].get('description')}\n"
        f"Вес: {order_state[user_id].get('weight')}\n\n"
        f"Если все верно, нажмите 'Все верно', иначе - 'Заполнить заново'."
    )
    await message.answer(summary, reply_markup=order_confirm_keyboard())

@router.callback_query(lambda c: c.data in ["order_confirm", "order_restart"])
async def order_confirmation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in order_state:
        await callback.answer("Заказ не найден", show_alert=True)
        return
    state = order_state[user_id]
    if callback.data == "order_confirm":
        try:
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
                state.get("description"),
                state.get("weight")
            )
        except Exception as e:
            logging.exception("Ошибка при добавлении заказа в БД")
            await callback.message.edit_text(
                "Произошла ошибка при оформлении заказа. Повторите позже или обратитесь к админу.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Связаться с диспетчером", callback_data="contact_dispatcher")]
                ])
            )
            return

        # Отправляем уведомление админам
        summary = (
            f"📦 Новый заказ от пользователя {user_id} (Order ID: {order_id}):\n"
            f"Отправитель: {state.get('phone_sender')}\n"
            f"Адрес отправки: {state.get('pickup_address')}\n"
            f"Получатель: {state.get('phone_receiver')}\n"
            f"Адрес получения: {state.get('delivery_address')}\n"
            f"Расстояние: {state.get('distance'):.2f} км\n"
            f"Стоимость: {state.get('total_cost')} сом\n"
            f"Описание: {state.get('description')}\n"
            f"Вес: {state.get('weight')}"
        )
        for admin_id in ADMIN_IDS:
            try:
                if state.get("photo_id"):
                    if state.get("media_type") == "photo":
                        await callback.bot.send_photo(chat_id=admin_id, photo=state["photo_id"], caption=summary)
                    elif state.get("media_type") == "document":
                        await callback.bot.send_document(chat_id=admin_id, document=state["photo_id"], caption=summary)
                    else:
                        await callback.bot.send_message(chat_id=admin_id, text=summary)
                else:
                    await callback.bot.send_message(chat_id=admin_id, text=summary)
            except Exception as e:
                logging.exception(f"Ошибка отправки сообщения админу {admin_id}: {e}")
        order_state.pop(user_id, None)
        await callback.message.edit_text("✅ Заказ принят!", reply_markup=registered_menu_keyboard())
    elif callback.data == "order_restart":
        order_state[user_id] = {"step": "phone_sender"}
        await callback.message.edit_text(
            "✏️ Заполните данные заново.\nВведите номер телефона отправителя (например: +996123456789):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back")]
            ])
        )
    await callback.answer()
