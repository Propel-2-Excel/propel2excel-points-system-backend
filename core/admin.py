from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Activity, PointsLog, Incentive, Redemption, UserStatus, Professional, ReviewRequest

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'company', 'university', 'total_points', 'created_at']
    list_filter = ['role', 'company', 'university', 'created_at']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Propel2Excel Info', {
            'fields': ('role', 'company', 'university', 'discord_id', 'total_points')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Propel2Excel Info', {
            'fields': ('role', 'company', 'university', 'discord_id')
        }),
    )

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['name', 'activity_type', 'points_value', 'is_active', 'created_at']
    list_filter = ['activity_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['activity_type', 'points_value']

@admin.register(PointsLog)
class PointsLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity', 'points_earned', 'timestamp']
    list_filter = ['activity', 'timestamp']
    search_fields = ['user__username', 'activity__name', 'details']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']

@admin.register(Incentive)
class IncentiveAdmin(admin.ModelAdmin):
    list_display = ['name', 'points_required', 'sponsor', 'status', 'is_active', 'created_at']
    list_filter = ['status', 'is_active', 'sponsor', 'created_at']
    search_fields = ['name', 'description', 'sponsor']
    ordering = ['points_required']

@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'incentive', 'points_spent', 'status', 'redeemed_at', 'processed_at']
    list_filter = ['status', 'incentive', 'redeemed_at']
    search_fields = ['user__username', 'incentive__name', 'admin_notes']
    ordering = ['-redeemed_at']
    readonly_fields = ['redeemed_at']
    
    actions = ['approve_redemptions', 'reject_redemptions']
    
    def approve_redemptions(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='approved', processed_at=timezone.now())
        self.message_user(request, f'{updated} redemptions approved.')
    approve_redemptions.short_description = "Approve selected redemptions"
    
    def reject_redemptions(self, request, queryset):
        from django.utils import timezone
        from django.db import transaction
        
        with transaction.atomic():
            for redemption in queryset:
                # Refund points
                user = redemption.user
                user.total_points += redemption.points_spent
                user.save()
                
                # Update redemption
                redemption.status = 'rejected'
                redemption.processed_at = timezone.now()
                redemption.save()
        
        self.message_user(request, f'{queryset.count()} redemptions rejected and points refunded.')
    reject_redemptions.short_description = "Reject selected redemptions and refund points"

@admin.register(UserStatus)
class UserStatusAdmin(admin.ModelAdmin):
    list_display = ['user', 'warnings', 'points_suspended', 'suspension_end', 'last_activity']
    list_filter = ['points_suspended', 'warnings', 'last_activity']
    search_fields = ['user__username']
    ordering = ['-last_activity']
    readonly_fields = ['last_activity']

@admin.register(Professional)
class ProfessionalAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'specialties', 'total_reviews', 'rating', 'is_active', 'created_at']
    list_filter = ['is_active', 'specialties', 'created_at']
    search_fields = ['name', 'email', 'specialties', 'bio']
    ordering = ['name']
    readonly_fields = ['total_reviews', 'rating', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'specialties', 'bio')
        }),
        ('Status & Stats', {
            'fields': ('is_active', 'total_reviews', 'rating')
        }),
        ('Availability', {
            'fields': ('availability',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ReviewRequest)
class ReviewRequestAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'professional', 'status', 'priority', 'target_industry', 
        'target_role', 'submission_date', 'matched_date', 'completed_date'
    ]
    list_filter = [
        'status', 'priority', 'target_industry', 'experience_level',
        'submission_date', 'matched_date', 'completed_date'
    ]
    search_fields = [
        'student__username', 'student__email', 'professional__name',
        'target_industry', 'target_role', 'admin_notes'
    ]
    ordering = ['-submission_date']
    readonly_fields = ['submission_date', 'matched_date', 'completed_date']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('student', 'status', 'priority', 'professional')
        }),
        ('Student Details', {
            'fields': ('target_industry', 'target_role', 'experience_level')
        }),
        ('Scheduling', {
            'fields': ('preferred_times', 'scheduled_time', 'session_duration'),
            'classes': ('collapse',)
        }),
        ('Review Details', {
            'fields': ('review_notes', 'student_feedback', 'rating'),
            'classes': ('collapse',)
        }),
        ('Form Data', {
            'fields': ('form_data',),
            'classes': ('collapse',)
        }),
        ('Admin', {
            'fields': ('admin_notes',)
        }),
        ('Timestamps', {
            'fields': ('submission_date', 'matched_date', 'completed_date'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['assign_to_professional', 'mark_as_completed', 'cancel_requests']
    
    def assign_to_professional(self, request, queryset):
        """Custom action to assign multiple requests to a professional"""
        # This would need additional form handling in a real implementation
        updated = queryset.filter(status='pending').update(status='matched')
        self.message_user(request, f'{updated} review requests marked as matched.')
    assign_to_professional.short_description = "Mark selected requests as matched"
    
    def mark_as_completed(self, request, queryset):
        """Custom action to mark requests as completed"""
        from django.utils import timezone
        updated = queryset.filter(status__in=['matched', 'scheduled']).update(
            status='completed',
            completed_date=timezone.now()
        )
        self.message_user(request, f'{updated} review requests marked as completed.')
    mark_as_completed.short_description = "Mark selected requests as completed"
    
    def cancel_requests(self, request, queryset):
        """Custom action to cancel requests"""
        updated = queryset.filter(status__in=['pending', 'matched']).update(status='cancelled')
        self.message_user(request, f'{updated} review requests cancelled.')
    cancel_requests.short_description = "Cancel selected requests"
