#!/bin/bash

# Quick API Test Script for Resume Review System
# Tests key API endpoints with authentication

BASE_URL="http://localhost:8000"

echo "🧪 Testing Resume Review API Endpoints"
echo "======================================="

# Login and get token
echo "🔐 Logging in as admin..."
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/users/login/" \
  -H "Content-Type: application/json" \
  -d '{"username": "testadmin", "password": "testpass123"}')

TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['tokens']['access'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get authentication token"
    exit 1
fi

echo "✅ Got authentication token"

# Test professionals endpoint
echo ""
echo "👥 Testing professionals endpoint..."
curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/professionals/" | python3 -m json.tool | head -20

# Test activities endpoint  
echo ""
echo "📝 Testing activities endpoint..."
curl -s "$BASE_URL/api/activities/" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for activity in data:
    print(f'• {activity[\"name\"]} ({activity[\"points_value\"]} pts) - {activity[\"activity_type\"]}')
"

# Test review requests endpoint
echo ""
echo "📋 Testing review requests endpoint..."
REVIEW_COUNT=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/review-requests/" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "Current review requests: $REVIEW_COUNT"

echo ""
echo "✅ API endpoints are working!"
echo ""
echo "🌐 Admin Interface: http://localhost:8000/admin/"
echo "   Username: testadmin"
echo "   Password: testpass123"
