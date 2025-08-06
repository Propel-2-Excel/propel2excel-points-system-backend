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
        ('event_attendance', 'Event Attendance'),
        ('resource_share', 'Resource Share'),
        ('like_interaction', 'Like/Interaction'),
        ('linkedin_post', 'LinkedIn Post'),
        ('discord_activity', 'Discord Activity'),
    ]
    
    name = models.CharField(max_length=100)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
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
