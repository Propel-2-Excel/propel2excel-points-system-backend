# Render Deployment Checklist

## ✅ Current Status - Your Code is Render-Ready!

Your Django backend is already properly configured for Render deployment. Here's what's correctly set up:

### ✅ Backend Configuration (Already Correct):
- **Environment Variables**: Settings read from environment using `django-environ`
- **ALLOWED_HOSTS**: Configurable via `ALLOWED_HOSTS` env var
- **CORS Origins**: Now configurable via `CORS_ALLOWED_ORIGINS` env var
- **Database**: Uses `DATABASE_URL` for Supabase connection
- **Gunicorn**: Already in requirements.txt for production serving
- **Static Files**: Configured for production

## 🚀 Render Environment Variables to Set:

When deploying on Render, set these in your Render service dashboard:

```env
# Required
DATABASE_URL=your_supabase_connection_string
SECRET_KEY=your_production_secret_key
DEBUG=False
ALLOWED_HOSTS=your-backend.onrender.com
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000

# Optional (Discord)
DISCORD_TOKEN=your_discord_bot_token
BOT_SHARED_SECRET=your_bot_secret
```

## 📝 Render Service Settings:

### Build Command:
```bash
pip install -r requirements.txt
```

### Start Command:
```bash
gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
```

### Auto-Deploy:
- ✅ Enable auto-deploy from your git branch

## 🔗 Frontend Integration Options:

### Option 1: Development (Frontend Local, Backend on Render)
```env
# In your Next.js .env.local:
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com/api
```

### Option 2: Full Production (Both Deployed)
```env
# Frontend env vars (Vercel/Netlify):
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com/api

# Backend env vars (Render):
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
```

## 🧪 Testing After Deployment:

### 1. Test Backend Health:
```bash
curl https://your-backend.onrender.com/api/activities/
```

### 2. Test API Documentation:
Visit: `https://your-backend.onrender.com/api/docs/`

### 3. Test CORS:
```bash
curl -H "Origin: https://your-frontend.vercel.app" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: authorization,content-type" \
     -X OPTIONS \
     https://your-backend.onrender.com/api/users/profile/
```

## ⚡ Quick Deployment Steps:

1. **Deploy Backend to Render:**
   - Connect your GitHub repo
   - Set environment variables above
   - Deploy will use existing Dockerfile/requirements.txt

2. **Update Frontend Environment:**
   - Point `NEXT_PUBLIC_API_URL` to your Render backend URL
   - Deploy frontend to Vercel/Netlify

3. **Update Backend CORS:**
   - Add your frontend URL to `CORS_ALLOWED_ORIGINS` in Render

That's it! Your integration is ready for Render! 🎉

