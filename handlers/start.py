import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from keyboards import main_menu_keyboard

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    При вводе /start всегда выводим выбор: войти как админ или как магазин.
    """
    await message.answer("👋 Выберите действие:", reply_markup=main_menu_keyboard())
