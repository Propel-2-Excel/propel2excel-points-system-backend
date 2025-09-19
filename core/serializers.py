from rest_framework import serializers
from .models import User, Track, Activity, PointsLog, Incentive, Redemption, UserStatus, UserIncentiveUnlock, DiscordLinkCode, Professional, ReviewRequest, ScheduledSession, ProfessionalAvailability, UserPreferences, PartnerMetrics

class TrackSerializer(serializers.ModelSerializer):
    """Serializer for Track model"""
    
    class Meta:
        model = Track
        fields = ['id', 'name', 'display_name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    track_info = TrackSerializer(source='track', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'track', 'track_info', 'company', 'university', 'major', 'graduation_year', 'display_name',
            'discord_id', 'total_points', 'created_at', 'updated_at', 'password',
            
            # Discord verification fields
            'discord_username_unverified', 'discord_verified', 'discord_verified_at',
            
            # Media consent fields
            'media_consent', 'media_consent_date', 'media_consent_ip',
            'media_consent_user_agent', 'onboarding_completed', 'onboarding_completed_date'
        ]
        read_only_fields = [
            'id', 'total_points', 'created_at', 'updated_at', 'discord_verified', 'discord_verified_at',
            'media_consent_date', 'media_consent_ip', 'media_consent_user_agent', 'onboarding_completed_date',
            'track_info'
        ]
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

class ActivitySerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Activity
        fields = '__all__'

