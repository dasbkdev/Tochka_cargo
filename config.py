import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DGIS_API_KEY = os.getenv("DGIS_API_KEY")
ADMIN_IDS = set(map(int, os.getenv("ADMIN_IDS").split(",")))
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Бишкек")
DISPATCHER_PHONE = os.getenv("DISPATCHER_PHONE")
BASE_TARIFF = float(os.getenv("BASE_TARIFF", "48"))
PRICE_PER_KM = float(os.getenv("PRICE_PER_KM", "12"))
DOOR_TO_DOOR = float(os.getenv("DOOR_TO_DOOR", "60"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "database.db")
