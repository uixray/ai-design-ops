# ОБНОВЛЕНИЕ: Используем Python 3.11 для поддержки современного синтаксиса библиотек
FROM python:3.11-slim

WORKDIR /app

# Сначала копируем requirements для кэширования
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Запуск сервера
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]