class PointsLogSerializer(serializers.ModelSerializer):
    activity_name = serializers.CharField(source='activity.name', read_only=True)
    activity_category = serializers.CharField(source='activity.category', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = PointsLog
        fields = [
            'id', 'user', 'user_username', 'activity', 'activity_name', 'activity_category',
            'points_earned', 'details', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']

class IncentiveSerializer(serializers.ModelSerializer):
    is_unlocked = serializers.SerializerMethodField()
    unlocked_at = serializers.SerializerMethodField()
    can_redeem = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Incentive
        fields = '__all__'
        read_only_fields = ['is_unlocked', 'unlocked_at', 'can_redeem']

    def get_is_unlocked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        # Fallback to current total points to ensure UI reflects reality even if
        # an unlock row hasn't been created yet.
        if getattr(request.user, 'total_points', 0) >= obj.points_required:
            return True
        return UserIncentiveUnlock.objects.filter(user=request.user, incentive=obj).exists()

    def get_unlocked_at(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        uiu = UserIncentiveUnlock.objects.filter(user=request.user, incentive=obj).first()
        return uiu.unlocked_at if uiu else None
    
    def get_can_redeem(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return (getattr(request.user, 'total_points', 0) >= obj.points_required and 
                obj.is_active and obj.stock_available > 0)

class RedemptionSerializer(serializers.ModelSerializer):
    incentive_name = serializers.CharField(source='incentive.name', read_only=True)
    incentive_image_url = serializers.URLField(source='incentive.image_url', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Redemption
        fields = [
            'id', 'user', 'user_username', 'incentive', 'incentive_name', 'incentive_image_url',
            'points_spent', 'status', 'status_display', 'delivery_details', 'tracking_info',
            'estimated_delivery', 'admin_notes', 'redeemed_at', 'processed_at'
        ]
        read_only_fields = ['id', 'redeemed_at', 'processed_at', 'status_display']

class UserStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserStatus
        fields = [
            'id', 'user', 'user_username', 'warnings',
            'points_suspended', 'suspension_end', 'last_activity'
        ]
        read_only_fields = ['id', 'last_activity'] 


class DiscordLinkCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscordLinkCode
        fields = ['code', 'expires_at', 'used_at']
        read_only_fields = fields

class ProfessionalSerializer(serializers.ModelSerializer):
    review_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Professional
        fields = [
            'id', 'name', 'email', 'specialties', 'bio', 'availability',
            'is_active', 'total_reviews', 'rating', 'review_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total_reviews', 'rating', 'created_at', 'updated_at']
    
    def get_review_count(self, obj):
        return obj.assigned_reviews.filter(status='completed').count()

class ReviewRequestSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    professional_name = serializers.CharField(source='professional.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    days_since_submission = serializers.SerializerMethodField()
    
    class Meta:
        model = ReviewRequest
        fields = [
            'id', 'student', 'student_username', 'professional', 'professional_name',
            'status', 'status_display', 'priority', 'priority_display',
            'form_data', 'target_industry', 'target_role', 'experience_level',
            'preferred_times', 'scheduled_time', 'session_duration',
            'review_notes', 'student_feedback', 'rating',
            'submission_date', 'matched_date', 'completed_date',
            'admin_notes', 'days_since_submission'
        ]
        read_only_fields = [
            'id', 'submission_date', 'matched_date', 'completed_date',
            'student_username', 'professional_name', 'status_display', 
            'priority_display', 'days_since_submission'
        ]
    
    def get_days_since_submission(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.submission_date
        return delta.days

class ReviewRequestCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating review requests via Discord bot"""
    
    class Meta:
        model = ReviewRequest
        fields = [
            'student', 'target_industry', 'target_role', 'experience_level',
            'preferred_times', 'priority', 'form_data', 'admin_notes'
        ]

class ScheduledSessionSerializer(serializers.ModelSerializer):
    student_username = serializers.CharField(source='student.username', read_only=True)
    professional_name = serializers.CharField(source='professional.name', read_only=True)
    review_request_id = serializers.IntegerField(source='review_request.id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ScheduledSession
        fields = [
            'id', 'review_request', 'review_request_id', 'student', 'student_username',
            'professional', 'professional_name', 'scheduled_time', 'duration_minutes',
            'meeting_link', 'calendar_event_id', 'status', 'status_display',
            'admin_notes', 'session_notes', 'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'student_username', 'professional_name',
            'review_request_id', 'status_display'
        ]

class ProfessionalAvailabilitySerializer(serializers.ModelSerializer):
    professional_name = serializers.CharField(source='professional.name', read_only=True)
    days_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = ProfessionalAvailability
        fields = [
            'id', 'professional', 'professional_name', 'form_response_id',
            'form_data', 'availability_slots', 'preferred_days', 'time_zone',
            'start_date', 'end_date', 'submission_date', 'is_active',
            'notes', 'days_valid'
        ]
        read_only_fields = [
            'id', 'submission_date', 'professional_name', 'days_valid'
        ]
    
    def get_days_valid(self, obj):
        from django.utils import timezone
        if not obj.is_active:
            return 0
        today = timezone.now().date()
        if today > obj.end_date:
            return 0
        return (obj.end_date - max(today, obj.start_date)).days

class DiscordValidationSerializer(serializers.Serializer):
    """Serializer for Discord username validation requests"""
    discord_username = serializers.CharField(
        max_length=50, 
        help_text="Discord username with discriminator (e.g., JaneDoe#1234)"
    )
    
    def validate_discord_username(self, value):
        """Validate Discord username format"""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Discord username cannot be empty")
        
        # Basic validation - Discord usernames can have various formats
        # We'll let the bot do the actual server membership validation
        if len(value) < 2:
            raise serializers.ValidationError("Discord username too short")
        
        return value

class DiscordValidationResponseSerializer(serializers.Serializer):
    """Serializer for Discord validation responses"""
    valid = serializers.BooleanField()
    message = serializers.CharField(max_length=200)
    discord_username = serializers.CharField(max_length=50)
    discord_id = serializers.CharField(max_length=50, required=False)

class UserPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for user preferences"""
    
    class Meta:
        model = UserPreferences
        fields = [
            'id', 'user', 'email_notifications', 'privacy_settings',
            'display_preferences', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class PartnerMetricsSerializer(serializers.ModelSerializer):
    """Serializer for the PartnerMetrics model."""
    class Meta:
        model = PartnerMetrics
        fields = '__all__'