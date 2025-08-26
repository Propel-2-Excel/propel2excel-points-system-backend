# Demo Data Patterns - Time & Category Diversity

## Overview

The demo users now have **both diverse category focuses AND different temporal activity patterns**, making them perfect for comprehensive frontend testing of all analytics features.

---

## 👥 **Demo Users - Unique Patterns**

### 1. Carol Davis - **1,904 Points** 👑
- **Username:** `student_carol` / **Password:** `carol123`
- **Pattern:** Long-term consistent user (6 months)
- **Time Span:** Feb 27 - Aug 25 (179 days)
- **Temporal Pattern:** Recent boost (50% more active in last 30 days)
- **Category Focus:** 40% Professional, 30% Engagement, 15% Social
- **Distribution:** 477 pts recent (30d) | 1,427 pts historical

### 2. David Wilson - **1,723 Points** 🥈  
- **Username:** `student_david` / **Password:** `david123`
- **Pattern:** Recent high achiever (3 months)
- **Time Span:** May 28 - Aug 25 (89 days)
- **Temporal Pattern:** Consistently high activity (85% active days)
- **Category Focus:** 50% Professional, 25% Events, 15% Engagement
- **Distribution:** 583 pts recent (30d) | 1,140 pts historical

### 3. Alice Johnson - **1,159 Points** 🥉
- **Username:** `student_alice` / **Password:** `alice123`
- **Pattern:** Event-driven participant (5 months)
- **Time Span:** Apr 1 - Aug 17 (138 days)
- **Temporal Pattern:** Activity spikes every 3 weeks (event cycles)
- **Category Focus:** 50% Events, 25% Professional, 15% Engagement
- **Distribution:** 153 pts recent (30d) | 1,006 pts historical

### 4. Eva Martinez - **478 Points**
- **Username:** `student_eva` / **Password:** `eva123`
- **Pattern:** Weekend social warrior (4 months)
- **Time Span:** May 3 - Aug 24 (113 days)
- **Temporal Pattern:** 2.5x more active on weekends
- **Category Focus:** 40% Social, 30% Engagement, 15% Professional
- **Distribution:** 91 pts recent (30d) | 387 pts historical

### 5. Bob Smith - **134 Points**
- **Username:** `student_bob` / **Password:** `bob123`
- **Pattern:** Growing new user (6 weeks)
- **Time Span:** Jul 16 - Aug 24 (39 days)
- **Temporal Pattern:** Growth curve (started 20%, now 80% activity)
- **Category Focus:** 35% Content, 30% Engagement, 20% Professional
- **Distribution:** 98 pts recent (30d) | 36 pts historical

---

## 📊 **Perfect for Testing**

### **Timeline Charts:**
- **Carol:** Long-term trend with recent acceleration
- **David:** Steady high performance over 3 months
- **Alice:** Dramatic spikes every 3 weeks
- **Eva:** Weekend-heavy patterns
- **Bob:** Clear growth trajectory

### **Dashboard Trends:**
- **Recent vs Historical:** Every user has different ratios
- **Period Comparisons:** Varied patterns for 7/30/90 day analysis
- **Growth Indicators:** Mix of up/down/steady trends

### **Category Radar Charts:**
- **Professional Focus:** David (50%), Carol (40%)
- **Event Focus:** Alice (50%)
- **Social Focus:** Eva (40%)
- **Content Focus:** Bob (35%)
- **Engagement:** Spread across all users

### **Leaderboard Dynamics:**
- **Different time periods show different leaders**
- **Recent activity vs all-time rankings vary**
- **Realistic competition between users**

---

## 🎯 **Specific Test Scenarios**

### **Timeline Chart Testing:**
1. **Login as Carol** - See 6-month history with recent boost
2. **Switch to Alice** - See event-driven spikes pattern
3. **Check Bob** - See clear growth curve from new user
4. **Compare Eva** - See weekend-focused activity

### **Dashboard Stats Testing:**
1. **30-day trends** - Different for each user
2. **Period comparisons** - Varied historical vs recent
3. **Growth indicators** - Mix of up/down/steady

### **Category Analysis:**
1. **Professional leaders** - David and Carol
2. **Event specialist** - Alice
3. **Social influencer** - Eva  
4. **Content creator** - Bob

### **Leaderboard Variations:**
1. **All-time:** Carol > David > Alice > Eva > Bob
2. **Recent 30 days:** David > Carol > Alice > Bob > Eva
3. **Monthly/Weekly:** Different patterns based on activity cycles

---

## 🔍 **Data Verification**

### **Timestamp Distribution:**
- ✅ **Carol:** 179 days of history (Feb-Aug)
- ✅ **David:** 89 days of history (May-Aug)
- ✅ **Alice:** 138 days of history (Apr-Aug)
- ✅ **Eva:** 113 days of history (May-Aug)
- ✅ **Bob:** 39 days of history (Jul-Aug)

### **Activity Patterns:**
- ✅ **Weekend spikes** (Eva)
- ✅ **Event cycles** (Alice - every 3 weeks)
- ✅ **Recent boost** (Carol - 50% increase)
- ✅ **Growth curve** (Bob - 20% to 80%)
- ✅ **Steady high** (David - 85% active days)

### **Category Distribution:**
- ✅ **Professional:** David (50%), Carol (40%)
- ✅ **Events:** Alice (50%)
- ✅ **Social:** Eva (40%)
- ✅ **Content:** Bob (35%)
- ✅ **Engagement:** Distributed across all

---

## 🚀 **API Endpoints Ready**

All endpoints now return rich, realistic data:

- **`/api/dashboard/stats/`** - Real period-over-period trends
- **`/api/points/timeline/`** - Historical data with patterns
- **`/api/leaderboard/`** - Dynamic rankings by time period
- **`/api/points-logs/`** - Activity history with categories
- **`/api/rewards/available/`** - Varied redemption capabilities

## 🎉 **Result**

Each demo user now provides a **completely unique testing experience** with realistic data patterns that mirror real-world usage. Perfect for demonstrating all frontend analytics, gamification, and engagement features! 

The data includes:
- ✅ **6 months of historical activity** (Carol)
- ✅ **Different temporal patterns** (weekend, events, growth, boost)
- ✅ **Diverse category focuses** (professional, social, events, content)
- ✅ **Realistic point distributions** (134-1,904 points)
- ✅ **Varied recent vs historical ratios** for trend testing
