import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from config import ADMIN_IDS
from keyboards import main_menu_keyboard, registered_menu_keyboard, admin_menu_keyboard
from database import get_user

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if user:
        if user["role"] == "store":
            await message.answer(f"✅ Добро пожаловать, {user['shop_name']}!", reply_markup=registered_menu_keyboard())
        elif user["role"] == "admin":
            await message.answer("✅ Вы вошли как администратор", reply_markup=admin_menu_keyboard())
    else:
        await message.answer("👋 Выберите действие:", reply_markup=main_menu_keyboard())
