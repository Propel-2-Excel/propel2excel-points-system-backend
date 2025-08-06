from rest_framework import serializers
from .models import User, Activity, PointsLog, Incentive, Redemption, UserStatus

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
    class Meta:
        model = Incentive
        fields = '__all__'

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