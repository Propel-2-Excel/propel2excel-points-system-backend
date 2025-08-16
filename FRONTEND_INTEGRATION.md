# Frontend Integration Guide

This guide explains how to integrate the Django backend with the Next.js frontend at [P2E-Dashboard](https://github.com/oluwatomisinabiola/P2E-Dashboard).

## Backend Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the backend root:
```env
# Database
DATABASE_URL=your_supabase_database_url

# Django
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Discord Bot (optional)
DISCORD_TOKEN=your_discord_bot_token
BOT_SHARED_SECRET=your_bot_secret

# CORS Origins (add your frontend domains)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,https://your-frontend-domain.com
```

### 3. Run Backend
```bash
python manage.py migrate
python manage.py runserver 8000
```

The backend will run at `http://localhost:8000`

## API Endpoints Overview

### Authentication
- `POST /api/users/register/` - Register new user
- `POST /api/users/login/` - Login user  
- `GET /api/users/profile/` - Get current user profile

### Points System
- `POST /api/users/{id}/add_points/` - Add points for activity
- `GET /api/points-logs/` - View points history
- `GET /api/activities/` - List available activities

### Incentives & Rewards
- `GET /api/incentives/` - List available incentives
- `POST /api/redemptions/redeem/` - Redeem incentive
- `GET /api/redemptions/` - View redemption history

### Admin (Admin role required)
- `POST /api/redemptions/{id}/approve/` - Approve redemption
- `POST /api/redemptions/{id}/reject/` - Reject redemption

### Discord Integration
- `POST /api/link/start` - Start Discord account linking
- `GET /api/link/status` - Check link status

## Frontend Setup

### 1. Clone Frontend Repository
```bash
git clone https://github.com/oluwatomisinabiola/P2E-Dashboard.git
cd P2E-Dashboard
npm install
```

### 2. Environment Configuration
Create `.env.local` in the frontend root:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

### 3. API Service Layer
Create the following files in your Next.js project:

#### `src/services/api.ts`
```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';

class ApiService {
  private baseURL: string;
  private token: string | null = null;

  constructor() {
    this.baseURL = API_BASE_URL;
    // Get token from localStorage on client side
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('access_token');
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers as Record<string, string>,
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Authentication
  async register(userData: {
    username: string;
    email: string;
    password: string;
    role?: string;
    company?: string;
    university?: string;
  }) {
    return this.request('/users/register/', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async login(credentials: { username: string; password: string }) {
    const response = await this.request<{
      user: any;
      tokens: { access: string; refresh: string };
    }>('/users/login/', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    // Store tokens
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', response.tokens.access);
      localStorage.setItem('refresh_token', response.tokens.refresh);
      this.token = response.tokens.access;
    }

    return response;
  }

  async getProfile() {
    return this.request('/users/profile/');
  }

  // Points System
  async getActivities() {
    return this.request('/activities/');
  }

  async getPointsHistory() {
    return this.request('/points-logs/');
  }

  async addPoints(userId: number, data: { activity_type: string; details?: string }) {
    return this.request(`/users/${userId}/add_points/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Incentives
  async getIncentives() {
    return this.request('/incentives/');
  }

  async redeemIncentive(incentiveId: number) {
    return this.request('/redemptions/redeem/', {
      method: 'POST',
      body: JSON.stringify({ incentive_id: incentiveId }),
    });
  }

  async getRedemptions() {
    return this.request('/redemptions/');
  }

  // Discord Linking
  async startDiscordLink() {
    return this.request('/link/start', { method: 'POST' });
  }

  async checkLinkStatus() {
    return this.request('/link/status');
  }

  // Auth helpers
  logout() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      this.token = null;
    }
  }

  isAuthenticated(): boolean {
    return !!this.token;
  }
}

export const apiService = new ApiService();
```

#### `src/hooks/useAuth.ts`
```typescript
import { useState, useEffect, createContext, useContext } from 'react';
import { apiService } from '../services/api';

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  total_points: number;
  company?: string;
  university?: string;
  discord_id?: string;
}

