# Imagen oficial de Playwright: trae Python, Chromium y las librerías de sistema.
# La versión debe coincidir con playwright==1.57.0 de requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.57.0-noble

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Primero solo requirements, para aprovechar la caché de capas de Docker.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# --reload recarga la API al guardar cambios (en dev). En producción no se usa.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
