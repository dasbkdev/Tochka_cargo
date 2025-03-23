import logging
import math
import re
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Токен бота и список администраторов
TOKEN = "7616633587:AAHj-sRw1DFoo3c4mgAJQ2trx6HcQ1Wf48E"
ADMIN_IDS = {8003292110, 984834133, 1952805890}

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
router = Router()
dp = Dispatcher()
dp.include_router(router)

# API ключ для 2ГИС
DGIS_API_KEY = "97d5f84b-e090-47fd-91c4-a381a29da62f"

# Тарифы
BASE_TARIFF = 48        # Базовый тариф (сом)
PRICE_PER_KM = 12       # Цена за 1 км (сом)
DOOR_TO_DOOR = 60       # Опция «От двери до двери» (сом)

# Константы
DEFAULT_CITY = "Бишкек"
DISPATCHER_PHONE = "+996501264803"

# Глобальные хранилища данных
user_data = {}      # ключ: user_id, значение: словарь с данными и состоянием (registration, registered, order, admin)
orders_history = [] # список подтверждённых заказов

# Inline-клавиатуры

main_inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔑 Войти как администратор", callback_data="admin_login")],
    [InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data="register")]
])

registered_menu_inline = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🚀 Оформить заказ", callback_data="order")],
    [InlineKeyboardButton(text="📜 История заказов", callback_data="order_history")],
    [InlineKeyboardButton(text="☎️ Связаться с диспетчером", callback_data="contact_dispatcher")],
    [InlineKeyboardButton(text="Назад", callback_data="back")]
])

admin_menu_inline = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Список зарегистрированных магазинов", callback_data="admin_shop_list")],
    [InlineKeyboardButton(text="Список заказов", callback_data="admin_order_list")],
    [InlineKeyboardButton(text="Назад", callback_data="back")]
])

order_confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Все верно", callback_data="order_confirm")],
    [InlineKeyboardButton(text="✏️ Заполнить заново", callback_data="order_restart")],
    [InlineKeyboardButton(text="Назад", callback_data="back")]
])

# Новая inline-клавиатура для запроса фото товара
photo_prompt_inline = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Пропустить", callback_data="skip_photo")],
    [InlineKeyboardButton(text="Назад", callback_data="back")]
])

def format_address(address: str) -> str:
    """Добавляет город Бишкек, если его нет в адресе."""
    return f"{DEFAULT_CITY}, {address}" if "," not in address else address

