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
            'name': 'Azure Certification',
            'description': 'Free Azure certification voucher',
            'points_required': 50,
            'sponsor': 'Microsoft'
        },
        {
            'name': 'Hackathon Entry',
            'description': 'Exclusive hackathon entry opportunity',
            'points_required': 100,
            'sponsor': 'Propel2Excel'
        },
        {
            'name': 'Resume Review',
            'description': 'Professional resume review by industry expert',
            'points_required': 75,
            'sponsor': 'Career Services'
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