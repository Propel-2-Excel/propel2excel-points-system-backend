#!/usr/bin/env python
"""
Sample data creation script for the Propel2Excel Points System.
This script creates sample activities, incentives, and user data for testing the frontend.
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import User, Activity, PointsLog, Incentive, UserPreferences
from django.contrib.auth import get_user_model

def create_sample_activities():
    """Create sample activities with categories"""
    activities = [
        {
            'name': 'Discord Daily Check-in',
            'activity_type': 'discord_activity',
            'category': 'engagement',
            'points_value': 5,
            'description': 'Daily participation in Discord server'
        },
        {
            'name': 'Resume Upload',
            'activity_type': 'resume_upload',
            'category': 'professional',
            'points_value': 25,
            'description': 'Upload resume for review'
        },
        {
            'name': 'LinkedIn Post Share',
            'activity_type': 'linkedin_post',
            'category': 'social',
            'points_value': 15,
            'description': 'Share career-related content on LinkedIn'
        },
        {
            'name': 'Event Attendance',
            'activity_type': 'event_attendance',
            'category': 'events',
            'points_value': 30,
            'description': 'Attend virtual or in-person events'
        },
        {
            'name': 'Resource Sharing',
            'activity_type': 'resource_share',
            'category': 'content',
            'points_value': 20,
            'description': 'Share helpful resources with community'
        },
        {
            'name': 'Resume Review Request',
            'activity_type': 'resume_review_request',
            'category': 'professional',
            'points_value': 50,
            'description': 'Request professional resume review'
        },
        {
            'name': 'Community Interaction',
            'activity_type': 'like_interaction',
            'category': 'engagement',
            'points_value': 10,
            'description': 'Engage with community posts and discussions'
        }
    ]
    
    created_count = 0
    for activity_data in activities:
        activity, created = Activity.objects.get_or_create(
            activity_type=activity_data['activity_type'],
            defaults=activity_data
        )
        if created:
            created_count += 1
            print(f"Created activity: {activity.name}")
    
    print(f"Created {created_count} new activities")

def create_sample_incentives():
    """Create sample incentives/rewards with categories"""
    incentives = [
        {
            'name': 'P2E T-Shirt',
            'description': 'Official Propel2Excel branded t-shirt in your size',
            'points_required': 100,
            'category': 'merchandise',
            'sponsor': 'Propel2Excel',
            'stock_available': 25,
            'image_url': 'https://via.placeholder.com/300x200?text=P2E+T-Shirt'
        },
        {
            'name': '$25 Amazon Gift Card',
            'description': 'Digital Amazon gift card delivered via email',
            'points_required': 250,
            'category': 'gift_cards',
            'sponsor': 'Amazon',
            'stock_available': 10,
            'image_url': 'https://via.placeholder.com/300x200?text=Amazon+Gift+Card'
        },
        {
            'name': 'P2E Water Bottle',
            'description': 'Stainless steel water bottle with P2E logo',
            'points_required': 75,
            'category': 'merchandise',
            'sponsor': 'Propel2Excel',
            'stock_available': 50,
            'image_url': 'https://via.placeholder.com/300x200?text=P2E+Water+Bottle'
        },
        {
            'name': '$50 Starbucks Gift Card',
            'description': 'Perfect for your daily coffee needs',
            'points_required': 400,
            'category': 'gift_cards',
            'sponsor': 'Starbucks',
            'stock_available': 5,
            'image_url': 'https://via.placeholder.com/300x200?text=Starbucks+Gift+Card'
        },
        {
            'name': '1:1 Career Coaching Sessions',
            'description': 'Paired up with a volunteered champion who serves as coach to help you land your dream role and company',
            'points_required': 500,
            'category': 'services',
            'sponsor': 'P2E Career Services',
            'stock_available': 50,
            'image_url': 'https://via.placeholder.com/300x200?text=Career+Coaching'
        },
        {
            'name': 'P2E Laptop Sticker Pack',
            'description': 'Set of 5 premium vinyl stickers',
            'points_required': 50,
            'category': 'merchandise',
            'sponsor': 'Propel2Excel',
            'stock_available': 100,
            'image_url': 'https://via.placeholder.com/300x200?text=Sticker+Pack'
        },
        {
            'name': '$100 Best Buy Gift Card',
            'description': 'Electronics and tech accessories',
            'points_required': 750,
            'category': 'gift_cards',
            'sponsor': 'Best Buy',
            'stock_available': 3,
            'image_url': 'https://via.placeholder.com/300x200?text=Best+Buy+Gift+Card'
        },
        {
            'name': 'Resume Template Bundle',
            'description': '3 Resumes that landed offers in your company and role of interest',
            'points_required': 150,
            'category': 'digital',
            'sponsor': 'P2E Resources',
            'stock_available': 999,
            'image_url': 'https://via.placeholder.com/300x200?text=Resume+Templates'
        },
        {
            'name': 'Azure E-Learning',
            'description': 'Educational materials and training to gain the necessary knowledge to obtain a certification',
            'points_required': 50,
            'category': 'digital',
            'sponsor': 'Microsoft',
            'stock_available': 999,
            'image_url': 'https://via.placeholder.com/300x200?text=Azure+E-Learning'
        },
        {
            'name': 'Azure Exam Vouchers',
            'description': 'Free exam voucher code to sit for your certification exam',
            'points_required': 100,
            'category': 'digital',
            'sponsor': 'Microsoft',
            'stock_available': 50,
            'image_url': 'https://via.placeholder.com/300x200?text=Azure+Exam+Voucher'
        }
    ]
    
    created_count = 0
    for incentive_data in incentives:
        incentive, created = Incentive.objects.get_or_create(
            name=incentive_data['name'],
            defaults=incentive_data
        )
        if created:
            created_count += 1
            print(f"Created incentive: {incentive.name}")
    
    print(f"Created {created_count} new incentives")

def create_sample_users_and_activity():
    """Create sample users with historical activity"""
    sample_users = [
        {
            'username': 'student_alice',
            'email': 'alice@example.com',
            'first_name': 'Alice',
            'last_name': 'Johnson',
            'role': 'student',
            'university': 'State University',
            'total_points': 0  # Will be calculated
        },
        {
            'username': 'student_bob',
            'email': 'bob@example.com',
            'first_name': 'Bob',
            'last_name': 'Smith',
            'role': 'student',
            'university': 'Tech Institute',
            'total_points': 0
        },
        {
            'username': 'student_carol',
            'email': 'carol@example.com',
            'first_name': 'Carol',
            'last_name': 'Davis',
            'role': 'student',
            'university': 'Business College',
            'total_points': 0
        },
        {
            'username': 'student_david',
            'email': 'david@example.com',
            'first_name': 'David',
            'last_name': 'Wilson',
            'role': 'student',
            'university': 'Engineering School',
            'total_points': 0
        },
        {
            'username': 'student_eva',
            'email': 'eva@example.com',
            'first_name': 'Eva',
            'last_name': 'Martinez',
            'role': 'student',
            'university': 'Liberal Arts College',
            'total_points': 0
        }
    ]
    
    # Get all activities
    activities = list(Activity.objects.filter(is_active=True))
    if not activities:
        print("No activities found. Please run create_sample_activities first.")
        return
    
    created_users = 0
    created_logs = 0
    
    for user_data in sample_users:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults=user_data
        )
        
        if created:
            created_users += 1
            print(f"Created user: {user.username}")
            
            # Create user preferences
            UserPreferences.objects.get_or_create(
                user=user,
                defaults={
                    'email_notifications': {
                        'new_activities': True,
                        'reward_updates': True,
                        'leaderboard_changes': False
                    },
                    'privacy_settings': {
                        'show_in_leaderboard': True,
                        'display_name_preference': 'first_name_only'
                    },
                    'display_preferences': {}
                }
            )
        
        # Create historical activity (last 60 days)
        if created:
            import random
            total_points = 0
            
            # Create activity over the last 60 days
            for days_ago in range(60, 0, -1):
                activity_date = timezone.now() - timedelta(days=days_ago)
                
                # Random chance of activity each day (30-70% chance)
                if random.random() < 0.5:
                    # 1-3 activities per active day
                    num_activities = random.randint(1, 3)
                    
                    for _ in range(num_activities):
                        activity = random.choice(activities)
                        
                        # Create points log
                        points_log = PointsLog.objects.create(
                            user=user,
                            activity=activity,
                            points_earned=activity.points_value,
                            details=f"Sample activity from {days_ago} days ago",
                            timestamp=activity_date
                        )
                        
                        total_points += activity.points_value
                        created_logs += 1
            
            # Update user's total points
            user.total_points = total_points
            user.save()
            print(f"  Created {user.points_logs.count()} activity logs for {user.username} (Total: {total_points} points)")
    
    print(f"Created {created_users} new users and {created_logs} activity logs")

def main():
    """Main function to create all sample data"""
    print("Creating sample data for Propel2Excel Points System...")
    print("=" * 50)
    
    print("\n1. Creating sample activities...")
    create_sample_activities()
    
    print("\n2. Creating sample incentives...")
    create_sample_incentives()
    
    print("\n3. Creating sample users and activity history...")
    create_sample_users_and_activity()
    
    print("\n" + "=" * 50)
    print("Sample data creation completed!")
    
    # Print summary
    print(f"\nSummary:")
    print(f"- Activities: {Activity.objects.count()}")
    print(f"- Incentives: {Incentive.objects.count()}")
    print(f"- Users: {User.objects.count()}")
    print(f"- Points Logs: {PointsLog.objects.count()}")
    print(f"- User Preferences: {UserPreferences.objects.count()}")
    
    # Print top users
    print(f"\nTop 5 Users by Points:")
    top_users = User.objects.exclude(total_points=0).order_by('-total_points')[:5]
    for i, user in enumerate(top_users, 1):
        print(f"  {i}. {user.first_name} {user.last_name} ({user.username}): {user.total_points} points")

if __name__ == "__main__":
    main()