interface AuthContextType {
  user: User | null;
  login: (credentials: { username: string; password: string }) => Promise<void>;
  register: (userData: any) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      try {
        if (apiService.isAuthenticated()) {
          const profile = await apiService.getProfile();
          setUser(profile);
        }
      } catch (error) {
        console.error('Auth initialization failed:', error);
        apiService.logout();
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (credentials: { username: string; password: string }) => {
    const response = await apiService.login(credentials);
    setUser(response.user);
  };

  const register = async (userData: any) => {
    const response = await apiService.register(userData);
    setUser(response.user);
  };

  const logout = () => {
    apiService.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
```

## Integration Steps

### 1. Backend CORS Configuration ✅
- Added `django-cors-headers` to requirements
- Configured CORS to allow Next.js frontend connections
- Added JWT token configuration

### 2. Frontend API Service Setup
- Create the API service layer (`src/services/api.ts`)
- Set up authentication hooks (`src/hooks/useAuth.ts`)
- Configure environment variables

### 3. Frontend Components Integration
Create components to interact with your points system:

#### Dashboard Component Example:
```typescript
// src/components/Dashboard.tsx
import { useEffect, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { apiService } from '../services/api';

export const Dashboard = () => {
  const { user } = useAuth();
  const [activities, setActivities] = useState([]);
  const [incentives, setIncentives] = useState([]);
  const [pointsHistory, setPointsHistory] = useState([]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [activitiesData, incentivesData, historyData] = await Promise.all([
          apiService.getActivities(),
          apiService.getIncentives(),
          apiService.getPointsHistory(),
        ]);
        
        setActivities(activitiesData);
        setIncentives(incentivesData);
        setPointsHistory(historyData);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      }
    };

    if (user) {
      loadData();
    }
  }, [user]);

  return (
    <div className="dashboard">
      <h1>Welcome, {user?.username}!</h1>
      <div className="points-display">
        <h2>Total Points: {user?.total_points}</h2>
      </div>
      
      {/* Activities, Incentives, History components */}
    </div>
  );
};
```

### 4. Update your Next.js app structure:
```
src/
├── components/
│   ├── Dashboard.tsx
│   ├── Auth/
│   │   ├── LoginForm.tsx
│   │   └── RegisterForm.tsx
│   ├── Points/
│   │   ├── PointsHistory.tsx
│   │   └── ActivityList.tsx
│   └── Incentives/
│       ├── IncentiveList.tsx
│       └── RedemptionHistory.tsx
├── hooks/
│   └── useAuth.ts
├── services/
│   └── api.ts
└── pages/
    ├── _app.tsx (wrap with AuthProvider)
    ├── dashboard.tsx
    ├── login.tsx
    └── register.tsx
```

## Testing the Integration

### 1. Start Backend
```bash
cd /path/to/propel2excel-points-system
python manage.py runserver 8000
```

### 2. Start Frontend  
```bash
cd /path/to/P2E-Dashboard
npm run dev
```

### 3. Test API Connection
Visit `http://localhost:8000/api/docs/` to explore the API using Swagger UI.

### 4. Frontend Testing
- Test user registration/login
- Verify JWT token storage and authentication
- Test points system integration
- Test incentive redemption flow

## Production Deployment Considerations

### Backend (Django)
- Set `DEBUG=False` in production
- Configure proper `ALLOWED_HOSTS`
- Use environment-specific CORS origins
- Set up proper database connection (Supabase)
- Configure static file serving

### Frontend (Next.js)
- Update `NEXT_PUBLIC_API_URL` to production backend URL
- Configure deployment on Vercel, Netlify, or similar
- Ensure environment variables are set in deployment platform

## Key Data Models

### User
```typescript
interface User {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'student' | 'company' | 'university';
  total_points: number;
  company?: string;
  university?: string;
  discord_id?: string;
  created_at: string;
  updated_at: string;
}
```

### Activity
```typescript
interface Activity {
  id: number;
  name: string;
  activity_type: string;
  points_value: number;
  description: string;
  is_active: boolean;
}
```

### Incentive
```typescript
interface Incentive {
  id: number;
  name: string;
  description: string;
  points_required: number;
  sponsor: string;
  status: 'available' | 'unlocked' | 'redeemed';
  is_active: boolean;
  is_unlocked?: boolean; // Added by serializer
}
```

### PointsLog
```typescript
interface PointsLog {
  id: number;
  user: number;
  activity: Activity;
  points_earned: number;
  details: string;
  timestamp: string;
}
```

### Redemption
```typescript
interface Redemption {
  id: number;
  user: number;
  incentive: Incentive;
  points_spent: number;
  status: 'pending' | 'approved' | 'rejected';
  admin_notes: string;
  redeemed_at: string;
  processed_at?: string;
}
```

## Next Steps

1. **Clone the frontend repository**
2. **Set up the API service layer** using the provided code
3. **Create authentication components** (login, register forms)
4. **Build dashboard components** to display points, activities, and incentives
5. **Test the full integration** locally
6. **Deploy both backend and frontend** to production

## Authentication Flow

1. User registers/logs in via frontend
2. Backend returns JWT access and refresh tokens
3. Frontend stores tokens in localStorage
4. Frontend includes `Authorization: Bearer <token>` header in API requests
5. Backend validates JWT on protected endpoints

## Error Handling

The API returns standard HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `500` - Internal Server Error

Make sure to handle these appropriately in your frontend error handling logic.

