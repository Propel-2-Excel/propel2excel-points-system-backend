import pandas as pd
from django.core.management.base import BaseCommand
from core.models import DiscordEventLog, PartnerMetrics
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Processes daily Discord event logs and aggregates them into partner metrics.'

    def handle(self, *args, **options):
        yesterday = timezone.now().date() - timedelta(days=1)
        start_of_day = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.datetime.min.time()))
        end_of_day = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.datetime.max.time()))

        self.stdout.write(f"Processing metrics for {yesterday}...")

        # Read logs into a DataFrame
        logs = DiscordEventLog.objects.filter(timestamp__range=(start_of_day, end_of_day))
        if not logs.exists():
            self.stdout.write(self.style.WARNING('No event logs found for yesterday.'))
            return

        df = pd.DataFrame(list(logs.values()))

        # Calculate metrics
        total_active_users = df['user_id'].nunique()
        total_messages_sent = df[df['event_type'] == 'message'].shape[0]

        # Brand Equity Metrics (placeholders)
        brand_mentions_company_a = df[df['event_type'] == 'message']['metadata'].apply(
            lambda x: 'acmecorp' in x.get('content', '').lower() if isinstance(x, dict) else False
        ).sum()
        event_attendees_company_a = 0  # Placeholder

        # Talent Pipeline Metrics (placeholders)
        engaged_students = 0  # Placeholder
        resume_ready_students = 0  # Placeholder
        interview_prepped_students = 0  # Placeholder

        # Save metrics
        PartnerMetrics.objects.update_or_create(
            date=yesterday,
            defaults={
                'total_active_users': total_active_users,
                'total_messages_sent': total_messages_sent,
                'brand_mentions_company_a': brand_mentions_company_a,
                'event_attendees_company_a': event_attendees_company_a,
                'engaged_students': engaged_students,
                'resume_ready_students': resume_ready_students,
                'interview_prepped_students': interview_prepped_students,
            }
        )

        self.stdout.write(self.style.SUCCESS(f"Successfully processed and saved metrics for {yesterday}."))
