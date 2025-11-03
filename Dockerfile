# --- base image
FROM python:3.11-slim

# --- system basics
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# --- workdir
WORKDIR /app

# --- deps eerst cachen
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# --- code kopiëren
# verwacht je code onder ./app (met app/main.py)
COPY app /app/app

# --- poort door Render bepaald
EXPOSE 8000

# --- start (LET OP: ${PORT} van Render gebruiken)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
