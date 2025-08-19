#!/usr/bin/env python3
"""
Comprehensive test script for the Resume Review System
Tests API endpoints, creates sample data, and validates functionality
"""

import os
import django
import requests
import json
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import User, Professional, ReviewRequest, Activity
from rest_framework_simplejwt.tokens import RefreshToken

# Test configuration
BASE_URL = 'http://localhost:8000'
BOT_SECRET = 'your-bot-secret'  # Replace with your actual secret

def print_section(title):
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def print_test(test_name):
    print(f"\n🧪 Testing: {test_name}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def create_test_data():
    """Create test users and professionals"""
    print_section("CREATING TEST DATA")
    
    # Create test admin user
    admin_user, created = User.objects.get_or_create(
        username='testadmin',
        defaults={
            'email': 'admin@propel2excel.com',
            'role': 'admin',
            'discord_id': '123456789',
            'total_points': 100
        }
    )
    if created:
        admin_user.set_password('testpass123')
        admin_user.save()
        print_success("Created admin user: testadmin")
    
    # Create test student user
    student_user, created = User.objects.get_or_create(
        username='teststudent',
        defaults={
            'email': 'student@example.com',
            'role': 'student',
            'discord_id': '987654321',
            'total_points': 50
        }
    )
    if created:
        student_user.set_password('testpass123')
        student_user.save()
        print_success("Created student user: teststudent")
    
    # Create test professionals
    professionals_data = [
        {
            'name': 'Sarah Johnson',
            'email': 'sarah@techcorp.com',
            'specialties': 'Software Engineering, Tech Startups',
            'bio': 'Senior Software Engineer with 8 years experience',
            'availability': {'days': ['Monday', 'Wednesday', 'Friday'], 'times': ['2pm-5pm']}
        },
        {
            'name': 'Michael Chen',
            'email': 'michael@consultingfirm.com',
            'specialties': 'Management Consulting, Finance',
            'bio': 'Management Consultant at top-tier firm',
            'availability': {'days': ['Tuesday', 'Thursday'], 'times': ['10am-12pm', '2pm-4pm']}
        }
    ]
    
    for prof_data in professionals_data:
        prof, created = Professional.objects.get_or_create(
            email=prof_data['email'],
            defaults=prof_data
        )
        if created:
            print_success(f"Created professional: {prof.name}")
    
    return admin_user, student_user

def get_auth_token(username, password):
    """Get JWT token for user"""
    response = requests.post(f"{BASE_URL}/api/users/login/", {
        'username': username,
        'password': password
    })
    if response.status_code == 200:
        return response.json()['tokens']['access']
    return None

def test_api_endpoints():
    """Test all resume review API endpoints"""
    print_section("TESTING API ENDPOINTS")
    
    # Get auth tokens
    admin_token = get_auth_token('testadmin', 'testpass123')
    student_token = get_auth_token('teststudent', 'testpass123')
    
    if not admin_token or not student_token:
        print_error("Failed to get auth tokens")
        return
    
    headers_admin = {'Authorization': f'Bearer {admin_token}'}
    headers_student = {'Authorization': f'Bearer {student_token}'}
    
    # Test 1: List Professionals (Admin)
    print_test("GET /api/professionals/ (Admin)")
    response = requests.get(f"{BASE_URL}/api/professionals/", headers=headers_admin)
    if response.status_code == 200:
        print_success(f"Found {len(response.json())} professionals")
        print(f"   Professional names: {[p['name'] for p in response.json()]}")
    else:
        print_error(f"Status: {response.status_code}")
    
    # Test 2: List Professionals (Student)
    print_test("GET /api/professionals/ (Student)")
    response = requests.get(f"{BASE_URL}/api/professionals/", headers=headers_student)
    if response.status_code == 200:
        print_success(f"Student can view {len(response.json())} active professionals")
    else:
        print_error(f"Status: {response.status_code}")
    
    # Test 3: Create Review Request (Student)
    print_test("POST /api/review-requests/ (Student)")
    review_data = {
        'target_industry': 'Technology',
        'target_role': 'Software Engineer',
        'experience_level': 'Entry Level',
        'preferred_times': ['Monday 2pm', 'Wednesday 3pm'],
        'priority': 'medium',
        'form_data': {
            'resume_url': 'https://example.com/resume.pdf',
            'cover_letter': 'I am interested in tech roles...'
        }
        # Note: student field is automatically set by the ViewSet
    }
    response = requests.post(f"{BASE_URL}/api/review-requests/", 
                           json=review_data, headers=headers_student)
    if response.status_code == 201:
        review_request_id = response.json()['id']
        print_success(f"Created review request with ID: {review_request_id}")
    else:
        print_error(f"Status: {response.status_code}, Response: {response.text}")
        return
    
    # Test 4: List Review Requests (Admin)
    print_test("GET /api/review-requests/ (Admin)")
    response = requests.get(f"{BASE_URL}/api/review-requests/", headers=headers_admin)
    if response.status_code == 200:
        requests_data = response.json()
        print_success(f"Admin can view {len(requests_data)} review requests")
        if requests_data:
            print(f"   Latest request: {requests_data[0]['student_username']} -> {requests_data[0]['target_role']}")
    
    # Test 5: Get Pending Requests (Admin)
    print_test("GET /api/review-requests/pending_requests/ (Admin)")
    response = requests.get(f"{BASE_URL}/api/review-requests/pending_requests/", headers=headers_admin)
    if response.status_code == 200:
        pending = response.json()
        print_success(f"Found {len(pending)} pending requests")
    
    # Test 6: Assign Professional (Admin)
    print_test("POST /api/review-requests/{id}/assign_professional/ (Admin)")
    # Get first professional ID
    professionals = requests.get(f"{BASE_URL}/api/professionals/", headers=headers_admin).json()
    if professionals:
        prof_id = professionals[0]['id']
        assign_data = {'professional_id': prof_id}
        response = requests.post(f"{BASE_URL}/api/review-requests/{review_request_id}/assign_professional/",
                               json=assign_data, headers=headers_admin)
        if response.status_code == 200:
            print_success(f"Assigned professional {professionals[0]['name']} to review request")
        else:
            print_error(f"Status: {response.status_code}, Response: {response.text}")
    
    # Test 7: Get Statistics (Admin)
    print_test("GET /api/review-requests/statistics/ (Admin)")
    response = requests.get(f"{BASE_URL}/api/review-requests/statistics/", headers=headers_admin)
    if response.status_code == 200:
        stats = response.json()
        print_success("Retrieved statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")

def test_bot_integration():
    """Test Discord bot integration endpoints"""
    print_section("TESTING DISCORD BOT INTEGRATION")
    
    bot_headers = {
        'Content-Type': 'application/json',
        'X-Bot-Secret': BOT_SECRET
    }
    
    # Test 1: List Professionals via Bot
    print_test("Bot: List Professionals")
    bot_data = {'action': 'list-professionals'}
    response = requests.post(f"{BASE_URL}/api/bot/", json=bot_data, headers=bot_headers)
    if response.status_code == 200:
        result = response.json()
        print_success(f"Bot found {result['total_count']} professionals")
        for prof in result['professionals']:
            print(f"   {prof['name']} - {prof['specialties']}")
    else:
        print_error(f"Status: {response.status_code}, Response: {response.text}")
    
    # Test 2: Review Status via Bot
    print_test("Bot: Check Review Status")
    bot_data = {
        'action': 'review-status',
        'discord_id': '987654321'  # teststudent's discord_id
    }
    response = requests.post(f"{BASE_URL}/api/bot/", json=bot_data, headers=bot_headers)
    if response.status_code == 200:
        result = response.json()
        if result['has_request']:
            print_success(f"Found review request with status: {result['status']}")
            print(f"   Professional: {result.get('professional', 'Not assigned')}")
        else:
            print_success("No review requests found for user")
    else:
        print_error(f"Status: {response.status_code}, Response: {response.text}")
    
    # Test 3: Add Professional via Bot
    print_test("Bot: Add Professional")
    bot_data = {
        'action': 'add-professional',
        'name': 'Alex Rodriguez',
        'email': 'alex@startup.com',
        'specialties': 'Product Management, Startups'
    }
    response = requests.post(f"{BASE_URL}/api/bot/", json=bot_data, headers=bot_headers)
    if response.status_code == 200:
        result = response.json()
        print_success(f"Added professional: {result['name']}")
    else:
        print_error(f"Status: {response.status_code}, Response: {response.text}")
    
    # Test 4: Get Review Stats via Bot
    print_test("Bot: Get Review Statistics")
    bot_data = {'action': 'review-stats'}
    response = requests.post(f"{BASE_URL}/api/bot/", json=bot_data, headers=bot_headers)
    if response.status_code == 200:
        stats = response.json()
        print_success("Retrieved statistics via bot:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
    else:
        print_error(f"Status: {response.status_code}, Response: {response.text}")
    
    # Test 5: Add Resume Review Activity via Bot
    print_test("Bot: Add Resume Review Activity")
    bot_data = {
        'action': 'add-activity',
        'discord_id': '987654321',
        'activity_type': 'resume_review_request',
        'details': 'Student requested resume review via Discord bot'
    }
    response = requests.post(f"{BASE_URL}/api/bot/", json=bot_data, headers=bot_headers)
    if response.status_code == 200:
        result = response.json()
        print_success(f"Added activity: {result['message']}")
        print(f"   New total points: {result['total_points']}")
    else:
        print_error(f"Status: {response.status_code}, Response: {response.text}")

def test_admin_interface():
    """Instructions for testing Django admin interface"""
    print_section("TESTING DJANGO ADMIN INTERFACE")
    
    print("🌐 To test the Django admin interface:")
    print("1. Go to: http://localhost:8000/admin/")
    print("2. Login with: testadmin / testpass123")
    print("\n📋 Test these sections:")
    print("   • Core > Professionals - Add/edit professional reviewers")
    print("   • Core > Review requests - Manage review requests")
    print("   • Core > Activities - Verify 'Resume Review Request' activity exists")
    print("   • Core > Users - View test users and their points")
    print("\n🔧 Try these admin actions:")
    print("   • Create a new professional")
    print("   • Change a review request status")
    print("   • Use bulk actions on review requests")
    print("   • View professional performance statistics")

def test_workflow():
    """Test the complete resume review workflow"""
    print_section("COMPLETE WORKFLOW TEST")
    
    print("🎯 Complete Resume Review Workflow:")
    print("1. Student uses Discord !resume command")
    print("2. Bot calls /api/bot/ with 'add-activity' for resume_review_request")
    print("3. Student fills Google Form")
    print("4. Admin creates ReviewRequest via API or admin interface")
    print("5. Admin assigns professional via !match_review or admin")
    print("6. Review session is coordinated")
    print("7. Review is marked complete with feedback")
    
    print("\n📝 Manual Test Steps:")
    print("1. Start Discord bot: python bot.py")
    print("2. Test !resume command in Discord")
    print("3. Check admin interface for new requests")
    print("4. Test !match_review command")
    print("5. Verify statistics update")

def main():
    """Run all tests"""
    print_section("RESUME REVIEW SYSTEM - COMPREHENSIVE TESTING")
    
    try:
        # Setup
        admin_user, student_user = create_test_data()
        
        # Wait for server to be ready
        import time
        time.sleep(2)
        
        # Run tests
        test_api_endpoints()
        test_bot_integration()
        test_admin_interface()
        test_workflow()
        
        print_section("TESTING COMPLETE")
        print("✅ All automated tests completed!")
        print("🔧 Follow the manual testing instructions above")
        print("📊 Check the admin interface at: http://localhost:8000/admin/")
        
    except Exception as e:
        print_error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
