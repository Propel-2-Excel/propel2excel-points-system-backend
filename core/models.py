from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    """Extended user model with role-based access"""
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('student', 'Student'),
        ('company', 'Company'),
        ('university', 'University'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    company = models.CharField(max_length=100, blank=True, null=True)
    university = models.CharField(max_length=100, blank=True, null=True)
    discord_id = models.CharField(max_length=50, blank=True, null=True)
    total_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.username} ({self.role})"

class Activity(models.Model):
    """Points-earning activities"""
    ACTIVITY_TYPES = [
        ('resume_upload', 'Resume Upload'),
        ('resume_review_request', 'Resume Review Request'),
        ('event_attendance', 'Event Attendance'),
        ('resource_share', 'Resource Share'),
        ('like_interaction', 'Like/Interaction'),
        ('linkedin_post', 'LinkedIn Post'),
        ('discord_activity', 'Discord Activity'),
    ]
    
    name = models.CharField(max_length=100)
    activity_type = models.CharField(max_length=25, choices=ACTIVITY_TYPES)
    points_value = models.IntegerField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'activities'
        verbose_name_plural = 'Activities'
    
    def __str__(self):
        return f"{self.name} ({self.points_value} pts)"

class PointsLog(models.Model):
    """Log of all points earned by users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='points_logs')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    points_earned = models.IntegerField()
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'points_log'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} earned {self.points_earned} pts for {self.activity.name}"

class Incentive(models.Model):
    """Rewards that students can redeem with points"""
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('unlocked', 'Unlocked'),
        ('redeemed', 'Redeemed'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    points_required = models.IntegerField()
    sponsor = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'incentives'
    
    def __str__(self):
        return f"{self.name} ({self.points_required} pts)"

class Redemption(models.Model):
    """Log of incentive redemptions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='redemptions')
    incentive = models.ForeignKey(Incentive, on_delete=models.CASCADE)
    points_spent = models.IntegerField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='pending')
    admin_notes = models.TextField(blank=True)
    redeemed_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'redemptions'
        ordering = ['-redeemed_at']
    
    def __str__(self):
        return f"{self.user.username} redeemed {self.incentive.name}"

class UserStatus(models.Model):
    """User warnings and suspension tracking"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='status')
    warnings = models.IntegerField(default=0)
    points_suspended = models.BooleanField(default=False)
    suspension_end = models.DateTimeField(blank=True, null=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_status'
        verbose_name_plural = 'User Statuses'
    
    def __str__(self):
        return f"{self.user.username} - {self.warnings} warnings"

class UserIncentiveUnlock(models.Model):
    """Tracks when a user unlocks a given incentive threshold.

    This enables per-user unlock status on the website and allows
    notification deduplication if needed.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unlocked_incentives')
    incentive = models.ForeignKey(Incentive, on_delete=models.CASCADE, related_name='user_unlocks')
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_incentive_unlocks'
        unique_together = ('user', 'incentive')
        ordering = ['-unlocked_at']

    def __str__(self):
        return f"{self.user.username} unlocked {self.incentive.name}"

class DiscordLinkCode(models.Model):
    """One-time code to link a logged-in website user with a Discord account."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discord_link_codes')
    code = models.CharField(max_length=6, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'discord_link_codes'
        indexes = [
            models.Index(fields=['code']),
        ]

    def __str__(self):
        status = 'used' if self.used_at else 'active'
        return f"LinkCode({self.code}) for {self.user.username} [{status}]"

class Professional(models.Model):
    """Professional reviewers for resume review system"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    specialties = models.TextField(help_text="Industries or specializations (e.g., Tech, Finance, Consulting)")
    bio = models.TextField(blank=True, help_text="Professional background and experience")
    availability = models.JSONField(default=dict, help_text="Availability preferences and schedule")
    is_active = models.BooleanField(default=True)
    total_reviews = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, help_text="Average rating from students")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'professionals'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.specialties}"

class ReviewRequest(models.Model):
    """Resume review requests from students"""
    STATUS_CHOICES = [
        ('pending', 'Pending Match'),
        ('matched', 'Matched with Professional'),
        ('scheduled', 'Review Scheduled'),
        ('completed', 'Review Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_requests')
    professional = models.ForeignKey(Professional, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_reviews')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Form submission data
    form_data = models.JSONField(default=dict, help_text="Data from Google Form submission")
    target_industry = models.CharField(max_length=100, blank=True)
    target_role = models.CharField(max_length=100, blank=True)
    experience_level = models.CharField(max_length=50, blank=True)
    
    # Scheduling
    preferred_times = models.JSONField(default=list, help_text="Student's preferred time slots")
    scheduled_time = models.DateTimeField(null=True, blank=True)
    session_duration = models.IntegerField(default=30, help_text="Duration in minutes")
    
    # Review details
    review_notes = models.TextField(blank=True, help_text="Professional's feedback notes")
    student_feedback = models.TextField(blank=True, help_text="Student's feedback about the review")
    rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)], help_text="Student rating (1-5)")
    
    # Timestamps
    submission_date = models.DateTimeField(auto_now_add=True)
    matched_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Admin notes
    admin_notes = models.TextField(blank=True)

    class Meta:
        db_table = 'review_requests'
        ordering = ['-submission_date']

    def __str__(self):
        professional_name = self.professional.name if self.professional else "Unassigned"
        return f"{self.student.username} - {professional_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Update timestamps based on status changes
        if self.pk:  # Only for updates, not new records
            old_instance = ReviewRequest.objects.get(pk=self.pk)
            if old_instance.status != self.status:
                if self.status == 'matched' and not self.matched_date:
                    self.matched_date = timezone.now()
                elif self.status == 'completed' and not self.completed_date:
                    self.completed_date = timezone.now()
                    # Update professional's total reviews
                    if self.professional:
                        self.professional.total_reviews += 1
                        self.professional.save()
        super().save(*args, **kwargs)
