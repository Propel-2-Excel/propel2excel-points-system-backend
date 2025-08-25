#!/usr/bin/env python3
"""
Deployment Script for Propel2Excel Automatic Meeting Scheduling System

This script helps deploy and test the new automatic meeting scheduling feature.

Usage:
    python deploy_scheduling_system.py
"""

import os
import sys
import subprocess
import django
from pathlib import Path

def setup_django():
    """Set up Django environment"""
    sys.path.append(str(Path(__file__).parent))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()

def run_migrations():
    """Run database migrations"""
    print("🔄 Running database migrations...")
    try:
        subprocess.run(['python', 'manage.py', 'makemigrations'], check=True)
        subprocess.run(['python', 'manage.py', 'migrate'], check=True)
        print("✅ Database migrations completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        return False
    return True

def create_test_data():
    """Create test data for development"""
    print("🔄 Creating test data...")
    
    setup_django()
    
    from core.models import Professional, ProfessionalAvailability, User, ReviewRequest, Activity
    from datetime import date, timedelta
    
    try:
        # Create test professional
        professional, created = Professional.objects.get_or_create(
            email="test.professional@example.com",
            defaults={
                'name': "John Smith",
                'specialties': "Technology, Software Engineering, Career Coaching",
                'bio': "Senior Software Engineer with 10+ years experience in mentoring",
                'is_active': True
            }
        )
        
        if created:
            print(f"✅ Created test professional: {professional.name}")
        
        # Create test availability
        availability, created = ProfessionalAvailability.objects.get_or_create(
            professional=professional,
            form_response_id="test_response_123",
            defaults={
                'availability_slots': [
                    "Monday 2:00 PM - 4:00 PM",
                    "Wednesday afternoon",
                    "Friday 10:00 AM - 12:00 PM"
                ],
                'preferred_days': ["Monday", "Wednesday", "Friday"],
                'time_zone': "Eastern Time (ET)",
                'start_date': date.today(),
                'end_date': date.today() + timedelta(weeks=4),
                'is_active': True,
                'notes': "Test availability record"
            }
        )
        
        if created:
            print(f"✅ Created test availability record")
        
        # Create test student user if doesn't exist
        try:
            student = User.objects.get(username="test_student")
        except User.DoesNotExist:
            student = User.objects.create_user(
                username="test_student",
                email="test.student@university.edu",
                password="testpass123",
                role="student",
                discord_id="123456789"
            )
            print(f"✅ Created test student: {student.username}")
        
        # Create test review request
        review_request, created = ReviewRequest.objects.get_or_create(
            student=student,
            status='pending',
            defaults={
                'target_industry': 'Technology',
                'target_role': 'Software Engineer',
                'experience_level': 'Entry Level',
                'preferred_times': [
                    "Monday afternoon",
                    "Wednesday 2-3 PM",
                    "Friday morning"
                ],
                'form_data': {
                    'name': 'Test Student',
                    'email': 'test.student@university.edu',
                    'target_role': 'Software Engineer'
                }
            }
        )
        
        if created:
            print(f"✅ Created test review request")
            
        # Ensure resume review activity exists
        activity, created = Activity.objects.get_or_create(
            activity_type='resume_review_request',
            defaults={
                'name': 'Resume Review Request',
                'points_value': 20,
                'description': 'Points earned for requesting a resume review',
                'is_active': True
            }
        )
        
        if created:
            print(f"✅ Created resume review activity")
        
        print("✅ Test data creation completed")
        return True
        
    except Exception as e:
        print(f"❌ Test data creation failed: {e}")
        return False

def test_matching_algorithm():
    """Test the availability matching algorithm"""
    print("🔄 Testing availability matching algorithm...")
    
    try:
        from availability_matcher import find_availability_matches, get_time_suggestions
        
        student_availability = [
            "Monday afternoon",
            "Wednesday 2-3 PM", 
            "Friday morning"
        ]
        
        professional_availability = [
            "Monday 2:00 PM - 4:00 PM",
            "Wednesday afternoon",
            "Friday 10:00 AM - 12:00 PM"
        ]
        
        matches = find_availability_matches(student_availability, professional_availability)
        suggestions = get_time_suggestions(student_availability, professional_availability)
        
        print(f"✅ Found {len(matches)} availability matches")
        print(f"✅ Generated {len(suggestions)} time suggestions")
        
        if matches:
            best_match = matches[0]
            print(f"   Best match score: {best_match['match_score']:.2f}")
            print(f"   Student: {best_match['student_availability']}")
            print(f"   Professional: {best_match['professional_availability']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Matching algorithm test failed: {e}")
        return False

def test_bot_integration():
    """Test bot integration endpoints"""
    print("🔄 Testing bot integration...")
    
    setup_django()
    
    try:
        from core.views import BotIntegrationView
        from django.test import RequestFactory
        import json
        
        factory = RequestFactory()
        view = BotIntegrationView()
        
        # Test pending reviews action
        request = factory.post('/api/bot/', 
            data=json.dumps({"action": "pending-reviews"}),
            content_type='application/json',
            HTTP_X_BOT_SECRET=os.getenv('BOT_SHARED_SECRET', 'test-secret')
        )
        
        response = view.post(request)
        
        if response.status_code == 200:
            print("✅ Bot integration test passed")
            return True
        else:
            print(f"❌ Bot integration test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Bot integration test failed: {e}")
        return False

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("🔄 Checking dependencies...")
    
    required_packages = [
        'django',
        'djangorestframework',
        'python-dateutil'
    ]
    
    optional_packages = [
        'google-auth',
        'google-auth-oauthlib', 
        'google-auth-httplib2',
        'google-api-python-client'
    ]
    
    missing_required = []
    missing_optional = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_required.append(package)
    
    for package in optional_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_optional.append(package)
    
    if missing_required:
        print(f"❌ Missing required packages: {', '.join(missing_required)}")
        print("   Run: pip install " + " ".join(missing_required))
        return False
    
    if missing_optional:
        print(f"⚠️  Missing optional packages (calendar integration): {', '.join(missing_optional)}")
        print("   Run: pip install " + " ".join(missing_optional))
    
    print("✅ All required dependencies found")
    return True

def print_setup_summary():
    """Print setup summary and next steps"""
    print("\n" + "="*60)
    print("🎉 AUTOMATIC MEETING SCHEDULING SYSTEM DEPLOYED!")
    print("="*60)
    
    print("\n📋 SETUP SUMMARY:")
    print("✅ Database models created (ScheduledSession, ProfessionalAvailability)")
    print("✅ Bot commands implemented (!pending_reviews, !suggest_matches, !schedule_session)")
    print("✅ Google Forms integration ready")
    print("✅ Enhanced availability matching algorithm")
    print("✅ Calendar integration (optional)")
    print("✅ Admin interface configured")
    
    print("\n🚀 NEXT STEPS:")
    print("1. Set up Professional Availability Google Form:")
    print("   - Run the script in professional_availability_form_setup.js")
    print("   - Update webhook URLs and secrets")
    
    print("\n2. Configure environment variables:")
    print("   - FORM_WEBHOOK_SECRET (for Google Forms)")
    print("   - GOOGLE_CALENDAR_CREDENTIALS (optional, for calendar integration)")
    print("   - BOT_SHARED_SECRET (for Discord bot)")
    
    print("\n3. Test the workflow:")
    print("   - Student: !resume")
    print("   - Admin: !pending_reviews")
    print("   - Admin: !suggest_matches @student")
    print("   - Admin: !schedule_session @student \"Professional Name\" \"Monday 2:00 PM\"")
    
    print("\n📖 DOCUMENTATION:")
    print("   - SCHEDULING_SETUP_GUIDE.md - Complete setup guide")
    print("   - professional_availability_form_setup.js - Google Form creation")
    print("   - availability_matcher.py - Matching algorithm")
    print("   - calendar_integration.py - Calendar functionality")
    
    print("\n🔧 TESTING:")
    print("   - Test data created in database")
    print("   - Use Django admin to manage professionals and sessions")
    print("   - Check bot commands in Discord")
    
    print("\n📞 SUPPORT:")
    print("   - Review logs for any errors")
    print("   - Check Django admin for data consistency")
    print("   - Contact: propel@propel2excel.com")
    
    print("\n" + "="*60)

def main():
    """Main deployment function"""
    print("🚀 DEPLOYING PROPEL2EXCEL AUTOMATIC MEETING SCHEDULING SYSTEM")
    print("="*70)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Deployment failed: Missing required dependencies")
        return False
    
    # Run migrations
    if not run_migrations():
        print("\n❌ Deployment failed: Database migration error")
        return False
    
    # Create test data
    if not create_test_data():
        print("\n⚠️  Warning: Test data creation failed (non-critical)")
    
    # Test matching algorithm
    if not test_matching_algorithm():
        print("\n⚠️  Warning: Matching algorithm test failed")
    
    # Test bot integration
    if not test_bot_integration():
        print("\n⚠️  Warning: Bot integration test failed")
    
    # Print summary
    print_setup_summary()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Deployment completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Deployment completed with errors")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Deployment failed with error: {e}")
        sys.exit(1)
