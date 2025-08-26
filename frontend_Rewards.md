# Frontend Rewards System Integration Guide

## 🎯 Overview

The rewards system is fully functional with all API endpoints working correctly. The backend provides 11 rewards that should **ALWAYS be displayed** in the frontend, regardless of whether the user can redeem them or not.

## 📊 Current System Status

✅ **Backend Fixed**: All API routing issues resolved  
✅ **Data Available**: 11 rewards in database  
✅ **Authentication**: Working correctly  
✅ **User Points**: Demo user updated to 932 points  

## 🔌 API Endpoints

### 1. Available Rewards
```
GET /api/rewards/available/
```

**Headers Required:**
```
Authorization: Bearer {JWT_TOKEN}
Content-Type: application/json
```

**Response Format:**
```json
{
  "rewards": [
    {
      "id": 9,
      "name": "P2E Laptop Sticker Pack",
      "description": "Set of 5 premium vinyl stickers",
      "points_required": 50,
      "image_url": "https://via.placeholder.com/300x200?text=Sticker+Pack",
      "category": "merchandise",
      "stock_available": 100,
      "can_redeem": true,
      "sponsor": "Propel2Excel"
    }
  ]
}
```

**Current Data (11 total rewards):**
- **8 redeemable** (for users with 932+ points)
- **3 non-redeemable** (out of stock or insufficient points)

### 2. Redemption History
```
GET /api/redemptions/history/
```

**Headers Required:**
```
Authorization: Bearer {JWT_TOKEN}
Content-Type: application/json
```

**Response Format:**
```json
{
  "redemptions": [
    {
      "id": 1,
      "reward": {
        "name": "P2E T-Shirt",
        "image_url": "https://via.placeholder.com/300x200?text=P2E+T-Shirt"
      },
      "points_spent": 100,
      "redeemed_at": "2025-08-26T08:14:17.123Z",
      "status": "pending",
      "tracking_info": null,
      "estimated_delivery": null
    }
  ]
}
```

### 3. Redeem Reward
```
POST /api/rewards/redeem/
```

**Headers Required:**
```
Authorization: Bearer {JWT_TOKEN}
Content-Type: application/json
```

**Request Body:**
```json
{
  "reward_id": 9,
  "delivery_details": {
    "address": "123 Main St",
    "city": "Boston",
    "state": "MA",
    "zip": "02101"
  }
}
```

**Response Format:**
```json
{
  "success": true,
  "data": {
    "redemption_id": 1,
    "reward_name": "P2E Laptop Sticker Pack",
    "points_spent": 50,
    "remaining_points": 882,
    "status": "pending"
  },
  "message": "Successfully redeemed P2E Laptop Sticker Pack",
  "timestamp": "2025-08-26T08:14:17.123Z"
}
```

## 🎨 Frontend Display Requirements

### **Critical Rule: ALWAYS Show All Rewards**

The frontend must display **ALL 11 rewards** regardless of redemption status. Use the `can_redeem` field to control interactivity, not visibility.

```javascript
// ✅ CORRECT - Show all rewards
const displayRewards = rewards; // Show all 11 rewards

// ❌ WRONG - Don't filter out non-redeemable rewards
const displayRewards = rewards.filter(r => r.can_redeem); 
```

### **Visual States**

1. **Redeemable Rewards** (`can_redeem: true`)
   - Full color display
   - "Redeem" button enabled
   - Green checkmark or "Available" badge

2. **Non-Redeemable Rewards** (`can_redeem: false`)
   - Grayed out or muted display
   - "Redeem" button disabled
   - Show reason: "Need X more points" or "Out of stock"

### **Categories to Display**
- `merchandise` (4 items)
- `gift_cards` (3 items) 
- `digital` (1 item)
- `services` (1 item)
- `other` (2 items)

## 📝 Reward Details

### **Available Rewards List:**
1. **P2E Laptop Sticker Pack** - 50 points (redeemable)
2. **Azure Certification** - 50 points (out of stock)
3. **P2E Water Bottle** - 75 points (redeemable)
4. **Resume Review** - 75 points (out of stock)
5. **P2E T-Shirt** - 100 points (redeemable)
6. **Hackathon Entry** - 100 points (out of stock)
7. **Resume Template Bundle** - 150 points (redeemable)
8. **$25 Amazon Gift Card** - 250 points (redeemable)
9. **$50 Starbucks Gift Card** - 400 points (redeemable)
10. **1-on-1 Career Coaching Session** - 500 points (redeemable)
11. **$100 Best Buy Gift Card** - 750 points (redeemable)

## 🔧 Implementation Notes

### **Authentication**
- All endpoints require JWT authentication
- Use the user's access token in the Authorization header
- Demo user has 932 points for testing

### **Error Handling**
```javascript
// Handle insufficient points
if (response.error?.code === 'INSUFFICIENT_POINTS') {
  showMessage(`Need ${response.error.details.required - response.error.details.available} more points`);
}

// Handle out of stock
if (response.error?.code === 'OUT_OF_STOCK') {
  showMessage('This reward is currently out of stock');
}
```

### **User Experience**
- **Loading State**: Show skeleton cards while fetching rewards
- **Empty State**: If no rewards (shouldn't happen), show "No rewards available"
- **Success State**: Show confirmation with remaining points after redemption

## 🚀 Testing

### **Verify These Work:**
1. Load rewards page → Should show 11 rewards
2. Filter by category → Should work for all categories
3. Click redeemable reward → Should open redemption modal
4. Click non-redeemable reward → Should show helpful message
5. View redemption history → Should load (empty for new users)

### **Test Users:**
- `demo_user`: 932 points (8 redeemable rewards)
- `testuser`: 5 points (0 redeemable rewards, all should still display)

## ✅ Status Summary

**Backend Issues**: ✅ All FIXED
- Routing conflicts resolved
- All endpoints returning correct data
- User points properly configured

**Frontend Ready**: ✅ YES
- All APIs working
- Proper authentication
- Complete reward data available

The rewards system is now fully functional and ready for frontend integration! 🎉
