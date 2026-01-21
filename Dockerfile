FROM python:3.13-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    iputils-ping \
    mariadb-client \
    && rm -rf /var/lib/lists/*

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

# Copy postmant script
# COPY postmant /usr/local/bin/postmant
# RUN chmod +x /usr/local/bin/postmant

# Copy api key service script
# COPY scripts/encode_api_key.py /usr/local/bin/encode_api_key.py
# RUN chmod +x /usr/local/bin/encode_api_key.py

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application with postmant
CMD ["/usr/local/bin/postmant", "python", "-m", "uvicorn", "app_fast_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
