# Используем официальный образ Python (можно выбрать версию, например, 3.9-slim)
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем исходный код бота в контейнер
COPY . .

# Определяем команду для запуска бота
CMD ["python", "bot.py"]
