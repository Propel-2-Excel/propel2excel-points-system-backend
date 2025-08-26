# Frontend Backend Requirements

## Overview

This document outlines the backend API endpoints and data structures needed to support the current frontend implementation of the Propel2Excel Points System. The frontend has been updated to use real data where possible, but some features require additional backend support.

---

## 🟢 CURRENTLY WORKING (No Backend Changes Needed)

### ✅ Authentication & User Management
- `POST /api/users/login/` - User login ✅
- `POST /api/users/register/` - User registration ✅
- `GET /api/users/profile/` - Get user profile with total points ✅

### ✅ Points System
- `GET /api/points-logs/` - Get user's points history ✅
- `POST /api/users/{id}/add_points/` - Add points for activities ✅

### ✅ Activities & Incentives
- `GET /api/activities/` - List available activities ✅
- `GET /api/incentives/` - List available rewards ✅

---

## 🟡 PARTIALLY WORKING (Frontend Adapted)

### Recent Activity Table ✅
**Status:** Working with real data
- Uses existing `GET /api/points-logs/` endpoint
- Frontend processes and displays recent activities

### Points by Category Radar Chart ✅
**Status:** Working with real data
- Uses existing `GET /api/points-logs/` endpoint
- Frontend groups points by `activity.category` field

### Statistics Cards ✅
**Status:** Working with real data (no trends)
- Total Points: From user session ✅
- Activities Completed: Count from points history ✅
- Available Rewards: Count from incentives API ✅
- **Note:** Trend indicators removed (were showing fake data)

---

## 🔴 MISSING FEATURES (Backend Implementation Required)

### 1. 📈 **Dashboard Statistics with Trends**

**Current Issue:** No trend calculations available
**Frontend Needs:** Period-over-period comparison data

#### Required Endpoint:
```http
GET /api/dashboard/stats/?period={period}
```

**Parameters:**
- `period`: `30days`, `7days`, `90days` (optional, defaults to 30days)

**Expected Response:**
```json
{
  "current_period": {
    "total_points": 150,
    "activities_completed": 12,
    "points_earned": 50,
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "previous_period": {
    "total_points": 100,
    "activities_completed": 8,
    "points_earned": 30,
    "start_date": "2023-12-01",
    "end_date": "2023-12-31"
  },
  "trends": {
    "total_points": {
      "change": 50,
      "percentage": 50.0,
      "direction": "up"
    },
    "activities_completed": {
      "change": 4,
      "percentage": 50.0,
      "direction": "up"
    },
    "points_earned": {
      "change": 20,
      "percentage": 66.67,
      "direction": "up"
    }
  }
}
```

**Backend Implementation Notes:**
- Compare current period vs same-length previous period
- Calculate percentage changes
- Handle edge cases (division by zero, first-time users)

---

### 2. 📊 **Points Timeline Chart**

**Current Issue:** No time-series data for graphing points over time
**Frontend Needs:** Historical points data grouped by time periods

#### Required Endpoint:
```http
GET /api/points/timeline/?granularity={granularity}&days={days}
```

**Parameters:**
- `granularity`: `daily`, `weekly`, `monthly` (optional, defaults to daily)
- `days`: Number of days to look back (optional, defaults to 30)

**Expected Response:**
```json
{
  "timeline": [
    {
      "date": "2024-01-01",
      "points_earned": 10,
      "cumulative_points": 110,
      "activities_count": 2
    },
    {
      "date": "2024-01-02", 
      "points_earned": 25,
      "cumulative_points": 135,
      "activities_count": 1
    },
    {
      "date": "2024-01-03",
      "points_earned": 0,
      "cumulative_points": 135,
      "activities_count": 0
    }
  ],
  "summary": {
    "total_days": 30,
    "total_points_earned": 150,
    "average_daily_points": 5.0,
    "most_active_date": "2024-01-15"
  }
}
```

**Backend Implementation Notes:**
- Group points logs by date/week/month
- Calculate running totals (cumulative points)
- Fill gaps with zero values for consistent charting
- Consider timezone handling for date grouping

---

### 3. 🏆 **Leaderboard System**

**Current Issue:** Leaderboard page exists but has no data
**Frontend Needs:** Ranked list of users by points

#### Required Endpoint:
```http
GET /api/leaderboard/?limit={limit}&period={period}
```

**Parameters:**
- `limit`: Number of top users to return (optional, defaults to 10)
- `period`: `all_time`, `monthly`, `weekly` (optional, defaults to all_time)

**Expected Response:**
```json
{
  "leaderboard": [
    {
      "rank": 1,
      "user_id": 123,
      "username": "student_john",
      "display_name": "John D.", // Privacy-safe display name
      "total_points": 1250,
      "points_this_period": 150,
      "avatar_url": null, // Optional
      "is_current_user": false
    },
    {
      "rank": 2,
      "user_id": 456,
      "username": "student_jane",
      "display_name": "Jane S.",
      "total_points": 1100,
      "points_this_period": 200,
      "avatar_url": null,
      "is_current_user": false
    }
  ],
  "current_user_rank": {
    "rank": 15,
    "user_id": 789,
    "username": "current_user",
    "display_name": "You",
    "total_points": 450,
    "points_this_period": 50,
    "is_current_user": true
  },
  "total_participants": 150
}
```

**Backend Implementation Notes:**
- Include current user's rank even if outside top N
- Privacy considerations for display names
- Handle ties in rankings
- Consider caching for performance

---

### 4. 🎁 **Enhanced Rewards System**

**Current Issue:** Basic rewards list exists, but missing redemption functionality
**Frontend Needs:** Redemption tracking and user redemption history

#### Required Endpoints:

##### Get Available Rewards (Enhanced):
```http
GET /api/rewards/available/
```