async def get_coordinates(address: str) -> tuple:
    """Получает координаты через API 2ГИС (для Кыргызстана, адрес с городом Бишкек)."""
    url = f"https://catalog.api.2gis.com/3.0/items?q={address}&key={DGIS_API_KEY}&fields=items.point"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            items = data.get("result", {}).get("items", [])
            for item in items:
                point = item.get("point")
                if point:
                    return point.get("lat"), point.get("lon")
    return None, None

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Вычисляет расстояние между двумя точками по формуле Хаверсина."""
    if None in [lat1, lon1, lat2, lon2]:
        return None
    R = 6371  # Радиус Земли в км
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def validate_phone(phone: str) -> bool:
    """Проверяет, что номер начинается с '+' и содержит от 9 до 15 цифр."""
    return bool(re.fullmatch(r"\+\d{9,15}", phone))

def show_registered_menu(user_id: int, text: str):
    """Отправляет сообщение с меню для зарегистрированного пользователя."""
    shop_name = user_data[user_id].get("store_name", "Магазин")
    return bot.send_message(user_id, f"✅ Добро пожаловать, <b>{shop_name}</b>!\n{text}", reply_markup=registered_menu_inline)

def show_admin_menu(user_id: int, text: str):
    """Отправляет сообщение с меню для администратора."""
    return bot.send_message(user_id, text, reply_markup=admin_menu_inline)

@router.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    # Если пользователь уже зарегистрирован, сразу показываем ему его меню
    if user_data.get(user_id, {}).get("state") == "registered":
        await message.answer(f"✅ Добро пожаловать, <b>{user_data[user_id]['store_name']}</b>!", reply_markup=registered_menu_inline)
    else:
        user_data[user_id] = {"state": "main"}
        await message.answer("👋 Добро пожаловать!\nВыберите действие:", reply_markup=main_inline_keyboard)

@router.callback_query()
async def process_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    user = user_data.get(user_id, {"state": "main"})
    
    # Обработка кнопки "Назад"
    if data == "back":
        if user.get("state") == "admin":
            try:
                await callback.message.edit_text("Администраторское меню:", reply_markup=admin_menu_inline)
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
        elif user.get("state") in ["registered", "order"]:
            try:
                await callback.message.edit_text("Меню:", reply_markup=registered_menu_inline)
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
        else:
            try:
                await callback.message.edit_text("Выберите действие:", reply_markup=main_inline_keyboard)
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
    
    elif data == "admin_login":
        if user_id in ADMIN_IDS:
            user["state"] = "admin"
            try:
                await callback.message.edit_text("✅ Вы успешно вошли как администратор!", reply_markup=admin_menu_inline)
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
        else:
            try:
                await callback.message.edit_text("❌ Доступ запрещен. Вы не являетесь администратором.", reply_markup=main_inline_keyboard)
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
    
    elif data == "register":
        user_data[user_id] = {"state": "registration", "reg_step": "store_name"}
        try:
            await callback.message.edit_text(
                "🛍️ <b>Введите название магазина</b> (например: «Магазин №1»)\n\nДля отмены нажмите «Назад».",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back")]
                ])
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
    
    elif data == "order":
        user["state"] = "order"
        user["order"] = {"step": "phone_sender"}
        try:
            await callback.message.edit_text(
                "🚀 <b>Оформление заказа:</b>\n\n📲 Введите номер телефона отправителя\n(Пример: +996123456789)\n\nНажмите «Назад», чтобы вернуться в меню.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back")]
                ])
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                    raise

    elif data == "order_history":
        if not orders_history:
            try:
                await callback.message.edit_text("📜 История заказов пока не доступна.", reply_markup=registered_menu_inline)
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise
        else:
            orders_text = "\n\n".join(orders_history)
            try:
                await callback.message.edit_text(f"📜 История заказов:\n\n{orders_text}", reply_markup=registered_menu_inline)
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise

    elif data == "contact_dispatcher":
        try:
            await callback.message.edit_text(f"☎️ Свяжитесь с диспетчером: {DISPATCHER_PHONE}", reply_markup=registered_menu_inline)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

    elif data == "admin_shop_list":
        # Изменил фильтрацию: выводим всех, у кого есть store_name, независимо от состояния
        shops = [f"{uid}: {info.get('store_name', 'Без названия')}" 
                 for uid, info in user_data.items() if "store_name" in info]
        text = "Нет зарегистрированных магазинов." if not shops else "Список зарегистрированных магазинов:\n" + "\n".join(shops)
        try:
            await callback.message.edit_text(text, reply_markup=admin_menu_inline)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

    elif data == "admin_order_list":
        text = "Нет заказов." if not orders_history else "Список заказов:\n" + "\n\n".join(orders_history)
        try:
            await callback.message.edit_text(text, reply_markup=admin_menu_inline)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

    elif data == "skip_photo" and user.get("state") == "order":
        # Пользователь решил пропустить загрузку фото товара
        order = user.get("order")
        order["photo_id"] = None
        order["media_type"] = None
        order["step"] = "confirm"
        summary = (
            f"📦 <b>Проверьте данные заказа:</b>\n"
            f"------------------------------\n"
            f"📲 Отправитель: {order['phone_sender']}\n"
            f"📍 Адрес отправки: {order['pickup_address']}\n"
            f"☎️ Получатель: {order['phone_receiver']}\n"
            f"🚚 Адрес получения: {order['delivery_address']}\n"
            f"📏 Расстояние: {order['distance']:.2f} км\n"
            f"💰 Стоимость доставки: {order['total_cost']} сом\n"
            f"------------------------------\n"
            f"Если все верно, нажмите кнопку ниже."
        )
        try:
            await callback.message.edit_text(summary, reply_markup=order_confirm_keyboard)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise

    elif data == "order_confirm" and user.get("state") == "order":
        order = user.get("order")
        summary = (
            f"📦 Новый заказ от пользователя {user_id}:\n"
            f"📲 Отправитель: {order['phone_sender']}\n"
            f"📍 Адрес отправки: {order['pickup_address']}\n"
            f"☎️ Получатель: {order['phone_receiver']}\n"
            f"🚚 Адрес получения: {order['delivery_address']}\n"
            f"📏 Расстояние: {order['distance']:.2f} км\n"
            f"💰 Стоимость доставки: {order['total_cost']} сом"
        )
        orders_history.append(summary)
        for admin_id in ADMIN_IDS:
            # Отправляем фото или документ в зависимости от типа
            if order.get("photo_id"):
                if order.get("media_type") == "photo":
                    await bot.send_photo(chat_id=admin_id, photo=order["photo_id"], caption=summary)
                elif order.get("media_type") == "document":
                    await bot.send_document(chat_id=admin_id, document=order["photo_id"], caption=summary)
                else:
                    await bot.send_message(chat_id=admin_id, text=summary)
            else:
                await bot.send_message(chat_id=admin_id, text=summary)
        try:
            await callback.message.edit_text("✅ Заказ оформлен! В течение 2 минут с вами свяжется курьер.", reply_markup=registered_menu_inline)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
        user["state"] = "registered"
        user.pop("order", None)
    
    elif data == "order_restart" and user.get("state") == "order":
        user["order"] = {"step": "phone_sender"}
        try:
            await callback.message.edit_text(
                "✏️ Заполните данные заново.\n\n📲 Введите номер телефона отправителя (Пример: +996123456789)\n\nНажмите «Назад», чтобы вернуться в меню.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back")]
                ])
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise
    
    await callback.answer()

@router.message()
async def handle_messages(message: Message):
    user_id = message.from_user.id
    # Если сообщение не содержит ни текста, ни медиа, пропускаем его
    if not message.text and not (message.photo or message.document):
        return
    # Если сообщение содержит текст, получаем его; иначе text будет None
    text = message.text.strip() if message.text else None
    user = user_data.get(user_id)
    
    if not user:
        await message.answer("Пожалуйста, нажмите /start для начала.", reply_markup=main_inline_keyboard)
        return

    # Если пользователь оформляет заказ и находится на шаге загрузки фото,
    # обрабатываем медиа-сообщение
    if user.get("state") == "order":
        order = user.get("order", {})
        current_step = order.get("step")
        if current_step == "photo":
            if message.photo or message.document:
                if message.photo:
                    photo_id = message.photo[-1].file_id
                    order["media_type"] = "photo"
                else:
                    photo_id = message.document.file_id
                    order["media_type"] = "document"
                order["photo_id"] = photo_id
                order["step"] = "confirm"
                summary = (
                    f"📦 <b>Проверьте данные заказа:</b>\n"
                    f"------------------------------\n"
                    f"📲 Отправитель: {order['phone_sender']}\n"
                    f"📍 Адрес отправки: {order['pickup_address']}\n"
                    f"☎️ Получатель: {order['phone_receiver']}\n"
                    f"🚚 Адрес получения: {order['delivery_address']}\n"
                    f"📏 Расстояние: {order['distance']:.2f} км\n"
                    f"💰 Стоимость доставки: {order['total_cost']} сом\n"
                    f"------------------------------\n"
                    f"Если все верно, нажмите кнопку ниже."
                )
                await message.answer(summary, reply_markup=order_confirm_keyboard)
            else:
                await message.answer(
                    "❌ Пожалуйста, отправьте фото товара или нажмите «Пропустить».",
                    reply_markup=photo_prompt_inline
                )
            return

    if text is None:
        return

    # Далее обрабатываем текстовые сообщения
    # Регистрация магазина
    if user.get("state") == "registration":
        reg_step = user.get("reg_step")
        if reg_step == "store_name":
            user["store_name"] = text
            user["reg_step"] = "contact"
            await message.answer(
                "📞 <b>Введите номер телефона или WhatsApp</b> (Пример: +996123456789)\n\nНажмите «Назад», чтобы отменить.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back")]
                ])
            )
        elif reg_step == "contact":
            if not validate_phone(text):
                await message.answer(
                    "❌ Неверный формат номера. Пример: +996123456789\nПопробуйте ещё раз:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Назад", callback_data="back")]
                    ])
                )
                return
            user["contact"] = text
            user["state"] = "registered"
            await message.answer(f"✅ Добро пожаловать, <b>{user['store_name']}</b>!\nВыберите действие:", reply_markup=registered_menu_inline)
        else:
            await message.answer("Ошибка в процессе регистрации. Попробуйте /start", reply_markup=main_inline_keyboard)
    
    # Оформление заказа
    elif user.get("state") == "order":
        order = user.get("order", {})
        current_step = order.get("step")
        
        if current_step == "phone_sender":
            if not validate_phone(text):
                await message.answer(
                    "❌ Неверный формат номера отправителя. Пример: +996123456789\nПопробуйте ввести снова:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Назад", callback_data="back")]
                    ])
                )
                return
            order["phone_sender"] = text
            order["step"] = "pickup_address"
            await message.answer(
                "📍 <b>Введите адрес отправки</b>\n(Пример: Чуй 120)\n*Город автоматически добавится (Бишкек)*\n\nНажмите «Назад» для возврата.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back")]
                ])
            )
        
        elif current_step == "pickup_address":
            order["pickup_address"] = format_address(text)
            order["step"] = "phone_receiver"
            await message.answer(
                "☎️ <b>Введите номер телефона получателя</b>\n(Пример: +996987654321)\n\nНажмите «Назад» для возврата.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back")]
                ])
            )
        
        elif current_step == "phone_receiver":
            if not validate_phone(text):
                await message.answer(
                    "❌ Неверный формат номера получателя. Пример: +996987654321\nПопробуйте ввести снова:",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Назад", callback_data="back")]
                    ])
                )
                return
            order["phone_receiver"] = text
            order["step"] = "delivery_address"
            await message.answer(
                "🚚 <b>Введите адрес получения</b>\n(Пример: Ленина 5)\n*Город автоматически добавится (Бишкек)*\n\nНажмите «Назад» для возврата.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back")]
                ])
            )
        
        elif current_step == "delivery_address":
            order["delivery_address"] = format_address(text)
            # Получаем координаты для расчёта расстояния
            lat1, lon1 = await get_coordinates(order["pickup_address"])
            lat2, lon2 = await get_coordinates(order["delivery_address"])
            if None in (lat1, lon1, lat2, lon2):
                await message.answer(
                    "❌ Ошибка при определении координат. Проверьте адреса и введите их заново.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Назад", callback_data="back")]
                    ])
                )
                order["step"] = "pickup_address"
                return
            distance = calculate_distance(lat1, lon1, lat2, lon2)
            total_cost = math.ceil(BASE_TARIFF + (PRICE_PER_KM * distance) + DOOR_TO_DOOR)
            order["distance"] = distance
            order["total_cost"] = total_cost
            # Переходим к шагу загрузки фото товара
            order["step"] = "photo"
            await message.answer(
                "📸 Отправьте, пожалуйста, фото товара или нажмите «Пропустить».",
                reply_markup=photo_prompt_inline
            )
        
        elif current_step == "photo":
            # Если пользователь отправил фото или документ, обработка выполняется в блоке выше.
            await message.answer(
                "❌ Пожалуйста, отправьте фото товара или нажмите «Пропустить».",
                reply_markup=photo_prompt_inline
            )
        
        else:
            await message.answer("Ошибка в оформлении заказа. Попробуйте /start", reply_markup=registered_menu_inline)
    
    elif user.get("state") == "registered":
        await message.answer("Пожалуйста, используйте кнопки для выбора действия.", reply_markup=registered_menu_inline)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
