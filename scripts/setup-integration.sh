#!/bin/bash

# Frontend-Backend Integration Setup Script
# This script helps set up the integration between Django backend and Next.js frontend

echo "🚀 Setting up Frontend-Backend Integration..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    print_error "Please run this script from the Django project root directory"
    exit 1
fi

echo "📦 Installing backend dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    print_status "Backend dependencies installed"
else
    print_error "Failed to install backend dependencies"
    exit 1
fi

echo ""
echo "🔧 Setting up environment files..."

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    print_status "Created .env file from template"
    print_warning "Please edit .env file with your actual configuration values"
else
    print_warning ".env file already exists"
fi

echo ""
echo "🗄️ Setting up database..."
python manage.py migrate

if [ $? -eq 0 ]; then
    print_status "Database migrations completed"
else
    print_error "Database migration failed"
    exit 1
fi

echo ""
echo "🎯 Testing backend setup..."
python manage.py check

if [ $? -eq 0 ]; then
    print_status "Django backend configuration is valid"
else
    print_error "Django backend configuration has issues"
    exit 1
fi

echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your actual configuration"
echo "2. Start backend: python manage.py runserver 8000"
echo "3. Clone frontend: git clone https://github.com/oluwatomisinabiola/P2E-Dashboard.git"
echo "4. Copy frontend-api-service.ts to frontend/src/services/api.ts"
echo "5. Create frontend/.env.local with API URLs"
echo "6. Start frontend: cd P2E-Dashboard && npm install && npm run dev"
echo ""
echo "📚 Read FRONTEND_INTEGRATION.md for detailed instructions"
echo "🌐 API Documentation: http://localhost:8000/api/docs/"
echo ""
print_status "Backend setup complete!"