**Expected Response:**
```json
{
  "rewards": [
    {
      "id": 1,
      "name": "P2E T-Shirt",
      "description": "Official Propel2Excel branded t-shirt",
      "points_required": 100,
      "image_url": "/images/tshirt.jpg",
      "category": "merchandise",
      "stock_available": 25,
      "can_redeem": true, // Based on user's current points
      "sponsor": "Propel2Excel"
    },
    {
      "id": 2,
      "name": "$25 Amazon Gift Card", 
      "description": "Digital Amazon gift card",
      "points_required": 250,
      "image_url": "/images/amazon.jpg",
      "category": "gift_cards",
      "stock_available": 10,
      "can_redeem": false,
      "sponsor": "Amazon"
    }
  ]
}
```

##### Redeem Reward:
```http
POST /api/rewards/redeem/
```

**Request Body:**
```json
{
  "reward_id": 1,
  "delivery_details": {
    "address": "123 Main St, City, State 12345", // If physical item
    "email": "user@example.com" // If digital item
  }
}
```

##### Get User Redemption History:
```http
GET /api/redemptions/history/
```

**Expected Response:**
```json
{
  "redemptions": [
    {
      "id": 1,
      "reward": {
        "name": "P2E T-Shirt",
        "image_url": "/images/tshirt.jpg"
      },
      "points_spent": 100,
      "redeemed_at": "2024-01-15T10:30:00Z",
      "status": "pending", // pending, approved, shipped, delivered, rejected
      "tracking_info": null,
      "estimated_delivery": "2024-01-22"
    }
  ]
}
```

---

### 5. 👤 **Enhanced Profile Management**

**Current Issue:** Profile page exists but minimal functionality
**Frontend Needs:** Profile editing and preference management

#### Required Endpoints:

##### Update Profile:
```http
PUT /api/users/profile/
```

**Request Body:**
```json
{
  "university": "Updated University",
  "major": "Computer Science", 
  "graduation_year": 2025,
  "bio": "Student passionate about technology",
  "privacy_settings": {
    "show_in_leaderboard": true,
    "display_name_preference": "first_name_only" // full_name, first_name_only, username
  }
}
```

##### Get Activity Preferences:
```http
GET /api/users/activity-preferences/
```

**Expected Response:**
```json
{
  "email_notifications": {
    "new_activities": true,
    "reward_updates": true,
    "leaderboard_changes": false
  },
  "discord_integration": {
    "is_linked": true,
    "discord_username": "user#1234",
    "sync_activities": true
  }
}
```

---

## 🛠️ **IMPLEMENTATION PRIORITY**

### High Priority (Core Functionality)
1. **Leaderboard System** - Page exists but empty
2. **Enhanced Rewards System** - Core feature for user engagement

### Medium Priority (Analytics & UX)
3. **Dashboard Statistics with Trends** - Improves dashboard value
4. **Points Timeline Chart** - Visual progress tracking

### Low Priority (Nice to Have)
5. **Enhanced Profile Management** - User customization

---

## 📋 **DATABASE SCHEMA ADDITIONS**

### New Tables Needed:

#### Redemptions Table:
```sql
CREATE TABLE redemptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    reward_id INTEGER REFERENCES incentives(id),
    points_spent INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    delivery_details JSONB,
    redeemed_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP NULL,
    tracking_info VARCHAR(255) NULL,
    notes TEXT NULL
);
```

#### User Preferences Table:
```sql
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) UNIQUE,
    email_notifications JSONB DEFAULT '{}',
    privacy_settings JSONB DEFAULT '{}',
    display_preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔄 **API RESPONSE STANDARDS**

### Success Response Format:
```json
{
  "success": true,
  "data": { /* response data */ },
  "message": "Operation completed successfully",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Response Format:
```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_POINTS",
    "message": "Not enough points to redeem this reward",
    "details": {
      "required": 100,
      "available": 75
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🧪 **TESTING REQUIREMENTS**

### Data for Testing:
1. **Multiple users** with varying point totals for leaderboard
2. **Historical point activities** spanning several months for timeline charts
3. **Various activity categories** for radar chart testing
4. **Different reward types** with varying point requirements
5. **Sample redemption history** for testing redemption flow

### Test Scenarios:
- Users with zero points/activities (empty states)
- Users with maximum points (edge cases)
- Tied rankings in leaderboard
- Insufficient points for redemptions
- API failures and error handling

---

## 📞 **FRONTEND INTEGRATION NOTES**

### Current Frontend Capabilities:
- ✅ **Real-time API integration** with authentication
- ✅ **Error handling** and loading states
- ✅ **Responsive design** for all screen sizes
- ✅ **TypeScript interfaces** for type safety

### Frontend Will Handle:
- Data caching and optimization
- User interface state management
- Form validation and submission
- Real-time updates and polling
- Error recovery and retry logic

### Backend Should Provide:
- **Consistent API responses** following the documented format
- **Proper HTTP status codes** for different scenarios
- **Authentication validation** on all protected endpoints
- **Input validation** and sanitization
- **Rate limiting** for API endpoints

---

## 🚀 **DEPLOYMENT CONSIDERATIONS**

### Environment Variables Needed:
```bash
# Frontend (.env.local)
NEXT_PUBLIC_API_BASE_URL=https://api.propel2excel.com
NEXTAUTH_SECRET=your-secret-key
NEXTAUTH_URL=https://frontend.propel2excel.com
```

### CORS Configuration:
```python
# Backend settings.py
CORS_ALLOWED_ORIGINS = [
    "https://frontend.propel2excel.com",
    "http://localhost:3000",  # For development
]
```

---

This document provides a complete roadmap for backend implementation to support all frontend features. Each section includes specific technical requirements, expected data formats, and implementation notes to ensure seamless integration.
