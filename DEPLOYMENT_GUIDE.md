# Deployment Guide

## Local Development Setup

### Backend (Django) Setup
1. **Install Python dependencies:**
   ```bash
   cd propel2excel-points-system
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

3. **Run migrations and start server:**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser  # Optional: for admin access
   python manage.py runserver 8000
   ```

4. **Test API:**
   Visit `http://localhost:8000/api/docs/` for Swagger documentation

### Frontend (Next.js) Setup
1. **Clone and setup frontend:**
   ```bash
   git clone https://github.com/oluwatomisinabiola/P2E-Dashboard.git
   cd P2E-Dashboard
   npm install
   ```

2. **Configure environment:**
   ```bash
   # Create .env.local file with:
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
   ```

3. **Add API service:**
   - Copy `frontend-api-service.ts` content to `src/services/api.ts`
   - Create authentication hooks and components as documented

4. **Start development server:**
   ```bash
   npm run dev
   ```

## Production Deployment

### Backend Deployment (Railway/Heroku/DigitalOcean)

1. **Environment Variables:**
   ```env
   DATABASE_URL=your_production_database_url
   SECRET_KEY=your_production_secret_key
   DEBUG=False
   ALLOWED_HOSTS=your-backend-domain.com
   CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
   ```

2. **Database Migration:**
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

3. **Gunicorn Configuration:**
   ```bash
   gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
   ```

### Frontend Deployment (Vercel/Netlify)

1. **Environment Variables:**
   ```env
   NEXT_PUBLIC_API_URL=https://your-backend-domain.com
   NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com/api
   ```

2. **Build and Deploy:**
   ```bash
   npm run build
   npm start
   ```

## Testing Integration

### 1. Backend Health Check
```bash
curl http://localhost:8000/api/activities/
```

### 2. Frontend API Connection
Test user registration:
```bash
curl -X POST http://localhost:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com", 
    "password": "testpass123",
    "role": "student"
  }'
```

### 3. JWT Authentication
After login, test authenticated endpoint:
```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8000/api/users/profile/
```

## Common Issues & Solutions

### CORS Errors
- Ensure `django-cors-headers` is installed
- Verify frontend URL is in `CORS_ALLOWED_ORIGINS`
- Check that CORS middleware is properly configured

### Authentication Issues
- Verify JWT tokens are being stored in localStorage
- Check token expiration (default: 60 minutes)
- Implement token refresh logic

### Database Connection Issues
- Verify DATABASE_URL format for Supabase
- Ensure SSL mode is configured for production
- Check database credentials and network access

## Monitoring & Maintenance

### Backend Monitoring
- Monitor API response times at `/api/docs/`
- Track database performance
- Monitor Discord bot connection status

### Frontend Monitoring
- Monitor API call failures
- Track user authentication flows
- Monitor frontend performance metrics

