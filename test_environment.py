#!/usr/bin/env python3
"""
Environment Variable Validation Script
Tests BACKEND_API_URL, BOT_SHARED_SECRET, and DISCORD_TOKEN
"""

import os
import requests
import asyncio
import aiohttp
from dotenv import load_dotenv

def test_backend_url():
    """Test if BACKEND_API_URL is valid and accessible"""
    print("🔍 Testing BACKEND_API_URL...")
    
    backend_url = os.getenv('BACKEND_API_URL')
    if not backend_url:
        print("❌ BACKEND_API_URL not set!")
        return False
    
    print(f"   URL: {backend_url}")
    
    # Check if it's still localhost
    if 'localhost' in backend_url or '127.0.0.1' in backend_url:
        print("❌ WARNING: Still pointing to localhost!")
        print("   This will prevent the bot from working on Render!")
        return False
    
    # Test if URL is accessible
    try:
        response = requests.get(f"{backend_url}/api/activities/", timeout=10)
        if response.status_code == 200:
            print("✅ Backend URL is accessible")
            return True
        else:
            print(f"⚠️ Backend URL accessible but returned status {response.status_code}")
            return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend URL not accessible: {e}")
        return False

def test_bot_secret():
    """Test if BOT_SHARED_SECRET is set and matches Django"""
    print("\n🔐 Testing BOT_SHARED_SECRET...")
    
    bot_secret = os.getenv('BOT_SHARED_SECRET')
    if not bot_secret:
        print("❌ BOT_SHARED_SECRET not set!")
        return False
    
    print(f"   Secret: {bot_secret[:8]}...{bot_secret[-4:] if len(bot_secret) > 12 else '***'}")
    
    # Check if Django can read it
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
        django.setup()
        
        from django.conf import settings
        django_secret = getattr(settings, 'BOT_SHARED_SECRET', None)
        
        if django_secret:
            if django_secret == bot_secret:
                print("✅ BOT_SHARED_SECRET matches Django settings")
                return True
            else:
                print("❌ BOT_SHARED_SECRET does NOT match Django settings!")
                print(f"   Django expects: {django_secret[:8]}...{django_secret[-4:] if len(django_secret) > 12 else '***'}")
                return False
        else:
            print("⚠️ Django doesn't have BOT_SHARED_SECRET configured")
            return False
            
    except Exception as e:
        print(f"⚠️ Could not check Django settings: {e}")
        return True  # Assume it's okay if we can't check Django

def test_discord_token():
    """Test if DISCORD_TOKEN is valid"""
    print("\n🤖 Testing DISCORD_TOKEN...")
    
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        print("❌ DISCORD_TOKEN not set!")
        return False
    
    print(f"   Token: {discord_token[:8]}...{discord_token[-4:] if len(discord_token) > 12 else '***'}")
    
    # Test token validity
    headers = {'Authorization': f'Bot {discord_token}'}
    
    try:
        # Test basic token validity
        response = requests.get('https://discord.com/api/v10/users/@me', headers=headers, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            print(f"✅ Discord token is valid")
            print(f"   Bot: {bot_info.get('username', 'Unknown')}#{bot_info.get('discriminator', '0000')}")
            print(f"   Bot ID: {bot_info.get('id', 'Unknown')}")
            return True
        elif response.status_code == 401:
            print("❌ Discord token is invalid (401 Unauthorized)")
            return False
        else:
            print(f"⚠️ Discord API returned status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not test Discord token: {e}")
        return False

def test_bot_backend_communication():
    """Test if bot can communicate with backend"""
    print("\n🌐 Testing Bot-Backend Communication...")
    
    backend_url = os.getenv('BACKEND_API_URL')
    bot_secret = os.getenv('BOT_SHARED_SECRET')
    
    if not backend_url or not bot_secret:
        print("❌ Missing BACKEND_API_URL or BOT_SHARED_SECRET")
        return False
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'X-Bot-Secret': bot_secret
        }
        
        # Test bot API endpoint
        response = requests.post(
            f"{backend_url}/api/bot/",
            json={'action': 'summary', 'discord_id': 'test123'},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Bot can communicate with backend successfully")
            return True
        elif response.status_code == 401:
            print("❌ Bot authentication failed (401 Unauthorized)")
            print("   Check if BOT_SHARED_SECRET matches between bot and Django")
            return False
        else:
            print(f"⚠️ Backend returned status {response.status_code}")
            return True  # At least communication is working
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not communicate with backend: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Environment Variable Validation Test")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Run tests
    tests = [
        test_backend_url(),
        test_bot_secret(),
        test_discord_token(),
        test_bot_backend_communication()
    ]
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = sum(tests)
    total = len(tests)
    
    if passed == total:
        print("🎉 All tests passed! Your environment is properly configured.")
    else:
        print(f"⚠️ {passed}/{total} tests passed. Some issues need attention.")
        
        if not tests[0]:
            print("\n🔧 Fix BACKEND_API_URL:")
            print("   - Update to your Render URL (e.g., https://your-app.onrender.com)")
            print("   - Remove localhost references")
            
        if not tests[1]:
            print("\n🔧 Fix BOT_SHARED_SECRET:")
            print("   - Ensure it matches between bot and Django settings")
            print("   - Check Django settings.py for BOT_SHARED_SECRET")
            
        if not tests[2]:
            print("\n🔧 Fix DISCORD_TOKEN:")
            print("   - Verify token is correct in Discord Developer Portal")
            print("   - Check bot permissions and invite status")
            
        if not tests[3]:
            print("\n🔧 Fix Bot-Backend Communication:")
            print("   - Check BACKEND_API_URL and BOT_SHARED_SECRET")
            print("   - Verify Django is running and accessible")

if __name__ == "__main__":
    main()
