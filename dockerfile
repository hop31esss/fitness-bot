FROM python:3.11-slim

WORKDIR /app

# Принудительно удаляем старые версии и ставим правильные
RUN pip uninstall numpy matplotlib -y || true && \
    pip install --no-cache-dir numpy==1.26.4 matplotlib==3.8.3

# Копируем и устанавливаем остальное
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]