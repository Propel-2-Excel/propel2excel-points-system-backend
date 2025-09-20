#!/usr/bin/env python3
"""
Script to update existing rewards in the database to match the new requirements.

This script will:
1. Delete the old "Azure Certification" reward
2. Add the new "Azure E-Learning" and "Azure Exam Vouchers" rewards
3. Update the description of "Resume Template Bundle" 
4. Update the description and stock of "1:1 Career Coaching Sessions"
"""

import os
import sys
import django

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import Incentive

def update_rewards():
    """Update the rewards in the database"""
    print("🔄 Updating rewards in the database...")
    
    # 1. Delete the old "Azure Certification" reward
    try:
        old_azure = Incentive.objects.filter(name="Azure Certification").first()
        if old_azure:
            print(f"🗑️ Deleting old reward: {old_azure.name}")
            old_azure.delete()
        else:
            print("ℹ️ No 'Azure Certification' reward found to delete")
    except Exception as e:
        print(f"❌ Error deleting old Azure reward: {e}")
    
    # 2. Create new Azure E-Learning reward
    try:
        azure_elearning, created = Incentive.objects.get_or_create(
            name="Azure E-Learning",
            defaults={
                'description': 'Educational materials and training to gain the necessary knowledge to obtain a certification',
                'points_required': 50,
                'sponsor': 'Microsoft',
                'category': 'digital',
                'stock_available': 999,
                'is_active': True
            }
        )
        if created:
            print(f"✅ Created new reward: {azure_elearning.name}")
        else:
            print(f"ℹ️ Reward already exists: {azure_elearning.name}")
    except Exception as e:
        print(f"❌ Error creating Azure E-Learning reward: {e}")
    
    # 3. Create new Azure Exam Vouchers reward
    try:
        azure_vouchers, created = Incentive.objects.get_or_create(
            name="Azure Exam Vouchers",
            defaults={
                'description': 'Free exam voucher code to sit for your certification exam',
                'points_required': 100,
                'sponsor': 'Microsoft',
                'category': 'digital',
                'stock_available': 50,
                'is_active': True
            }
        )
        if created:
            print(f"✅ Created new reward: {azure_vouchers.name}")
        else:
            print(f"ℹ️ Reward already exists: {azure_vouchers.name}")
    except Exception as e:
        print(f"❌ Error creating Azure Exam Vouchers reward: {e}")
    
    # 4. Update Resume Template Bundle description
    try:
        resume_bundle = Incentive.objects.filter(name="Resume Template Bundle").first()
        if resume_bundle:
            old_desc = resume_bundle.description
            resume_bundle.description = "3 Resumes that landed offers in your company and role of interest"
            resume_bundle.save()
            print(f"✅ Updated Resume Template Bundle description")
            print(f"   Old: {old_desc}")
            print(f"   New: {resume_bundle.description}")
        else:
            print("ℹ️ Resume Template Bundle not found")
    except Exception as e:
        print(f"❌ Error updating Resume Template Bundle: {e}")
    
    # 5. Update 1:1 Career Coaching Sessions description and stock
    try:
        # Try different possible names for this reward
        coaching_names = [
            "1:1 Career Coaching Sessions",
            "1-on-1 Career Coaching Session", 
            "Career Coaching Session"
        ]
        
        coaching_reward = None
        for name in coaching_names:
            coaching_reward = Incentive.objects.filter(name=name).first()
            if coaching_reward:
                break
        
        if coaching_reward:
            old_desc = coaching_reward.description
            old_stock = coaching_reward.stock_available
            
            coaching_reward.description = "Paired up with a volunteered champion who serves as coach to help you land your dream role and company"
            coaching_reward.stock_available = 50
            coaching_reward.save()
            
            print(f"✅ Updated {coaching_reward.name}")
            print(f"   Old description: {old_desc}")
            print(f"   New description: {coaching_reward.description}")
            print(f"   Old stock: {old_stock}")
            print(f"   New stock: {coaching_reward.stock_available}")
        else:
            print("ℹ️ 1:1 Career Coaching Sessions not found")
    except Exception as e:
        print(f"❌ Error updating Career Coaching Sessions: {e}")
    
    # 6. Show final rewards list
    print("\n📋 Final rewards list:")
    all_rewards = Incentive.objects.all().order_by('points_required')
    for reward in all_rewards:
        print(f"  • {reward.name} ({reward.points_required} pts) - Stock: {reward.stock_available}")
        print(f"    Description: {reward.description}")
        print(f"    Category: {reward.category} | Sponsor: {reward.sponsor}")
        print()
    
    print("✅ Reward update completed!")

if __name__ == "__main__":
    update_rewards()
