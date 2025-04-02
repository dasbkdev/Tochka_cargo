import math
import re
import aiohttp
from config import DEFAULT_CITY, DGIS_API_KEY

def format_address(address: str) -> str:
    return f"{DEFAULT_CITY}, {address}" if "," not in address else address

async def get_coordinates(address: str) -> tuple:
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
    if None in [lat1, lon1, lat2, lon2]:
        return None
    R = 6371  # Радиус Земли в км
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def validate_phone(phone: str) -> bool:
    pattern = (
        r'^(\+7\d{10}|'
        r'\+996\d{9}|'     
        r'\+998\d{9}|'    
        r'\+992\d{9}|'   
        r'\+993\d{9}|'
        r'\+994\d{9}|'
        r'\+995\d{9}|'
        r'\+374\d{8,9}|'
        r'\+375\d{9}|'
        r'\+380\d{9}|'
        r'\+373\d{8,9})$'
    )
    return bool(re.match(pattern, phone))

def validate_address(address: str) -> bool:
    pattern = r'^.+?\s+\d+.*$'
    return bool(re.match(pattern, address))
