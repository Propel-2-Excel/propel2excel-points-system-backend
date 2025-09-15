#!/usr/bin/env python3
"""
Test Discord Bot Commands for Resume Review System
This script simulates Discord bot commands for testing
"""

import requests
import json
import os
from datetime import datetime

# Configuration
BASE_URL = 'http://localhost:8000'
BOT_SECRET = os.getenv('BOT_SHARED_SECRET', 'test-secret-change-me')

def simulate_discord_command(action, **kwargs):
    """Simulate a Discord bot command by calling the API"""
    headers = {
        'Content-Type': 'application/json',
        'X-Bot-Secret': BOT_SECRET
    }
    
    data = {'action': action, **kwargs}
    
    print(f"\n🤖 Simulating Discord Command: {action}")
    print(f"📤 Request: {json.dumps(data, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/api/bot/", json=data, headers=headers)
    
    print(f"📥 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success: {json.dumps(result, indent=2)}")
        return result
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_resume_review_workflow():
    """Test the complete resume review workflow via Discord commands"""
    
    print("="*60)
    print(" TESTING DISCORD BOT RESUME REVIEW WORKFLOW")
    print("="*60)
    
    # Test Discord ID for a test user
    test_discord_id = "987654321"
    
    # 1. Student requests resume review
    print("\n📋 Step 1: Student requests resume review (!resume command)")
    result = simulate_discord_command(
        'add-activity',
        discord_id=test_discord_id,
        activity_type='resume_review_request',
        details='Student requested resume review via !resume command'
    )
    
    # 2. Check user's review status
    print("\n📊 Step 2: Check review status (!review_status command)")
    result = simulate_discord_command(
        'review-status',
        discord_id=test_discord_id
    )
    
    # 3. Admin lists available professionals
    print("\n👥 Step 3: Admin lists professionals (!list_professionals command)")
    professionals_result = simulate_discord_command('list-professionals')
    
    # 4. Admin adds a new professional
    print("\n➕ Step 4: Admin adds new professional (!add_professional command)")
    result = simulate_discord_command(
        'add-professional',
        name='Dr. Emily Watson',
        email='emily@university.edu',
        specialties='Academic Research, PhD Applications'
    )
    
    # 5. Admin matches student with professional
    print("\n🤝 Step 5: Admin matches student with professional (!match_review command)")
    if professionals_result and professionals_result.get('professionals'):
        # Use the first available professional
        prof_id = professionals_result['professionals'][0]['id']
        result = simulate_discord_command(
            'match-review',
            discord_id=test_discord_id,
            professional_id=prof_id
        )
    else:
        print("❌ No professionals available for matching")
    
    # 6. Get program statistics
    print("\n📈 Step 6: Admin checks program statistics (!review_stats command)")
    result = simulate_discord_command('review-stats')
    
    # 7. Check updated review status
    print("\n🔄 Step 7: Check updated review status")
    result = simulate_discord_command(
        'review-status',
        discord_id=test_discord_id
    )

def test_error_scenarios():
    """Test error handling scenarios"""
    
    print("\n" + "="*60)
    print(" TESTING ERROR SCENARIOS")
    print("="*60)
    
    # Test with invalid Discord ID
    print("\n❌ Test 1: Invalid Discord ID")
    simulate_discord_command(
        'review-status',
        discord_id='invalid_user_123'
    )
    
    # Test with invalid professional ID
    print("\n❌ Test 2: Invalid Professional ID")
    simulate_discord_command(
        'match-review',
        discord_id='987654321',
        professional_id=99999
    )
    
    # Test with missing parameters
    print("\n❌ Test 3: Missing Parameters")
    simulate_discord_command(
        'add-professional',
        name='Incomplete Professional'
        # Missing email
    )

def test_authentication():
    """Test authentication scenarios"""
    
    print("\n" + "="*60)
    print(" TESTING AUTHENTICATION")
    print("="*60)
    
    # Test with wrong bot secret
    print("\n🔒 Test 1: Wrong Bot Secret")
    headers = {
        'Content-Type': 'application/json',
        'X-Bot-Secret': 'wrong-secret'
    }
    
    data = {'action': 'list-professionals'}
    response = requests.post(f"{BASE_URL}/api/bot/", json=data, headers=headers)
    
    if response.status_code == 401:
        print("✅ Correctly rejected unauthorized request")
    else:
        print(f"❌ Unexpected response: {response.status_code}")
    
    # Test with missing bot secret
    print("\n🔒 Test 2: Missing Bot Secret")
    headers = {'Content-Type': 'application/json'}
    response = requests.post(f"{BASE_URL}/api/bot/", json=data, headers=headers)
    
    if response.status_code == 401:
        print("✅ Correctly rejected request without secret")
    else:
        print(f"❌ Unexpected response: {response.status_code}")

if __name__ == "__main__":
    print("🤖 Discord Bot Resume Review Testing")
    print(f"🔗 API Endpoint: {BASE_URL}/api/bot/")
    print(f"🔑 Bot Secret: {BOT_SECRET}")
    
    # Run tests
    test_resume_review_workflow()
    test_error_scenarios()
    test_authentication()
    
    print("\n" + "="*60)
    print(" DISCORD BOT TESTING COMPLETE")
    print("="*60)
    print("\n💡 To test with actual Discord bot:")
    print("1. Set BOT_SHARED_SECRET in your .env file")
    print("2. Start the bot: python bot.py")
    print("3. Use these commands in Discord:")
    print("   • !resume")
    print("   • !review_status") 
    print("   • !list_professionals (admin)")
    print("   • !add_professional <name> <specialties> (admin)")
    print("   • !match_review <@user> <professional_name> (admin)")
    print("   • !review_stats (admin)")
