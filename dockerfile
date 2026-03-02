FROM python:3.11-slim

WORKDIR /app

# Копируем requirements.txt
COPY requirements.txt .

# Принудительно переустанавливаем numpy и matplotlib
RUN pip install --no-cache-dir --upgrade pip && \
    pip uninstall numpy matplotlib -y && \
    pip install --no-cache-dir numpy==1.24.3 matplotlib==3.7.0

# Устанавливаем остальные зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаем директории
RUN mkdir -p data exports backups

CMD ["python", "main.py"]FROM python:3.11-slim

WORKDIR /app

# Копируем requirements.txt
COPY requirements.txt .

# Принудительно переустанавливаем numpy и matplotlib
RUN pip install --no-cache-dir --upgrade pip && \
    pip uninstall numpy matplotlib -y && \
    pip install --no-cache-dir numpy==1.24.3 matplotlib==3.7.0

# Устанавливаем остальные зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Создаем директории
RUN mkdir -p data exports backups

CMD ["python", "main.py"]