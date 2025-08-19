from rest_framework import serializers
from .models import User, Activity, PointsLog, Incentive, Redemption, UserStatus, UserIncentiveUnlock, DiscordLinkCode, Professional, ReviewRequest

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'company', 'university', 'discord_id',
            'total_points', 'created_at', 'updated_at', 'password'
        ]
        read_only_fields = ['id', 'total_points', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = '__all__'

class PointsLogSerializer(serializers.ModelSerializer):
    activity_name = serializers.CharField(source='activity.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = PointsLog
        fields = [
            'id', 'user', 'user_username', 'activity', 'activity_name',
            'points_earned', 'details', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']

class IncentiveSerializer(serializers.ModelSerializer):
    is_unlocked = serializers.SerializerMethodField()
    unlocked_at = serializers.SerializerMethodField()
    class Meta:
        model = Incentive
        fields = '__all__'
        read_only_fields = ['is_unlocked', 'unlocked_at']

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

class RedemptionSerializer(serializers.ModelSerializer):
    incentive_name = serializers.CharField(source='incentive.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Redemption
        fields = [
            'id', 'user', 'user_username', 'incentive', 'incentive_name',
            'points_spent', 'status', 'admin_notes', 'redeemed_at', 'processed_at'
        ]
        read_only_fields = ['id', 'redeemed_at', 'processed_at']

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