from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Activity, PointsLog, Incentive, Redemption, UserStatus

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
