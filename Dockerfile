# Multi-arch, small base
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install deps
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app

EXPOSE 8000

# Make startup script executable and use it
RUN chmod +x start.sh

# Run both Django backend AND Discord bot using startup script
CMD ["./start.sh"]

