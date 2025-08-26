# Demo User Login Credentials

## Overview

These are the demo users created for testing the frontend with realistic data. Each user has historical activity data spanning 60 days and different point totals to demonstrate the leaderboard and analytics features.

---

## 🏆 **Demo Users (Ranked by Points)**

### 1. David Wilson - **932 Points** 👑
- **Username:** `student_david`
- **Password:** `david123`
- **Email:** `david@example.com`
- **University:** Engineering School
- **Role:** Student
- **Status:** Professional development focused (73% professional activities)

### 2. Alice Johnson - **782 Points** 🥈
- **Username:** `student_alice`
- **Password:** `alice123`
- **Email:** `alice@example.com`
- **University:** State University
- **Role:** Student
- **Status:** Event-focused participant (48% events activities)

### 3. Carol Davis - **707 Points** 🥉
- **Username:** `student_carol`
- **Password:** `carol123`
- **Email:** `carol@example.com`
- **University:** Business College
- **Role:** Student
- **Status:** Balanced professional/events focus (59% professional, 21% events)

### 4. Bob Smith - **562 Points**
- **Username:** `student_bob`
- **Password:** `bob123`
- **Email:** `bob@example.com`
- **University:** Tech Institute
- **Role:** Student
- **Status:** Content creation specialist (36% content activities)

### 5. Eva Martinez - **477 Points**
- **Username:** `student_eva`
- **Password:** `eva123`
- **Email:** `eva@example.com`
- **University:** Liberal Arts College
- **Role:** Student
- **Status:** Social media influencer (18% social activities)

---

## 🧪 **Testing Scenarios**

### **Leaderboard Testing:**
- Login as **Carol** to see #1 position experience
- Login as **Bob** to see lower-ranked user experience
- Compare different user perspectives

### **Dashboard Analytics:**
- Each user has 60 days of historical activity
- Different activity patterns and point accumulation rates
- Great for testing timeline charts and trend analysis

### **Rewards Testing:**
- **Carol & David** can redeem high-value rewards (500+ points)
- **Eva & Alice** can redeem mid-tier rewards (100-500 points)  
- **Bob** can redeem entry-level rewards (50-100 points)

### **Profile Features:**
- All users have user preferences configured
- Privacy settings vary between users
- Discord integration status can be tested

---

## 🚀 **Quick Login Guide**

### For Frontend Testing:
1. Start the backend server: `python manage.py runserver`
2. Go to your frontend login page
3. Use any of the credentials above
4. Explore different user experiences based on their point levels

### API Testing:
```bash
# Login to get auth token
curl -X POST "http://localhost:8000/api/users/login/" \
  -H "Content-Type: application/json" \
  -d '{"username": "student_carol", "password": "carol123"}'

# Use the token in subsequent requests
curl -X GET "http://localhost:8000/api/dashboard/stats/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## 📊 **User Data Summary**

| User | Points | Top Category | Category % | Best For Testing |
|------|--------|--------------|------------|------------------|
| David | 932 | Professional | 73% | Professional development focus |
| Alice | 782 | Events | 48% | Event participation patterns |
| Carol | 707 | Professional | 59% | Balanced professional/events |
| Bob | 562 | Content | 36% | Content creation specialist |
| Eva | 477 | Professional | 50% | Social media influencer |

---

## 🔧 **Additional Notes**

- All users have **user preferences** configured with default settings
- **Privacy settings** are set to show first name only in leaderboard
- **Email notifications** are enabled for new activities and reward updates
- Historical activity includes all types: Discord, LinkedIn, Events, Resume uploads, etc.
- Activity dates span the last **60 days** for realistic timeline charts

---

## 🎯 **Recommended Testing Flow**

1. **Start with Carol** (highest points) - See the "winner" experience
2. **Switch to Bob** (lowest points) - See the "newcomer" experience  
3. **Test David or Eva** - See the "competitive middle" experience
4. **Compare leaderboard** positions across different users
5. **Test reward redemption** at different point levels
6. **Verify timeline charts** show different activity patterns

These demo users provide comprehensive test coverage for all frontend features! 🎉

