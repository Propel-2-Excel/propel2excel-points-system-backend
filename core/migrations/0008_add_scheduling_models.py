# Generated migration for scheduling models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_add_media_consent_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfessionalAvailability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('form_response_id', models.CharField(help_text='Google Form response ID', max_length=255, unique=True)),
                ('form_data', models.JSONField(default=dict, help_text='Complete form response data')),
                ('availability_slots', models.JSONField(default=list, help_text='Parsed availability time slots')),
                ('preferred_days', models.JSONField(default=list, help_text='Preferred days of week')),
                ('time_zone', models.CharField(default='UTC', help_text="Professional's timezone", max_length=50)),
                ('start_date', models.DateField(help_text='Start of availability period')),
                ('end_date', models.DateField(help_text='End of availability period')),
                ('submission_date', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('notes', models.TextField(blank=True, help_text='Additional notes from professional')),
                ('professional', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='availability_responses', to='core.professional')),
            ],
            options={
                'db_table': 'professional_availability',
                'ordering': ['-submission_date'],
            },
        ),
        migrations.CreateModel(
            name='ScheduledSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduled_time', models.DateTimeField(help_text='Scheduled meeting time')),
                ('duration_minutes', models.IntegerField(default=30, help_text='Session duration in minutes')),
                ('meeting_link', models.URLField(blank=True, help_text='Video call link (Zoom, Google Meet, etc.)')),
                ('calendar_event_id', models.CharField(blank=True, help_text='Google Calendar event ID', max_length=255)),
                ('status', models.CharField(choices=[('scheduled', 'Scheduled'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('no_show', 'No Show')], default='scheduled', max_length=20)),
                ('admin_notes', models.TextField(blank=True, help_text='Admin notes about the session')),
                ('session_notes', models.TextField(blank=True, help_text='Notes from the actual session')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('professional', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='professional_sessions', to='core.professional')),
                ('review_request', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='scheduled_session', to='core.reviewrequest')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_sessions', to='core.user')),
            ],
            options={
                'db_table': 'scheduled_sessions',
                'ordering': ['-scheduled_time'],
            },
        ),
    ]
