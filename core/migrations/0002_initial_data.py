from django.db import migrations

def create_initial_data(apps, schema_editor):
    Activity = apps.get_model('core', 'Activity')
    Incentive = apps.get_model('core', 'Incentive')
    
    # Create initial activities
    activities = [
        {
            'name': 'Resume Upload',
            'activity_type': 'resume_upload',
            'points_value': 20,
            'description': 'Upload your resume to the platform'
        },
        {
            'name': 'Event Attendance',
            'activity_type': 'event_attendance',
            'points_value': 15,
            'description': 'Attend a Propel2Excel event'
        },
        {
            'name': 'Resource Share',
            'activity_type': 'resource_share',
            'points_value': 10,
            'description': 'Share a valuable resource with the community'
        },
        {
            'name': 'Like/Interaction',
            'activity_type': 'like_interaction',
            'points_value': 2,
            'description': 'Like or interact with community content'
        },
        {
            'name': 'LinkedIn Post',
            'activity_type': 'linkedin_post',
            'points_value': 5,
            'description': 'Post about Propel2Excel on LinkedIn'
        },
        {
            'name': 'Discord Activity',
            'activity_type': 'discord_activity',
            'points_value': 5,
            'description': 'Active participation in Discord community'
        }
    ]
    
    for activity_data in activities:
        Activity.objects.get_or_create(
            activity_type=activity_data['activity_type'],
            defaults=activity_data
        )
    
    # Create initial incentives
    incentives = [
        {
            'name': 'Azure E-Learning',
            'description': 'Educational materials and training to gain the necessary knowledge to obtain a certification',
            'points_required': 50,
            'sponsor': 'Microsoft',
            'stock_available': 999
        },
        {
            'name': 'Azure Exam Vouchers',
            'description': 'Free exam voucher code to sit for your certification exam',
            'points_required': 100,
            'sponsor': 'Microsoft',
            'stock_available': 50
        },
        {
            'name': 'Resume Template Bundle',
            'description': '3 Resumes that landed offers in your company and role of interest',
            'points_required': 150,
            'sponsor': 'P2E Resources',
            'stock_available': 999
        },
        {
            'name': '1:1 Career Coaching Sessions',
            'description': 'Paired up with a volunteered champion who serves as coach to help you land your dream role and company',
            'points_required': 500,
            'sponsor': 'P2E Career Services',
            'stock_available': 50
        }
    ]
    
    for incentive_data in incentives:
        Incentive.objects.get_or_create(
            name=incentive_data['name'],
            defaults=incentive_data
        )

def reverse_initial_data(apps, schema_editor):
    Activity = apps.get_model('core', 'Activity')
    Incentive = apps.get_model('core', 'Incentive')
    
    Activity.objects.all().delete()
    Incentive.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_initial_data, reverse_initial_data),
    ] 