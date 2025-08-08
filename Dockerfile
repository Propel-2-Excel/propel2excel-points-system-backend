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

# Run migrations then start Gunicorn; PORT is provided by most cloud hosts
CMD sh -c "python manage.py migrate && gunicorn backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}"

