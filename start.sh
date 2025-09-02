#!/bin/bash

# Django + Discord Bot Startup Script for Render
set -e

echo "🚀 Starting Propel2Excel services..."

# Run Django migrations
echo "📦 Running Django migrations..."
python manage.py migrate

# Start Discord bot in background
echo "🤖 Starting Discord bot..."
python bot.py &
BOT_PID=$!

# Start Django with gunicorn (this blocks and handles the port)
echo "🌐 Starting Django server..."
gunicorn backend.wsgi:application --bind 0.0.0.0:${PORT:-8000} &
DJANGO_PID=$!

# Function to clean up processes on exit
cleanup() {
    echo "🛑 Cleaning up..."
    kill $BOT_PID 2>/dev/null || true
    kill $DJANGO_PID 2>/dev/null || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Wait for Django process (main service)
wait $DJANGO_PID
