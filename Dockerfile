FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    iputils-ping \
    mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Instalar Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copiar archivos de dependencias
COPY pyproject.toml poetry.lock ./

# Instalar dependencias sin crear virtualenv
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copiar el resto del código
COPY . .

RUN mkdir -p logs

EXPOSE 8000

# Cambiar el CMD para usar la estructura correcta
CMD ["python", "-m", "uvicorn", "app_fast_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
