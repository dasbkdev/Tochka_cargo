import logging
from aiogram import Router, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from utils import validate_phone
from database import add_user
from keyboards import registered_menu_keyboard

router = Router()

# Временное хранение состояния регистрации
registration_state = {}

@router.callback_query(lambda c: c.data == "login_store")
async def login_store(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    registration_state[user_id] = {"step": "shop_name"}
    await callback.message.edit_text("Введите название магазина или имя:")
    await callback.answer()

@router.message(lambda message: message.from_user.id in registration_state)
async def process_registration(message: Message):
    user_id = message.from_user.id
    state = registration_state.get(user_id)
    if not state:
        return
    if state["step"] == "shop_name":
        state["shop_name"] = message.text.strip()
        state["step"] = "contact"
        await message.answer("Введите номер телефона или WhatsApp (например: +996123456789):")
    elif state["step"] == "contact":
        if not validate_phone(message.text.strip()):
            await message.answer("Неверный формат номера. Попробуйте ещё раз:")
            return
        state["contact"] = message.text.strip()
        add_user(user_id, state["shop_name"], state["contact"], role="store")
        registration_state.pop(user_id, None)
        await message.answer(
            f"✅ Добро пожаловать, {state['shop_name']}!\nКак работает доставка: [информация]\n\nВыберите действие:",
            reply_markup=registered_menu_keyboard()
        )
