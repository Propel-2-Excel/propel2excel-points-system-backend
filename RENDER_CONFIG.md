# Render Deployment Configuration

## Backend (Django) on Render

### Environment Variables to Set in Render Dashboard:

```env
# Database - Use your Supabase connection string
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require

# Django Core Settings
SECRET_KEY=your-production-secret-key-here
DEBUG=False

# Render Hosting Configuration
# Add your Render service URL (e.g., https://your-backend.onrender.com)
ALLOWED_HOSTS=your-backend.onrender.com

# CORS Origins - Add your frontend URLs
# Example for Vercel deployment:
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app,https://your-frontend.netlify.app,http://localhost:3000

# Discord Bot (Optional)
DISCORD_TOKEN=your_discord_bot_token
BOT_SHARED_SECRET=your_bot_secret
```

### Render Service Configuration:

1. **Service Type**: Web Service
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT`
4. **Python Version**: 3.11+ (set in runtime.txt)

### Important Notes:

- ✅ Your current settings.py is already configured to read from environment variables
- ✅ CORS is now configurable via `CORS_ALLOWED_ORIGINS` environment variable
- ✅ Gunicorn is included in requirements.txt for production serving

## Frontend Configuration

### For Vercel Deployment:
```env
# Environment Variables in Vercel Dashboard:
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com/api
```

### For Netlify Deployment:
```env
# Environment Variables in Netlify Dashboard:
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com/api
```

### For Local Development:
```env
# .env.local in your Next.js project:
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api

# Or if testing with Render backend:
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com/api
```

## Deployment Steps

### 1. Deploy Backend to Render:
1. Connect your GitHub repo to Render
2. Set environment variables in Render dashboard
3. Deploy will automatically use the build/start commands from above

### 2. Deploy Frontend to Vercel/Netlify:
1. Connect your frontend repo
2. Set environment variables to point to your Render backend URL
3. Deploy

### 3. Update CORS Origins:
Once your frontend is deployed, add its URL to the `CORS_ALLOWED_ORIGINS` environment variable in Render.

## Testing Your Render Deployment

### Test Backend Health:
```bash
curl https://your-backend.onrender.com/api/activities/
```

### Test Authentication:
```bash
curl -X POST https://your-backend.onrender.com/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123",
    "role": "student"
  }'
```

## Common Render Issues & Solutions

### Issue: CORS Errors
**Solution**: Add your frontend domain to `CORS_ALLOWED_ORIGINS` environment variable

### Issue: Database Connection
**Solution**: Verify your Supabase DATABASE_URL includes `?sslmode=require`

### Issue: Static Files
**Solution**: Render automatically handles static files with the current configuration

### Issue: Environment Variables Not Loading
**Solution**: Verify environment variables are set in Render dashboard, not in .env file

