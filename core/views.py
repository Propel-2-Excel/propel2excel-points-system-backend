from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import transaction, models
from django.utils import timezone
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
import logging
import requests

logger = logging.getLogger(__name__)
from .models import User, Track, Activity, PointsLog, Incentive, Redemption, UserStatus, UserIncentiveUnlock, DiscordLinkCode, Professional, ReviewRequest, ScheduledSession, ProfessionalAvailability, ResourceSubmission, EventSubmission, LinkedInSubmission, UserPreferences
from .serializers import (
    UserSerializer, TrackSerializer, ActivitySerializer, PointsLogSerializer,
    IncentiveSerializer, RedemptionSerializer, UserStatusSerializer, DiscordLinkCodeSerializer,
    ProfessionalSerializer, ReviewRequestSerializer, ReviewRequestCreateSerializer,
    ScheduledSessionSerializer, ProfessionalAvailabilitySerializer,
    DiscordValidationSerializer, DiscordValidationResponseSerializer, UserPreferencesSerializer
)

def invalidate_user_caches(user_id):
    """
    Invalidate all cached data for a specific user when their points/activities change.
    This ensures users see updated data immediately after activities are added.
    
    Args:
        user_id: The ID of the user whose caches should be invalidated
    """
    try:
        logger.info(f"🔥 CACHE INVALIDATION START for user {user_id}")
        
        # Count successful deletions for debugging
        deleted_count = 0
        
        # Activity-related caches - these change most frequently
        keys_to_delete = [
            f"activity_feed_{user_id}_lifetime",
            f"points_history_{user_id}_lifetime",
            f"rewards_available_{user_id}",
        ]
        
        # Dashboard stats caches - invalidate all periods
        for period in ['7days', '30days', '90days']:
            keys_to_delete.append(f"dashboard_stats_{user_id}_{period}")
        
        # Points timeline caches - invalidate common configurations
        for granularity in ['daily', 'weekly', 'monthly']:
            for days in [7, 30, 90, 365]:
                keys_to_delete.append(f"points_timeline_{user_id}_{granularity}_{days}")
        
        # Limited/paginated caches - invalidate common limits
        common_limits = [10, 20, 50, 100, 500, 1000]
        for limit in common_limits:
            keys_to_delete.append(f"activity_feed_{user_id}_{limit}")
            keys_to_delete.append(f"points_history_{user_id}_{limit}")
        
        # Leaderboard caches - invalidate for all periods and common limits
        leaderboard_periods = ['all_time', 'weekly', 'monthly']
        leaderboard_limits = [10, 20, 50, 100]
        for period in leaderboard_periods:
            for limit in leaderboard_limits:
                keys_to_delete.append(f"leaderboard_{period}_{limit}_{user_id}")
        
        # Delete all keys and count successes
        for key in keys_to_delete:
            if cache.delete(key):
                deleted_count += 1
                logger.info(f"✅ Deleted cache key: {key}")
            else:
                logger.info(f"⚪ Cache key not found (already expired): {key}")
        
        logger.info(f"🎉 CACHE INVALIDATION COMPLETED for user {user_id} - Deleted {deleted_count}/{len(keys_to_delete)} keys")
        
    except Exception as e:
        logger.error(f"❌ CACHE INVALIDATION FAILED for user {user_id}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Don't re-raise the exception to avoid breaking the main flow

class TrackViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for managing career tracks"""
    queryset = Track.objects.filter(is_active=True)
    serializer_class = TrackSerializer
    permission_classes = [permissions.AllowAny]  # Allow anyone to view tracks
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active tracks"""
        tracks = self.get_queryset()
        serializer = self.get_serializer(tracks, many=True)
        return Response(serializer.data)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        """Register a new user with Discord verification required"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data.get('password'))
            
            # Store UNVERIFIED Discord information (security: don't auto-link!)
            discord_data = request.data.get('discord_data', {})
            if discord_data.get('discord_username'):
                user.discord_username_unverified = discord_data.get('discord_username')
                logger.info(f"New user {user.username} registered with unverified Discord: {user.discord_username_unverified}")
            
            user.save()
            
            # Create user status
            UserStatus.objects.create(user=user)
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            response_data = {
                'user': serializer.data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }
            
            # Include Discord verification status
            if user.discord_username_unverified:
                response_data['discord_verification_required'] = True
                response_data['discord_username_pending'] = user.discord_username_unverified
                response_data['message'] = f'Account created! Please verify your Discord account "{user.discord_username_unverified}" using the bot to enable Discord features.'
            else:
                response_data['discord_verification_required'] = False
                response_data['message'] = 'Account created! You can link Discord later in your profile.'
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        # Return detailed error messages for better UX
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        """Login user"""
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            serializer = self.get_serializer(user)
            return Response({
                'user': serializer.data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            })
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=['get', 'put'])
    def profile(self, request):
        """Get or update current user profile"""
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        
        elif request.method == 'PUT':
            # Update user profile
            user = request.user
            serializer = self.get_serializer(user, data=request.data, partial=True)
            
            if serializer.is_valid():
                # Update media consent tracking if consent is being updated
                if 'media_consent' in request.data and request.data['media_consent'] != user.media_consent:
                    serializer.validated_data['media_consent_date'] = timezone.now()
                    serializer.validated_data['media_consent_ip'] = request.META.get('REMOTE_ADDR')
                    serializer.validated_data['media_consent_user_agent'] = request.META.get('HTTP_USER_AGENT', '')
                
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'Profile updated successfully',
                    'data': serializer.data
                })
            
            return Response({
                'success': False,
                'message': 'Profile update failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def consent(self, request):
        """Update user's media consent status"""
        try:
            user = request.user
            media_consent = request.data.get('media_consent')
            
            if media_consent is None:
                return Response({
                    'error': 'media_consent field is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update consent fields
            user.media_consent = media_consent
            user.media_consent_date = timezone.now()
            user.media_consent_ip = request.META.get('REMOTE_ADDR')
            user.media_consent_user_agent = request.META.get('HTTP_USER_AGENT', '')
            user.save()
            
            return Response({
                'success': True,
                'message': 'Consent status updated successfully',
                'data': {
                    'media_consent': user.media_consent,
                    'media_consent_date': user.media_consent_date.isoformat(),
                    'onboarding_step': 'consent_completed'
                }
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """Change user password with Discord verification"""
        try:
            user = request.user
            current_password = request.data.get('current_password')
            new_password = request.data.get('new_password')
            discord_id = request.data.get('discord_id')
            
            # Validate required fields
            if not current_password or not new_password:
                return Response({
                    'error': 'Both current_password and new_password are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify current password
            if not user.check_password(current_password):
                return Response({
                    'error': 'Current password is incorrect'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # For Discord-linked accounts, verify Discord ID
            if user.discord_id and user.discord_verified:
                if not discord_id or discord_id != user.discord_id:
                    return Response({
                        'error': 'Discord ID verification required for password change'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate new password (basic validation)
            if len(new_password) < 8:
                return Response({
                    'error': 'New password must be at least 8 characters long'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update password
            user.set_password(new_password)
            user.save()
            
            return Response({
                'success': True,
                'message': 'Password changed successfully'
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def discord_verification(self, request):
        """Get Discord verification status"""
        user = request.user
        
        return Response({
            'discord_linked': bool(user.discord_id and user.discord_verified),
            'discord_id': user.discord_id if user.discord_verified else None,
            'discord_username': user.discord_username_unverified if not user.discord_verified else None,
            'discord_verified': user.discord_verified,
            'discord_verified_at': user.discord_verified_at.isoformat() if user.discord_verified_at else None,
            'verification_required': bool(user.discord_username_unverified and not user.discord_verified)
        })
    
    @action(detail=False, methods=['post'])
    def complete_onboarding(self, request):
        """Mark user's onboarding as complete"""
        try:
            user = request.user
            
            # Mark onboarding as complete
            user.onboarding_completed = True
            user.onboarding_completed_date = timezone.now()
            user.save()
            
            return Response({
                'success': True,
                'message': 'Onboarding marked as complete',
                'data': {
                    'onboarding_completed': user.onboarding_completed,
                    'completion_date': user.onboarding_completed_date.isoformat()
                }
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def add_points(self, request, pk=None):
        """Add points to a user for an activity"""
        user = self.get_object()
        activity_type = request.data.get('activity_type')
        details = request.data.get('details', '')
        
        try:
            activity = Activity.objects.get(activity_type=activity_type, is_active=True)
            
            with transaction.atomic():
                # Create points log entry
                points_log = PointsLog.objects.create(
                    user=user,
                    activity=activity,
                    points_earned=activity.points_value,
                    details=details
                )
                
                # Update user's total points
                user.total_points += activity.points_value
                user.save()
                
            # Update user status last activity
            user_status, created = UserStatus.objects.get_or_create(user=user)
            user_status.last_activity = timezone.now()
            user_status.save()
        
            # CACHE INVALIDATION: Clear user's cached data after transaction commits
            # This ensures immediate updates in the frontend
            invalidate_user_caches(user.id)
            
            return Response({
                'message': f'Added {activity.points_value} points for {activity.name}',
                'total_points': user.total_points,
                'points_log': PointsLogSerializer(points_log).data
            })
            
        except Activity.DoesNotExist:
            return Response({'error': 'Activity not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['patch'])
    def update_track(self, request, pk=None):
        """Update a user's career track"""
        user = self.get_object()
        
        # Users can only update their own track, or admins can update any
        if user != request.user and request.user.role != 'admin':
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        track_id = request.data.get('track_id')
        if track_id is None:
            return Response({'error': 'track_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if track_id == '' or track_id is None:
                # Remove track
                user.track = None
                user.save()
                return Response({
                    'message': 'Track removed successfully',
                    'user': UserSerializer(user).data
                })
            else:
                # Set track
                track = Track.objects.get(id=track_id, is_active=True)
                user.track = track
                user.save()
                return Response({
                    'message': f'Track updated to {track.display_name}',
                    'user': UserSerializer(user).data
                })
        except Track.DoesNotExist:
            return Response({'error': 'Track not found'}, status=status.HTTP_404_NOT_FOUND)

class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Activity.objects.filter(is_active=True)
    serializer_class = ActivitySerializer
    permission_classes = [permissions.AllowAny]

class PointsLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PointsLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """HIGHLY OPTIMIZED: Users can only see their own points logs"""
        # CRITICAL PERFORMANCE OPTIMIZATION
        # Uses indexes: idx_points_logs_user_timestamp, idx_points_logs_user_activity
        base_queryset = PointsLog.objects.select_related(
            'activity',  # Prevent N+1 queries for activity data
            'user'       # Prevent N+1 queries for user data
        ).prefetch_related(
            'activity__category'  # If activity has category relationships
        )
        
        if self.request.user.role == 'admin':
            queryset = base_queryset.all()
        else:
            # OPTIMIZED: Uses idx_points_logs_user_timestamp index
            queryset = base_queryset.filter(user=self.request.user)
        
        # FLEXIBLE LIMITING: Optional pagination for lifetime data access
        # No limit specified = full lifetime data
        # With limit = performance optimization for recent data
        limit_param = self.request.GET.get('limit')
        if limit_param:
            limit = min(int(limit_param), 1000)  # Higher cap for lifetime view
            return queryset.order_by('-timestamp')[:limit]
        else:
            # No limit = full lifetime data (complete earnings history)
            return queryset.order_by('-timestamp')
    
    def list(self, request):
        """SUPER OPTIMIZED with CACHING: Use values() for API responses to reduce data transfer"""
        # CACHING: Check for cached data first
        limit_param = request.GET.get('limit')
        if limit_param:
            limit = min(int(limit_param), 1000)
            cache_key = f"points_history_{request.user.id}_{limit}"
        else:
            limit = None
            cache_key = f"points_history_{request.user.id}_lifetime"
        
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        queryset = self.get_queryset()
        
        # PERFORMANCE: Only fetch needed fields, reduce memory usage
        optimized_data = queryset.values(
            'id', 'points_earned', 'timestamp', 'details',
            'activity__name', 'activity__category', 'activity__points_value'
        )
        
        # Convert to list and format timestamps
        formatted_data = []
        for item in optimized_data:
            formatted_item = dict(item)
            formatted_item['timestamp'] = item['timestamp'].isoformat()
            formatted_data.append(formatted_item)
        
        response_data = {
            'count': len(formatted_data),
            'results': formatted_data,
            'is_lifetime_data': limit is None,
            'limit_applied': limit
        }
        
        # CACHE: Store results for 24 hours (86400 seconds) - Points history with cache invalidation
        # Long TTL since cache invalidation handles real-time updates
        cache.set(cache_key, response_data, 86400)
        
        return Response(response_data)

class IncentiveViewSet(viewsets.ModelViewSet):
    queryset = Incentive.objects.all()
    serializer_class = IncentiveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter based on user role and action"""
        if self.action == 'list' and not self.request.user.is_authenticated:
            # Public access for listing - only show active incentives
            return Incentive.objects.filter(is_active=True)
        elif self.request.user.role == 'admin':
            # Admins can see all incentives
            return Incentive.objects.all()
        else:
            # Regular users can only see active incentives
            return Incentive.objects.filter(is_active=True)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def perform_create(self, serializer):
        """Only admins can create incentives"""
        if self.request.user.role != 'admin':
            raise permissions.PermissionDenied("Only admins can create incentives")
        serializer.save()

    def perform_update(self, serializer):
        """Only admins can update incentives"""
        if self.request.user.role != 'admin':
            raise permissions.PermissionDenied("Only admins can update incentives")
        serializer.save()

    def perform_destroy(self, instance):
        """Only admins can delete incentives"""
        if self.request.user.role != 'admin':
            raise permissions.PermissionDenied("Only admins can delete incentives")
        instance.delete()

    @action(detail=True, methods=['post'])
    def toggle_availability(self, request, pk=None):
        """Toggle incentive availability (admin only)"""
        if request.user.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        incentive = self.get_object()
        incentive.is_active = not incentive.is_active
        incentive.save()
        
        # Clear cache for all users since rewards changed
        from django.core.cache import cache
        cache.delete_many(cache.keys('rewards_available_*'))
        
        return Response({
            'success': True,
            'incentive_id': incentive.id,
            'name': incentive.name,
            'is_active': incentive.is_active,
            'message': f'Incentive "{incentive.name}" is now {"available" if incentive.is_active else "unavailable"}'
        })

    @action(detail=False, methods=['get'])
    def admin_list(self, request):
        """Get all incentives for admin management"""
        if request.user.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        incentives = Incentive.objects.all().order_by('points_required')
        serializer = self.get_serializer(incentives, many=True)
        return Response(serializer.data)

class RedemptionViewSet(viewsets.ModelViewSet):
    serializer_class = RedemptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own redemptions, admins see all"""
        if self.request.user.role == 'admin':
            return Redemption.objects.all()
        return Redemption.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def redeem(self, request):
        """Redeem an incentive"""
        incentive_id = request.data.get('incentive_id')
        
        try:
            incentive = Incentive.objects.get(id=incentive_id, is_active=True)
            user = request.user
            
            # Check if user has enough points
            if user.total_points < incentive.points_required:
                return Response({
                    'error': f'Insufficient points. Required: {incentive.points_required}, Available: {user.total_points}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                # Create redemption
                redemption = Redemption.objects.create(
                    user=user,
                    incentive=incentive,
                    points_spent=incentive.points_required
                )
                
                # Deduct points from user
                user.total_points -= incentive.points_required
                user.save()
            
            return Response({
                'message': f'Successfully redeemed {incentive.name}',
                'redemption': RedemptionSerializer(redemption).data,
                'remaining_points': user.total_points
            })
            
        except Incentive.DoesNotExist:
            return Response({'error': 'Incentive not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a redemption (admin only)"""
        if request.user.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        redemption = self.get_object()
        redemption.status = 'approved'
        redemption.processed_at = timezone.now()
        redemption.admin_notes = request.data.get('notes', '')
        redemption.save()
        
        # CACHE INVALIDATION: Clear user's cached data after redemption status change
        # This ensures immediate updates in the frontend
        invalidate_user_caches(redemption.user.id)
        
        return Response({'message': 'Redemption approved'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a redemption (admin only)"""
        if request.user.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        redemption = self.get_object()
        
        with transaction.atomic():
            # Refund points to user
            user = redemption.user
            user.total_points += redemption.points_spent
            user.save()
            
            # Update redemption status
            redemption.status = 'rejected'
            redemption.processed_at = timezone.now()
            redemption.admin_notes = request.data.get('notes', '')
            redemption.save()
        
        # CACHE INVALIDATION: Clear user's cached data after points refund
        # This ensures immediate updates in the frontend
        invalidate_user_caches(redemption.user.id)
        
        return Response({'message': 'Redemption rejected and points refunded'})

class UserStatusViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own status, admins see all"""
        if self.request.user.role == 'admin':
            return UserStatus.objects.all()
        return UserStatus.objects.filter(user=self.request.user)

class ProfessionalViewSet(viewsets.ModelViewSet):
    queryset = Professional.objects.all()
    serializer_class = ProfessionalSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        if self.request.user.role == 'admin':
            return Professional.objects.all()
        # Non-admin users can only view active professionals
        return Professional.objects.filter(is_active=True)
    
    def perform_create(self, serializer):
        """Only admins can create professionals"""
        if self.request.user.role != 'admin':
            raise permissions.PermissionDenied("Only admins can create professionals")
        serializer.save()
    
    def perform_update(self, serializer):
        """Only admins can update professionals"""
        if self.request.user.role != 'admin':
            raise permissions.PermissionDenied("Only admins can update professionals")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only admins can delete professionals"""
        if self.request.user.role != 'admin':
            raise permissions.PermissionDenied("Only admins can delete professionals")
        instance.delete()

class ReviewRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own requests, admins see all"""
        if self.request.user.role == 'admin':
            return ReviewRequest.objects.all()
        return ReviewRequest.objects.filter(student=self.request.user)
    
    def perform_create(self, serializer):
        """Set the student to current user"""
        serializer.save(student=self.request.user)
    
    @action(detail=True, methods=['post'])
    def assign_professional(self, request, pk=None):
        """Assign a professional to a review request (admin only)"""
        if request.user.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        review_request = self.get_object()
        professional_id = request.data.get('professional_id')
        
        try:
            professional = Professional.objects.get(id=professional_id, is_active=True)
            review_request.professional = professional
            review_request.status = 'matched'
            review_request.matched_date = timezone.now()
            review_request.save()
            
            return Response({
                'message': f'Assigned {professional.name} to review request',
                'review_request': ReviewRequestSerializer(review_request).data
            })
        except Professional.DoesNotExist:
            return Response({'error': 'Professional not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def complete_review(self, request, pk=None):
        """Mark review as completed and add notes"""
        review_request = self.get_object()
        
        # Students can only complete their own reviews, professionals and admins can complete any
        if (request.user.role not in ['admin'] and 
            review_request.student != request.user and 
            (not review_request.professional or review_request.professional.email != request.user.email)):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        review_request.status = 'completed'
        review_request.completed_date = timezone.now()
        review_request.review_notes = request.data.get('review_notes', review_request.review_notes)
        review_request.student_feedback = request.data.get('student_feedback', review_request.student_feedback)
        review_request.rating = request.data.get('rating', review_request.rating)
        review_request.save()
        
        return Response({
            'message': 'Review marked as completed',
            'review_request': ReviewRequestSerializer(review_request).data
        })
    
    @action(detail=False, methods=['get'])
    def pending_requests(self, request):
        """Get pending review requests (admin only)"""
        if request.user.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        pending_requests = ReviewRequest.objects.filter(status='pending').order_by('-submission_date')
        serializer = ReviewRequestSerializer(pending_requests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get review request statistics (admin only)"""
        if request.user.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        from django.db.models import Count, Avg
        
        stats = {
            'total_requests': ReviewRequest.objects.count(),
            'pending_requests': ReviewRequest.objects.filter(status='pending').count(),
            'matched_requests': ReviewRequest.objects.filter(status='matched').count(),
            'completed_requests': ReviewRequest.objects.filter(status='completed').count(),
            'cancelled_requests': ReviewRequest.objects.filter(status='cancelled').count(),
            'average_rating': ReviewRequest.objects.filter(rating__isnull=False).aggregate(Avg('rating'))['rating__avg'] or 0,
            'total_professionals': Professional.objects.filter(is_active=True).count(),
        }
        
        return Response(stats)

class ScheduledSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduledSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own sessions, admins see all"""
        if self.request.user.role == 'admin':
            return ScheduledSession.objects.all()
        return ScheduledSession.objects.filter(
            models.Q(student=self.request.user) | 
            models.Q(professional__email=self.request.user.email)
        )
    
    def perform_create(self, serializer):
        """Only admins can create scheduled sessions"""
        if self.request.user.role != 'admin':
            raise permissions.PermissionDenied("Only admins can create scheduled sessions")
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def complete_session(self, request, pk=None):
        """Mark session as completed and add notes"""
        session = self.get_object()
        
        # Check permissions
        can_complete = (
            request.user.role == 'admin' or 
            session.student == request.user or 
            (session.professional and session.professional.email == request.user.email)
        )
        
        if not can_complete:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.session_notes = request.data.get('session_notes', session.session_notes)
        session.save()
        
        # Also update the related review request
        session.review_request.status = 'completed'
        session.review_request.completed_date = timezone.now()
        session.review_request.review_notes = request.data.get('review_notes', session.review_request.review_notes)
        session.review_request.save()
        
        return Response({
            'message': 'Session marked as completed',
            'session': ScheduledSessionSerializer(session).data
        })
    
    @action(detail=True, methods=['post'])
    def cancel_session(self, request, pk=None):
        """Cancel a scheduled session"""
        session = self.get_object()
        
        # Check permissions
        can_cancel = (
            request.user.role == 'admin' or 
            session.student == request.user or 
            (session.professional and session.professional.email == request.user.email)
        )
        
        if not can_cancel:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        session.status = 'cancelled'
        session.admin_notes = request.data.get('reason', 'Session cancelled')
        session.save()
        
        # Update review request status
        session.review_request.status = 'pending'
        session.review_request.professional = None
        session.review_request.scheduled_time = None
        session.review_request.save()
        
        return Response({
            'message': 'Session cancelled',
            'session': ScheduledSessionSerializer(session).data
        })

class ProfessionalAvailabilityViewSet(viewsets.ModelViewSet):
    serializer_class = ProfessionalAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user role"""
        if self.request.user.role == 'admin':
            return ProfessionalAvailability.objects.all()
        # Professionals can only see their own availability
        return ProfessionalAvailability.objects.filter(professional__email=self.request.user.email)
    
    def perform_create(self, serializer):
        """Only admins and professionals can create availability records"""
        if self.request.user.role not in ['admin'] and not Professional.objects.filter(email=self.request.user.email).exists():
            raise permissions.PermissionDenied("Only admins and professionals can create availability records")
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def active_availability(self, request):
        """Get active availability for all professionals"""
        if request.user.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        from django.utils import timezone
        today = timezone.now().date()
        
        active_availability = ProfessionalAvailability.objects.filter(
            is_active=True,
            end_date__gte=today
        ).select_related('professional')
        
        serializer = ProfessionalAvailabilitySerializer(active_availability, many=True)
        return Response(serializer.data)


# New API endpoints for frontend requirements

class DashboardStatsView(APIView):
    """Dashboard statistics with trends endpoint - HIGHLY OPTIMIZED with CACHING"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get dashboard statistics with period-over-period comparison - CACHED"""
        from datetime import datetime, timedelta
        from django.db.models import Count, Sum
        
        # CACHING: Check for cached dashboard stats first
        period = request.GET.get('period', '30days')
        cache_key = f"dashboard_stats_{request.user.id}_{period}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        period = request.GET.get('period', '30days')
        
        # Calculate date ranges
        now = timezone.now()
        if period == '7days':
            current_start = now - timedelta(days=7)
            previous_start = now - timedelta(days=14)
            previous_end = current_start
        elif period == '90days':
            current_start = now - timedelta(days=90)
            previous_start = now - timedelta(days=180)
            previous_end = current_start
        else:  # 30days default
            current_start = now - timedelta(days=30)
            previous_start = now - timedelta(days=60)
            previous_end = current_start
        
        user = request.user
        
        # OPTIMIZED: Single query for current period stats using index
        # Uses idx_points_logs_user_timestamp for optimal performance
        current_stats = PointsLog.objects.filter(
            user=user,
            timestamp__gte=current_start
        ).aggregate(
            points_earned=Sum('points_earned'),
            activity_count=Count('id')
        )
        current_points_earned = current_stats['points_earned'] or 0
        current_activities = current_stats['activity_count'] or 0
        
        # OPTIMIZED: Single query for previous period stats
        previous_stats = PointsLog.objects.filter(
            user=user,
            timestamp__gte=previous_start,
            timestamp__lt=previous_end
        ).aggregate(
            points_earned=Sum('points_earned'),
            activity_count=Count('id')
        )
        previous_points_earned = previous_stats['points_earned'] or 0
        previous_activities = previous_stats['activity_count'] or 0
        
        # Calculate trends
        def calculate_trend(current, previous):
            if previous == 0:
                return {
                    'change': current,
                    'percentage': 100.0 if current > 0 else 0.0,
                    'direction': 'up' if current > 0 else 'neutral'
                }
            
            change = current - previous
            percentage = (change / previous) * 100
            direction = 'up' if change > 0 else 'down' if change < 0 else 'neutral'
            
            return {
                'change': change,
                'percentage': round(percentage, 2),
                'direction': direction
            }
        
        # Available rewards count
        available_rewards = Incentive.objects.filter(
            is_active=True,
            points_required__lte=user.total_points
        ).count()
        
        # CACHING: Prepare response data
        response_data = {
            'current_period': {
                'total_points': user.total_points,
                'activities_completed': current_activities,
                'points_earned': current_points_earned,
                'start_date': current_start.date().isoformat(),
                'end_date': now.date().isoformat()
            },
            'previous_period': {
                'total_points': user.total_points - current_points_earned,
                'activities_completed': previous_activities,
                'points_earned': previous_points_earned,
                'start_date': previous_start.date().isoformat(),
                'end_date': previous_end.date().isoformat()
            },
            'trends': {
                'total_points': calculate_trend(user.total_points, user.total_points - current_points_earned),
                'activities_completed': calculate_trend(current_activities, previous_activities),
                'points_earned': calculate_trend(current_points_earned, previous_points_earned)
            }
        }
        
        # CACHE: Store results for 24 hours (86400 seconds) - Dashboard stats with cache invalidation
        # Long TTL since cache invalidation handles real-time updates
        cache.set(cache_key, response_data, 86400)
        
        return Response(response_data)


class PointsTimelineView(APIView):
    """Points timeline chart endpoint - HIGHLY OPTIMIZED"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get historical points data grouped by time periods - OPTIMIZED"""
        from datetime import datetime, timedelta, date
        from django.db.models import Sum, Q
        from django.db import connection
        
        granularity = request.GET.get('granularity', 'daily')
        days = int(request.GET.get('days', 30))
        
        user = request.user
        start_date = timezone.now() - timedelta(days=days)
        
        # CACHE: Check for cached timeline data
        cache_key = f"points_timeline_{user.id}_{granularity}_{days}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        # OPTIMIZED: Single query for all points logs in period with aggregation
        # Uses idx_points_logs_user_timestamp index
        logs_aggregated = PointsLog.objects.filter(
            user=user,
            timestamp__gte=start_date
        ).extra(
            select={'date': "DATE(timestamp)"}
        ).values('date').annotate(
            points_earned=Sum('points_earned'),
            activities_count=Sum(1)
        ).order_by('date')
        
        # OPTIMIZED: Single query for all redemptions in period with aggregation
        # Uses idx_redemptions_user_timestamp index
        redemptions_aggregated = Redemption.objects.filter(
            user=user,
            redeemed_at__gte=start_date
        ).extra(
            select={'date': "DATE(redeemed_at)"}
        ).values('date').annotate(
            points_spent=Sum('points_spent'),
            redemptions_count=Sum(1)
        ).order_by('date')
        
        # Convert to dictionaries for fast lookup
        logs_dict = {item['date']: item for item in logs_aggregated}
        redemptions_dict = {item['date']: item for item in redemptions_aggregated}
        
        # Calculate starting cumulative points
        period_earned = sum(item['points_earned'] for item in logs_aggregated)
        period_redeemed = sum(item['points_spent'] for item in redemptions_aggregated)
        cumulative_points = user.total_points - period_earned + period_redeemed
        
        # Generate timeline efficiently
        timeline = []
        current_date = start_date.date()
        end_date = timezone.now().date()
        
        if granularity == 'daily':
            while current_date <= end_date:
                date_str = current_date.isoformat()
                
                # Get data for this date (default to 0 if no data)
                day_logs = logs_dict.get(current_date, {'points_earned': 0, 'activities_count': 0})
                day_redemptions = redemptions_dict.get(current_date, {'points_spent': 0, 'redemptions_count': 0})
                
                points_earned = day_logs['points_earned']
                points_redeemed = day_redemptions['points_spent']
                net_points = points_earned - points_redeemed
                cumulative_points += net_points
                
                timeline.append({
                    'date': date_str,
                    'points_earned': points_earned,
                    'points_redeemed': points_redeemed,
                    'net_points': net_points,
                    'cumulative_points': cumulative_points,
                    'activities_count': day_logs['activities_count'],
                    'redemptions_count': day_redemptions['redemptions_count']
                })
                
                current_date += timedelta(days=1)
                
        elif granularity == 'weekly':
            while current_date <= end_date:
                week_end = current_date + timedelta(days=6)
                week_logs = []
                week_redemptions = []
                
                # Collect data for the week
                temp_date = current_date
                while temp_date <= week_end and temp_date <= end_date:
                    if temp_date in logs_dict:
                        week_logs.append(logs_dict[temp_date])
                    if temp_date in redemptions_dict:
                        week_redemptions.append(redemptions_dict[temp_date])
                    temp_date += timedelta(days=1)
                
                # Aggregate week data
                points_earned = sum(item['points_earned'] for item in week_logs)
                points_redeemed = sum(item['points_spent'] for item in week_redemptions)
                activities_count = sum(item['activities_count'] for item in week_logs)
                redemptions_count = sum(item['redemptions_count'] for item in week_redemptions)
                
                net_points = points_earned - points_redeemed
                cumulative_points += net_points
                
                timeline.append({
                    'date': current_date.isoformat(),
                    'points_earned': points_earned,
                    'points_redeemed': points_redeemed,
                    'net_points': net_points,
                    'cumulative_points': cumulative_points,
                    'activities_count': activities_count,
                    'redemptions_count': redemptions_count
                })
                
                current_date += timedelta(days=7)
                
        elif granularity == 'monthly':
            while current_date <= end_date:
                month_end = current_date + timedelta(days=29)
                month_logs = []
                month_redemptions = []
                
                # Collect data for the month
                temp_date = current_date
                while temp_date <= month_end and temp_date <= end_date:
                    if temp_date in logs_dict:
                        month_logs.append(logs_dict[temp_date])
                    if temp_date in redemptions_dict:
                        month_redemptions.append(redemptions_dict[temp_date])
                    temp_date += timedelta(days=1)
                
                # Aggregate month data
                points_earned = sum(item['points_earned'] for item in month_logs)
                points_redeemed = sum(item['points_spent'] for item in month_redemptions)
                activities_count = sum(item['activities_count'] for item in month_logs)
                redemptions_count = sum(item['redemptions_count'] for item in month_redemptions)
                
                net_points = points_earned - points_redeemed
                cumulative_points += net_points
                
                timeline.append({
                    'date': current_date.isoformat(),
                    'points_earned': points_earned,
                    'points_redeemed': points_redeemed,
                    'net_points': net_points,
                    'cumulative_points': cumulative_points,
                    'activities_count': activities_count,
                    'redemptions_count': redemptions_count
                })
                
                current_date += timedelta(days=30)
        
        # Calculate summary stats efficiently
        total_points_earned = period_earned
        total_points_redeemed = period_redeemed
        net_points_change = total_points_earned - total_points_redeemed
        average_daily_points = total_points_earned / days if days > 0 else 0
        
        # Find most active date
        most_active_date = None
        if timeline:
            most_active = max(timeline, key=lambda x: x.get('net_points', x['points_earned']))
            if most_active.get('net_points', most_active['points_earned']) > 0:
                most_active_date = most_active['date']
        
        response_data = {
            'timeline': timeline,
            'summary': {
                'total_days': days,
                'total_points_earned': total_points_earned,
                'total_points_redeemed': total_points_redeemed,
                'net_points_change': net_points_change,
                'average_daily_points': round(average_daily_points, 1),
                'most_active_date': most_active_date
            }
        }
        
        # CACHE: Store results for 24 hours (86400 seconds) - Timeline data with cache invalidation
        # Long TTL since cache invalidation handles real-time updates
        cache.set(cache_key, response_data, 86400)
        
        return Response(response_data)


class LeaderboardView(APIView):
    """Leaderboard system endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get ranked list of users by points - CACHED"""
        from datetime import datetime, timedelta
        from django.db.models import Sum, Q
        
        limit = int(request.GET.get('limit', 10))
        period = request.GET.get('period', 'all_time')
        
        # CACHE: Check for cached leaderboard data first
        cache_key = f"leaderboard_{period}_{limit}_{request.user.id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        # Base queryset - exclude users without points and ensure they have proper usernames
        # Calculate total points earned from PointsLog (excluding redemptions)
        base_queryset = User.objects.exclude(username__startswith='discord_').annotate(
            total_points_earned=Sum('points_logs__points_earned', default=0)
        ).exclude(total_points_earned=0)
        
        if period == 'weekly':
            # Points earned in last 7 days
            week_ago = timezone.now() - timedelta(days=7)
            users_with_monthly_points = base_queryset.annotate(
                period_points=Sum('points_logs__points_earned', 
                                filter=Q(points_logs__timestamp__gte=week_ago))
            ).exclude(period_points__isnull=True).order_by('-period_points', '-total_points_earned')
        elif period == 'monthly':
            # Points earned in last 30 days
            month_ago = timezone.now() - timedelta(days=30)
            users_with_monthly_points = base_queryset.annotate(
                period_points=Sum('points_logs__points_earned', 
                                filter=Q(points_logs__timestamp__gte=month_ago))
            ).exclude(period_points__isnull=True).order_by('-period_points', '-total_points_earned')
        else:
            # All time points earned (excluding redemptions)
            users_with_monthly_points = base_queryset.annotate(
                period_points=models.F('total_points_earned')
            ).order_by('-total_points_earned')
        
        # Get top users
        top_users = users_with_monthly_points[:limit]
        
        # Build leaderboard
        leaderboard = []
        for rank, user in enumerate(top_users, 1):
            # Create privacy-safe display name
            if hasattr(user, 'preferences') and user.preferences and user.preferences.privacy_settings.get('display_name_preference') == 'first_name_only':
                display_name = user.first_name or user.username
            elif hasattr(user, 'preferences') and user.preferences and user.preferences.privacy_settings.get('display_name_preference') == 'username':
                display_name = user.username
            else:
                display_name = f"{user.first_name} {user.last_name[0]}." if user.first_name and user.last_name else user.username
            
            leaderboard.append({
                'rank': rank,
                'user_id': user.id,
                'username': user.username,
                'display_name': display_name,
                'total_points': user.total_points_earned,  # Use points earned, not current balance
                'points_this_period': getattr(user, 'period_points', user.total_points_earned) or 0,
                'avatar_url': None,  # Could be added later
                'is_current_user': user.id == request.user.id
            })
        
        # Always provide current user's rank information
        current_user_points_earned = PointsLog.objects.filter(user=request.user).aggregate(
            total=Sum('points_earned', default=0)
        )['total'] or 0
        
        # Check if current user is already in the leaderboard
        current_user_in_leaderboard = any(item['is_current_user'] for item in leaderboard)
        
        if current_user_in_leaderboard:
            # Find the current user's entry in the leaderboard
            current_user_entry = next(item for item in leaderboard if item['is_current_user'])
            current_user_rank = {
                'rank': current_user_entry['rank'],
                'user_id': current_user_entry['user_id'],
                'username': current_user_entry['username'],
                'display_name': 'You',
                'total_points': current_user_entry['total_points'],
                'points_this_period': current_user_entry['points_this_period'],
                'is_current_user': True
            }
        else:
            # Calculate current user's position if not in top users
            current_user_position = users_with_monthly_points.filter(
                Q(total_points_earned__gt=current_user_points_earned) |
                (Q(total_points_earned=current_user_points_earned) & Q(id__lt=request.user.id))
            ).count() + 1
            
            current_user_rank = {
                'rank': current_user_position,
                'user_id': request.user.id,
                'username': request.user.username,
                'display_name': 'You',
                'total_points': current_user_points_earned,  # Use points earned, not current balance
                'points_this_period': getattr(request.user, 'period_points', current_user_points_earned) or 0,
                'is_current_user': True
            }
        
        total_participants = users_with_monthly_points.count()
        
        response_data = {
            'leaderboard': leaderboard,
            'current_user_rank': current_user_rank,
            'total_participants': total_participants
        }
        
        # CACHE: Store results for 12 hours (43200 seconds) - Leaderboard with cache invalidation
        # Moderate TTL since leaderboard affects multiple users and changes less frequently
        cache.set(cache_key, response_data, 43200)
        
        return Response(response_data)


class RewardsAvailableView(APIView):
    """Enhanced rewards system - available rewards with CACHING"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get available rewards with redemption info - CACHED"""
        user = request.user
        
        # CACHE: Check for cached rewards data
        cache_key = f"rewards_available_{user.id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        # Get ALL rewards, not just active ones
        rewards = Incentive.objects.all().order_by('points_required')
        
        rewards_data = []
        for reward in rewards:
            can_redeem = (user.total_points >= reward.points_required and 
                         reward.is_active and 
                         reward.stock_available > 0)
            rewards_data.append({
                'id': reward.id,
                'name': reward.name,
                'description': reward.description,
                'points_required': reward.points_required,
                'image_url': reward.image_url,
                'category': reward.category,
                'stock_available': reward.stock_available,
                'can_redeem': can_redeem,
                'is_active': reward.is_active,  # Add this field for frontend
                'sponsor': reward.sponsor
            })
        
        response_data = {
            'rewards': rewards_data
        }
        
        # CACHE: Store results for 24 hours (86400 seconds) - Rewards change infrequently
        # Long TTL since rewards are mostly static, admin changes are rare
        cache.set(cache_key, response_data, 86400)
        
        return Response(response_data)


class ClearRewardsCacheView(APIView):
    """Clear rewards cache for all users"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Clear all rewards cache entries"""
        try:
            from django.core.cache import cache
            
            # Clear all cache keys that start with 'rewards_available_'
            cache.clear()
            
            return Response({
                'success': True,
                'message': 'Rewards cache cleared successfully'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClearUserCachesView(APIView):
    """Clear all caches for a specific user"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Clear all caches that could be affected by user data changes"""
        try:
            from django.core.cache import cache
            from django.contrib.auth import get_user_model
            import json
            
            User = get_user_model()
            
            # Handle both DRF request.data and raw request body
            if hasattr(request, 'data'):
                user_id = request.data.get('user_id')
            else:
                body = json.loads(request.body.decode('utf-8'))
                user_id = body.get('user_id')
            
            if not user_id:
                return Response({
                    'success': False,
                    'error': 'user_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Clear all cache types that could be affected by user changes
            cache_patterns = [
                f"dashboard_stats_{user_id}_*",
                f"points_timeline_{user_id}_*", 
                f"leaderboard_*_{user_id}",
                f"activity_feed_{user_id}_*",
                f"rewards_available_{user_id}"
            ]
            
            # Since Django cache doesn't support pattern deletion easily, clear all cache
            # This is the most reliable approach for ensuring all user caches are cleared
            cache.clear()
            
            return Response({
                'success': True,
                'message': f'All caches cleared for user {user_id}'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RedeemRewardView(APIView):
    """Redeem reward endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Redeem a reward"""
        reward_id = request.data.get('reward_id')
        delivery_details = request.data.get('delivery_details', {})
        
        if not reward_id:
            return Response({
                'success': False,
                'error': {
                    'code': 'MISSING_REWARD_ID',
                    'message': 'Reward ID is required'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            reward = Incentive.objects.get(id=reward_id, is_active=True)
        except Incentive.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': 'REWARD_NOT_FOUND',
                    'message': 'Reward not found or not available'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        user = request.user
        
        # Check if user has enough points
        if user.total_points < reward.points_required:
            return Response({
                'success': False,
                'error': {
                    'code': 'INSUFFICIENT_POINTS',
                    'message': 'Not enough points to redeem this reward',
                    'details': {
                        'required': reward.points_required,
                        'available': user.total_points
                    }
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check stock availability
        if reward.stock_available <= 0:
            return Response({
                'success': False,
                'error': {
                    'code': 'OUT_OF_STOCK',
                    'message': 'This reward is currently out of stock'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Create redemption
            redemption = Redemption.objects.create(
                user=user,
                incentive=reward,
                points_spent=reward.points_required,
                delivery_details=delivery_details,
                status='pending'
            )
            
            # Deduct points from user
            user.total_points -= reward.points_required
            user.save()
            
            # Reduce stock
            reward.stock_available -= 1
            reward.save()
        
        # CACHE INVALIDATION: Clear user's cached data after transaction commits
        # This ensures immediate updates in the frontend
        invalidate_user_caches(user.id)
        
        return Response({
            'success': True,
            'data': {
                'redemption_id': redemption.id,
                'reward_name': reward.name,
                'points_spent': reward.points_required,
                'remaining_points': user.total_points,
                'status': redemption.status
            },
            'message': f'Successfully redeemed {reward.name}',
            'timestamp': timezone.now().isoformat()
        })


class RedemptionHistoryView(APIView):
    """User redemption history endpoint"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get user's redemption history"""
        user = request.user
        redemptions = Redemption.objects.filter(user=user).select_related('incentive').order_by('-redeemed_at')
        
        redemption_data = []
        for redemption in redemptions:
            redemption_data.append({
                'id': redemption.id,
                'reward': {
                    'name': redemption.incentive.name,
                    'image_url': redemption.incentive.image_url
                },
                'points_spent': redemption.points_spent,
                'redeemed_at': redemption.redeemed_at.isoformat(),
                'status': redemption.status,
                'tracking_info': redemption.tracking_info,
                'estimated_delivery': redemption.estimated_delivery.isoformat() if redemption.estimated_delivery else None
            })
        
        return Response({
            'redemptions': redemption_data
        })


class UnifiedActivityFeedView(APIView):
    """PHASE 1 FIX: Combined activity and redemption feed for recent activity"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """HIGHLY OPTIMIZED with CACHING: Get unified activity feed with minimal database queries"""
        user = request.user
        
        # FLEXIBLE LIMITING: Optional pagination for lifetime data access
        limit_param = request.GET.get('limit')
        if limit_param:
            limit = min(int(limit_param), 1000)  # Higher cap for lifetime view
            cache_key = f"activity_feed_{request.user.id}_{limit}"
        else:
            limit = None
            cache_key = f"activity_feed_{request.user.id}_lifetime"
        
        # CACHING: Check for cached data first
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
        
        # SUPER OPTIMIZED: Use values() to minimize data transfer and memory usage
        # Uses idx_points_logs_user_timestamp index for optimal performance
        if limit:
            activities_data = PointsLog.objects.filter(user=user).values(
                'id', 'timestamp', 'points_earned', 'details',
                'activity__name', 'activity__category'
            ).order_by('-timestamp')[:limit]
        else:
            # No limit = full lifetime data
            activities_data = PointsLog.objects.filter(user=user).values(
                'id', 'timestamp', 'points_earned', 'details',
                'activity__name', 'activity__category'
            ).order_by('-timestamp')
        
        # SUPER OPTIMIZED: Use values() for redemptions
        # Uses idx_redemptions_user_timestamp index
        if limit:
            redemptions_data = Redemption.objects.filter(user=user).values(
                'id', 'redeemed_at', 'points_spent', 'status',
                'incentive__name'
            ).order_by('-redeemed_at')[:limit]
        else:
            # No limit = full lifetime redemptions
            redemptions_data = Redemption.objects.filter(user=user).values(
                'id', 'redeemed_at', 'points_spent', 'status',
                'incentive__name'
            ).order_by('-redeemed_at')
        
        # OPTIMIZED: Combine and format with minimal processing
        feed_items = []
        
        # Add activities - minimal object creation
        for activity in activities_data:
            feed_items.append({
                'id': f"activity_{activity['id']}",
                'type': 'activity',
                'timestamp': activity['timestamp'].isoformat(),
                'points_change': activity['points_earned'],  # Positive
                'description': f"Completed: {activity['activity__name']}",
                'details': {
                    'activity_name': activity['activity__name'],
                    'activity_category': activity['activity__category'],
                    'points_earned': activity['points_earned']
                }
            })
        
        # Add redemptions - minimal object creation
        for redemption in redemptions_data:
            feed_items.append({
                'id': f"redemption_{redemption['id']}",
                'type': 'redemption', 
                'timestamp': redemption['redeemed_at'].isoformat(),
                'points_change': -redemption['points_spent'],  # Negative
                'description': f"Redeemed: {redemption['incentive__name']}",
                'details': {
                    'reward_name': redemption['incentive__name'],
                    'points_spent': redemption['points_spent'],
                    'status': redemption['status']
                }
            })
        
        # Sort by timestamp (most recent first)
        feed_items.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Only apply limit if it was specified (for lifetime data, show all)
        if limit:
            feed_items = feed_items[:limit]
        
        # CACHING: Prepare response data
        response_data = {
            'feed': feed_items,
            'total_items': len(feed_items),
            'is_lifetime_data': limit is None,
            'limit_applied': limit,
            'total_activities': len([item for item in feed_items if item['type'] == 'activity']),
            'total_redemptions': len([item for item in feed_items if item['type'] == 'redemption'])
        }
        
        # CACHE: Store results for 24 hours (86400 seconds) - Activity feed with cache invalidation
        # Long TTL since cache invalidation handles real-time updates
        cache.set(cache_key, response_data, 86400)
        
        return Response(response_data)


class UserPreferencesViewSet(viewsets.ModelViewSet):
    """User preferences management"""
    serializer_class = UserPreferencesSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserPreferences.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # Ensure user can only create their own preferences
        serializer.save(user=self.request.user)
    
    def get_object(self):
        # Get or create user preferences
        preferences, created = UserPreferences.objects.get_or_create(
            user=self.request.user,
            defaults={
                'email_notifications': {
                    'new_activities': True,
                    'reward_updates': True,
                    'leaderboard_changes': False
                },
                'privacy_settings': {
                    'show_in_leaderboard': True,
                    'display_name_preference': 'first_name_only'
                },
                'display_preferences': {}
            }
        )
        return preferences
    
    @action(detail=False, methods=['get'])
    def activity_preferences(self, request):
        """Get activity preferences including Discord integration"""
        preferences = self.get_object()
        
        return Response({
            'email_notifications': preferences.email_notifications,
            'discord_integration': {
                'is_linked': bool(request.user.discord_id and request.user.discord_verified),
                'discord_username': request.user.discord_id,  # Could store actual username separately
                'sync_activities': True  # This could be a preference
            }
        })


class BotIntegrationView(APIView):
    """Minimal secured endpoints for Discord bot integration.

    Security: requires X-Bot-Secret header that matches settings.BOT_SHARED_SECRET.
    Supported actions via JSON body:
      - { "action": "upsert-user", "discord_id": str, "display_name"?: str, "username"?: str }
      - { "action": "add-activity", "discord_id": str, "activity_type": str, "details"?: str }
      - { "action": "summary", "discord_id": str, "limit"?: int }
      - { "action": "leaderboard", "page"?: int, "page_size"?: int }
      - { "action": "admin-adjust", "discord_id": str, "delta_points": int, "reason"?: str }
      - { "action": "redeem", "discord_id": str, "incentive_id": int }
      - { "action": "clear-warnings", "discord_id": str }
      - { "action": "suspend-user", "discord_id": str, "duration_minutes": int }
      - { "action": "unsuspend-user", "discord_id": str }
      - { "action": "activitylog", "hours"?: int, "limit"?: int }
      - { "action": "submit-resource", "discord_id": str, "description": str }
      - { "action": "approve-resource", "submission_id": int, "points": int, "notes"?: str }
      - { "action": "reject-resource", "submission_id": int, "reason"?: str }
      - { "action": "pending-resources" }
      - { "action": "submit-event", "discord_id": str, "event_name"?: str, "description"?: str }
      - { "action": "approve-event", "submission_id": int, "points": int, "notes"?: str }
      - { "action": "reject-event", "submission_id": int, "reason"?: str }
      - { "action": "pending-events" }
      - { "action": "submit-linkedin", "discord_id": str, "description"?: str }
      - { "action": "approve-linkedin", "submission_id": int, "points": int, "notes"?: str }
      - { "action": "reject-linkedin", "submission_id": int, "reason"?: str }
      - { "action": "pending-linkedin" }
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.conf import settings

        shared_secret = request.headers.get("X-Bot-Secret", "")
        if not settings.BOT_SHARED_SECRET or shared_secret != settings.BOT_SHARED_SECRET:
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        action = request.data.get("action")
        if action == "upsert-user":
            return self._upsert_user(request)
        if action == "add-activity":
            return self._add_activity(request)
        if action == "link":
            return self._link_discord(request)
        if action == "summary":
            return self._summary(request)
        if action == "leaderboard":
            return self._leaderboard(request)
        if action == "admin-adjust":
            return self._admin_adjust(request)
        if action == "redeem":
            return self._redeem(request)
        if action == "clear-warnings":
            return self._clear_warnings(request)
        if action == "suspend-user":
            return self._suspend_user(request)
        if action == "unsuspend-user":
            return self._unsuspend_user(request)
        if action == "activitylog":
            return self._activitylog(request)
        if action == "review-status":
            return self._review_status(request)
        if action == "add-professional":
            return self._add_professional(request)
        if action == "list-professionals":
            return self._list_professionals(request)
        if action == "match-review":
            return self._match_review(request)
        if action == "review-stats":
            return self._review_stats(request)
        if action == "pending-reviews":
            return self._pending_reviews(request)
        if action == "suggest-matches":
            return self._suggest_matches(request)
        if action == "schedule-session":
            return self._schedule_session(request)
        if action == "add-professional-availability":
            return self._add_professional_availability(request)
        if action == "validate-discord-user":
            return self._validate_discord_user(request)
        if action == "submit-resource":
            return self._submit_resource(request)
        if action == "approve-resource":
            return self._approve_resource(request)
        if action == "reject-resource":
            return self._reject_resource(request)
        if action == "pending-resources":
            return self._pending_resources(request)
        if action == "submit-event":
            return self._submit_event(request)
        if action == "approve-event":
            return self._approve_event(request)
        if action == "reject-event":
            return self._reject_event(request)
        if action == "pending-events":
            return self._pending_events(request)
        if action == "submit-linkedin":
            return self._submit_linkedin(request)
        if action == "approve-linkedin":
            return self._approve_linkedin(request)
        if action == "reject-linkedin":
            return self._reject_linkedin(request)
        if action == "pending-linkedin":
            return self._pending_linkedin(request)

        return Response({"error": "Unknown action"}, status=status.HTTP_400_BAD_REQUEST)

    def _upsert_user(self, request):
        discord_id = request.data.get("discord_id")
        display_name = request.data.get("display_name") or ""
        username = request.data.get("username") or (display_name or f"discord_{discord_id}")

        if not discord_id:
            return Response({"error": "discord_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        user, created = User.objects.get_or_create(
            discord_id=str(discord_id),
            defaults={
                "username": username[:150] or f"discord_{discord_id}",
                "role": "student",
            },
        )

        if created:
            # Ensure status row exists
            UserStatus.objects.get_or_create(user=user)

        return Response({
            "user_id": user.id,
            "created": created,
            "username": user.username,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def _add_activity(self, request):
        discord_id = request.data.get("discord_id")
        activity_type = request.data.get("activity_type")
        details = request.data.get("details", "")

        if not discord_id or not activity_type:
            return Response({"error": "discord_id and activity_type are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            activity = Activity.objects.get(activity_type=activity_type, is_active=True)
        except Activity.DoesNotExist:
            return Response({"error": "Activity not found"}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            # Check suspension
            user_status, _ = UserStatus.objects.get_or_create(user=user)
            now = timezone.now()
            if user_status.points_suspended and user_status.suspension_end and now < user_status.suspension_end:
                return Response({"error": f"User suspended until {user_status.suspension_end.isoformat()}"}, status=403)
            # If suspension expired, clear it
            if user_status.points_suspended and user_status.suspension_end and now >= user_status.suspension_end:
                user_status.points_suspended = False
                user_status.save(update_fields=["points_suspended"])

            # Daily limit check for discord_activity only
            if activity_type == "discord_activity":
                today = now.date()
                # Check if user already earned discord_activity points today
                existing_log = PointsLog.objects.filter(
                    user=user,
                    activity=activity,
                    timestamp__date=today
                ).first()
                
                if existing_log:
                    return Response({
                        "message": "Daily Discord activity points already earned today",
                        "total_points": user.total_points,
                        "already_earned_today": True,
                    })

            points_log = PointsLog.objects.create(
                user=user,
                activity=activity,
                points_earned=activity.points_value,
                details=details,
            )
            user.total_points += activity.points_value
            user.save(update_fields=["total_points"])
            user_status.last_activity = timezone.now()
            user_status.save(update_fields=["last_activity"])

        # Check for unlocks after commit
        _check_and_record_unlocks(user)

        # CACHE INVALIDATION: Clear user's cached data after transaction commits
        # This ensures immediate updates in the frontend
        logger.info(f"🚀 About to invalidate caches for user {user.id} after adding activity")
        invalidate_user_caches(user.id)
        logger.info(f"🎯 Cache invalidation call completed for user {user.id}")

        return Response({
            "message": f"Added {activity.points_value} points for {activity.name}",
            "total_points": user.total_points,
            "points_log_id": points_log.id,
        })

    def _link_discord(self, request):
        code = request.data.get("code")
        discord_id = request.data.get("discord_id")
        discord_username = request.data.get("discord_username")  # Bot will provide this
        
        if not code or not discord_id:
            return Response({"error": "code and discord_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Use a transaction for select_for_update to avoid DB errors under autocommit
        with transaction.atomic():
            try:
                link = DiscordLinkCode.objects.select_for_update().get(code=code)
            except DiscordLinkCode.DoesNotExist:
                return Response({"error": "Invalid code"}, status=status.HTTP_404_NOT_FOUND)

            if link.used_at:
                return Response({"error": "Code already used"}, status=status.HTTP_400_BAD_REQUEST)
            if timezone.now() > link.expires_at:
                return Response({"error": "Code expired"}, status=status.HTTP_400_BAD_REQUEST)

            user = link.user
            
            # SECURITY CHECK 1: Prevent relinking already verified accounts
            if user.discord_verified and user.discord_id:
                return Response({
                    "error": "Discord account already verified and linked. Cannot relink for security reasons."
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # SECURITY CHECK 2: If user has unverified username, verify it matches
            if user.discord_username_unverified and discord_username:
                # Extract username from full discord_username (remove discriminator for comparison)
                provided_username = user.discord_username_unverified.split('#')[0].lower()
                actual_username = discord_username.split('#')[0].lower()
                
                if provided_username != actual_username:
                    return Response({
                        "error": f"Discord username mismatch. You registered with '{user.discord_username_unverified}' but are linking as '{discord_username}'. Please use the correct Discord account."
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # SECURITY CHECK 3: Prevent linking to already-linked Discord accounts
            existing_user = User.objects.filter(discord_id=str(discord_id), discord_verified=True).exclude(id=user.id).first()
            if existing_user:
                return Response({
                    "error": f"This Discord account is already linked to another user account. Each Discord account can only be linked once."
                }, status=status.HTTP_400_BAD_REQUEST)

            # All security checks passed - complete the linking
            user.discord_id = str(discord_id)
            user.discord_verified = True
            user.discord_verified_at = timezone.now()
            
            # Clear unverified username now that it's verified
            if user.discord_username_unverified:
                user.discord_username_unverified = None
                
            user.save(update_fields=["discord_id", "discord_verified", "discord_verified_at", "discord_username_unverified"])
            
            link.used_at = timezone.now()
            link.save(update_fields=["used_at"])

        logger.info(f"Successfully verified and linked Discord account {discord_username} to user {user.username}")
        return Response({
            "linked": True, 
            "discord_id": str(discord_id),
            "verified": True,
            "message": "Discord account successfully verified and linked!"
        })

    def _summary(self, request):
        discord_id = request.data.get("discord_id")
        limit = int(request.data.get("limit", 10))
        if not discord_id:
            return Response({"error": "discord_id is required"}, status=400)
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        logs = PointsLog.objects.filter(user=user).select_related('activity').order_by('-timestamp')[:limit]
        log_items = [
            {
                "action": pl.activity.name,
                "details": pl.details,
                "points": pl.points_earned,
                "timestamp": pl.timestamp.isoformat(),
            }
            for pl in logs
        ]

        # Unlocked incentives
        unlocked_ids = set(UserIncentiveUnlock.objects.filter(user=user).values_list('incentive_id', flat=True))
        qualifying = Incentive.objects.filter(is_active=True, points_required__lte=user.total_points)
        unlocks = [
            {
                "id": inc.id,
                "name": inc.name,
                "points_required": inc.points_required,
                "unlocked": True,
            }
            for inc in qualifying
        ]

        return Response({
            "discord_id": str(discord_id),
            "total_points": user.total_points,
            "recent_logs": log_items,
            "unlocks": unlocks,
        })

    def _leaderboard(self, request):
        from django.core.paginator import Paginator
        from django.db.models import Sum
        
        page = int(request.data.get("page", 1))
        page_size = int(request.data.get("page_size", 10))
        
        # Calculate total points earned from PointsLog (excluding redemptions)
        qs = User.objects.exclude(discord_id__isnull=True).exclude(discord_id="").annotate(
            total_points_earned=Sum('points_logs__points_earned', default=0)
        ).exclude(total_points_earned=0).order_by('-total_points_earned')
        
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        items = [
            {
                "position": (page_obj.start_index() + idx),
                "discord_id": u.discord_id,
                "username": u.username,
                "total_points": u.total_points_earned,  # Use points earned, not current balance
            }
            for idx, u in enumerate(page_obj.object_list)
        ]
        return Response({
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "results": items,
            "total_users": paginator.count,
        })

    def _admin_adjust(self, request):
        discord_id = request.data.get("discord_id")
        delta = int(request.data.get("delta_points", 0))
        reason = request.data.get("reason", "Admin adjustment")
        if not discord_id or delta == 0:
            return Response({"error": "discord_id and non-zero delta_points are required"}, status=400)
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        # Use any existing activity type to record admin adjustments; falling back to discord_activity
        activity = Activity.objects.filter(activity_type='discord_activity', is_active=True).first()
        if not activity:
            return Response({"error": "discord_activity not configured"}, status=500)
        with transaction.atomic():
            PointsLog.objects.create(
                user=user,
                activity=activity,
                points_earned=delta,
                details=f"Admin adjustment: {reason}",
            )
            user.total_points += delta
            user.save(update_fields=["total_points"])
            status_row, _ = UserStatus.objects.get_or_create(user=user)
            status_row.last_activity = timezone.now()
            status_row.save(update_fields=["last_activity"])
        _check_and_record_unlocks(user)
        return Response({
            "discord_id": str(discord_id),
            "total_points": user.total_points,
            "delta_applied": delta,
        })

    def _redeem(self, request):
        discord_id = request.data.get("discord_id")
        incentive_id = request.data.get("incentive_id")
        if not discord_id or not incentive_id:
            return Response({"error": "discord_id and incentive_id are required"}, status=400)
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        try:
            incentive = Incentive.objects.get(id=incentive_id, is_active=True)
        except Incentive.DoesNotExist:
            return Response({"error": "Incentive not found"}, status=404)
        if user.total_points < incentive.points_required:
            return Response({"error": "Insufficient points"}, status=400)
        with transaction.atomic():
            redemption = Redemption.objects.create(
                user=user,
                incentive=incentive,
                points_spent=incentive.points_required,
                status='pending',
            )
            user.total_points -= incentive.points_required
            user.save(update_fields=["total_points"])
        return Response({
            "message": f"Redeemed {incentive.name}",
            "redemption_id": redemption.id,
            "remaining_points": user.total_points,
        })

    def _clear_warnings(self, request):
        discord_id = request.data.get("discord_id")
        if not discord_id:
            return Response({"error": "discord_id is required"}, status=400)
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        status_row, _ = UserStatus.objects.get_or_create(user=user)
        status_row.warnings = 0
        status_row.save(update_fields=["warnings"])
        return Response({"cleared": True})

    def _suspend_user(self, request):
        from datetime import timedelta
        discord_id = request.data.get("discord_id")
        duration_minutes = int(request.data.get("duration_minutes", 0))
        if not discord_id or duration_minutes <= 0:
            return Response({"error": "discord_id and positive duration_minutes are required"}, status=400)
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        status_row, _ = UserStatus.objects.get_or_create(user=user)
        status_row.points_suspended = True
        status_row.suspension_end = timezone.now() + timedelta(minutes=duration_minutes)
        status_row.save(update_fields=["points_suspended", "suspension_end"])
        return Response({
            "suspended": True,
            "until": status_row.suspension_end.isoformat(),
        })

    def _unsuspend_user(self, request):
        discord_id = request.data.get("discord_id")
        if not discord_id:
            return Response({"error": "discord_id is required"}, status=400)
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        status_row, _ = UserStatus.objects.get_or_create(user=user)
        status_row.points_suspended = False
        status_row.suspension_end = None
        status_row.save(update_fields=["points_suspended", "suspension_end"])
        return Response({"unsuspended": True})

    def _activitylog(self, request):
        from datetime import timedelta
        hours = int(request.data.get("hours", 24))
        limit = int(request.data.get("limit", 20))
        since = timezone.now() - timedelta(hours=hours)
        logs = PointsLog.objects.filter(timestamp__gt=since).select_related('user', 'activity').order_by('-timestamp')[:limit]
        items = [
            {
                "discord_id": pl.user.discord_id,
                "username": pl.user.username,
                "action": pl.activity.name,
                "details": pl.details,
                "points": pl.points_earned,
                "timestamp": pl.timestamp.isoformat(),
            }
            for pl in logs
        ]
        return Response({"items": items})

    def _review_status(self, request):
        """Check review request status for a user"""
        discord_id = request.data.get("discord_id")
        if not discord_id:
            return Response({"error": "discord_id is required"}, status=400)
        
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        # Get user's most recent review request
        recent_request = ReviewRequest.objects.filter(student=user).order_by('-submission_date').first()
        
        if not recent_request:
            return Response({
                "has_request": False,
                "message": "No review requests found"
            })
        
        return Response({
            "has_request": True,
            "status": recent_request.status,
            "submission_date": recent_request.submission_date.isoformat(),
            "professional": recent_request.professional.name if recent_request.professional else None,
            "scheduled_time": recent_request.scheduled_time.isoformat() if recent_request.scheduled_time else None,
        })

    def _add_professional(self, request):
        """Add a professional to the review pool"""
        name = request.data.get("name")
        email = request.data.get("email")
        specialties = request.data.get("specialties", "")
        
        if not name or not email:
            return Response({"error": "name and email are required"}, status=400)
        
        professional = Professional.objects.create(
            name=name,
            email=email,
            specialties=specialties,
            is_active=True
        )
        
        return Response({
            "message": f"Professional {name} added successfully",
            "professional_id": professional.id,
            "name": professional.name,
            "specialties": professional.specialties
        })

    def _list_professionals(self, request):
        """List available professionals"""
        professionals = Professional.objects.filter(is_active=True).order_by('name')
        
        items = [
            {
                "id": p.id,
                "name": p.name,
                "specialties": p.specialties,
                "total_reviews": p.total_reviews,
                "rating": float(p.rating) if p.rating else 0.0,
            }
            for p in professionals
        ]
        
        return Response({
            "professionals": items,
            "total_count": len(items)
        })

    def _match_review(self, request):
        """Match a student with a professional for review"""
        discord_id = request.data.get("discord_id")
        professional_id = request.data.get("professional_id")
        
        if not discord_id or not professional_id:
            return Response({"error": "discord_id and professional_id are required"}, status=400)
        
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        try:
            professional = Professional.objects.get(id=professional_id, is_active=True)
        except Professional.DoesNotExist:
            return Response({"error": "Professional not found"}, status=404)
        
        # Find pending review request for this student
        review_request = ReviewRequest.objects.filter(
            student=user, 
            status='pending'
        ).order_by('-submission_date').first()
        
        if not review_request:
            return Response({"error": "No pending review request found for this student"}, status=404)
        
        # Assign professional and update status
        review_request.professional = professional
        review_request.status = 'matched'
        review_request.matched_date = timezone.now()
        review_request.save()
        
        return Response({
            "message": f"Matched {user.username} with {professional.name}",
            "review_request_id": review_request.id,
            "student": user.username,
            "professional": professional.name,
            "status": review_request.status
        })

    def _review_stats(self, request):
        """Get resume review program statistics"""
        from django.db.models import Count, Avg
        
        stats = {
            "total_requests": ReviewRequest.objects.count(),
            "pending_requests": ReviewRequest.objects.filter(status='pending').count(),
            "matched_requests": ReviewRequest.objects.filter(status='matched').count(),
            "completed_requests": ReviewRequest.objects.filter(status='completed').count(),
            "cancelled_requests": ReviewRequest.objects.filter(status='cancelled').count(),
            "total_professionals": Professional.objects.filter(is_active=True).count(),
            "average_rating": ReviewRequest.objects.filter(rating__isnull=False).aggregate(Avg('rating'))['rating__avg'] or 0,
        }
        
        # Recent activity (last 7 days)
        from datetime import timedelta
        recent_date = timezone.now() - timedelta(days=7)
        stats["recent_requests"] = ReviewRequest.objects.filter(submission_date__gte=recent_date).count()
        stats["recent_completions"] = ReviewRequest.objects.filter(completed_date__gte=recent_date).count()
        
        return Response(stats)

    def _pending_reviews(self, request):
        """Get pending review requests with availability data"""
        pending_requests = ReviewRequest.objects.filter(status='pending').select_related('student').order_by('-submission_date')
        
        items = []
        for req in pending_requests:
            items.append({
                "id": req.id,
                "student_username": req.student.username,
                "discord_id": req.student.discord_id,
                "target_industry": req.target_industry,
                "target_role": req.target_role,
                "experience_level": req.experience_level,
                "preferred_times": req.preferred_times,
                "submission_date": req.submission_date.isoformat(),
                "days_pending": (timezone.now() - req.submission_date).days,
            })
        
        return Response({
            "pending_requests": items,
            "total_count": len(items)
        })
    
    def _suggest_matches(self, request):
        """Find professionals with overlapping availability for a student"""
        discord_id = request.data.get("discord_id")
        if not discord_id:
            return Response({"error": "discord_id is required"}, status=400)
        
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        # Get the student's review request
        review_request = ReviewRequest.objects.filter(
            student=user, 
            status='pending'
        ).order_by('-submission_date').first()
        
        if not review_request:
            return Response({"error": "No pending review request found for this student"}, status=404)
        
        # Get all active professionals with their availability
        from datetime import datetime, timedelta
        today = timezone.now().date()
        
        professionals_with_availability = ProfessionalAvailability.objects.filter(
            is_active=True,
            end_date__gte=today
        ).select_related('professional')
        
        matches = []
        student_times = review_request.preferred_times or []
        
        for prof_avail in professionals_with_availability:
            professional = prof_avail.professional
            if not professional.is_active:
                continue
                
            # Enhanced overlap detection using sophisticated matching algorithm
            try:
                from availability_matcher import find_availability_matches
                matches = find_availability_matches(student_times, prof_avail.availability_slots)
                overlapping_times = [match['student_availability'] + " ↔ " + match['professional_availability'] 
                                   for match in matches if match['match_score'] > 0.3]
            except ImportError:
                # Fallback to simple matching if enhanced matcher not available
                overlapping_times = self._find_time_overlaps(student_times, prof_avail.availability_slots)
            
            if overlapping_times:
                matches.append({
                    "professional_id": professional.id,
                    "professional_name": professional.name,
                    "specialties": professional.specialties,
                    "total_reviews": professional.total_reviews,
                    "rating": float(professional.rating) if professional.rating else 0.0,
                    "overlapping_times": overlapping_times,
                    "availability_valid_until": prof_avail.end_date.isoformat(),
                })
        
        # Sort by rating and total reviews
        matches.sort(key=lambda x: (x['rating'], x['total_reviews']), reverse=True)
        
        return Response({
            "student": user.username,
            "matches": matches,
            "total_matches": len(matches),
            "student_preferred_times": student_times
        })
    
    def _schedule_session(self, request):
        """Schedule a session between student and professional"""
        discord_id = request.data.get("discord_id")
        professional_name = request.data.get("professional_name")
        scheduled_time_str = request.data.get("scheduled_time")
        duration_minutes = int(request.data.get("duration_minutes", 30))
        
        if not all([discord_id, professional_name, scheduled_time_str]):
            return Response({"error": "discord_id, professional_name, and scheduled_time are required"}, status=400)
        
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        
        try:
            professional = Professional.objects.get(name__icontains=professional_name, is_active=True)
        except Professional.DoesNotExist:
            return Response({"error": "Professional not found"}, status=404)
        except Professional.MultipleObjectsReturned:
            return Response({"error": "Multiple professionals found with that name. Be more specific."}, status=400)
        
        # Find pending review request
        review_request = ReviewRequest.objects.filter(
            student=user, 
            status='pending'
        ).order_by('-submission_date').first()
        
        if not review_request:
            return Response({"error": "No pending review request found for this student"}, status=404)
        
        # Parse scheduled time
        try:
            from dateutil import parser
            scheduled_time = parser.parse(scheduled_time_str)
        except:
            return Response({"error": "Invalid date format. Use format like 'Monday 2:00 PM' or '2024-01-15 14:00'"}, status=400)
        
        # Create scheduled session
        with transaction.atomic():
            session = ScheduledSession.objects.create(
                review_request=review_request,
                student=user,
                professional=professional,
                scheduled_time=scheduled_time,
                duration_minutes=duration_minutes
            )
            
            # Update review request status
            review_request.professional = professional
            review_request.status = 'scheduled'
            review_request.scheduled_time = scheduled_time
            review_request.matched_date = timezone.now()
            review_request.save()
            
            # Create calendar event if calendar integration is available
            try:
                from calendar_integration import create_review_session_event
                
                # Get email addresses
                student_email = user.email or f"{user.username}@example.com"
                professional_email = professional.email
                
                # Create calendar event
                event_id = create_review_session_event(
                    student_email=student_email,
                    professional_email=professional_email,
                    start_time=scheduled_time,
                    duration_minutes=duration_minutes,
                    meeting_title=f"Resume Review Session - {user.username}",
                    meeting_description=f"Resume review session between {user.username} and {professional.name}"
                )
                
                if event_id:
                    session.calendar_event_id = event_id
                    session.save()
                    
            except ImportError:
                # Calendar integration not available
                pass
            except Exception as e:
                # Log calendar error but don't fail the session creation
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to create calendar event: {e}")
        
        return Response({
            "message": f"Session scheduled between {user.username} and {professional.name}",
            "session_id": session.id,
            "scheduled_time": session.scheduled_time.isoformat(),
            "duration_minutes": session.duration_minutes,
            "status": session.status
        })
    
    def _add_professional_availability(self, request):
        """Add professional availability from Google Form response"""
        professional_id = request.data.get("professional_id")
        form_response_id = request.data.get("form_response_id")
        form_data = request.data.get("form_data", {})
        availability_slots = request.data.get("availability_slots", [])
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        
        if not all([professional_id, form_response_id, start_date, end_date]):
            return Response({"error": "professional_id, form_response_id, start_date, and end_date are required"}, status=400)
        
        try:
            professional = Professional.objects.get(id=professional_id, is_active=True)
        except Professional.DoesNotExist:
            return Response({"error": "Professional not found"}, status=404)
        
        try:
            from datetime import datetime
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)
        
        # Create or update availability record
        availability, created = ProfessionalAvailability.objects.update_or_create(
            professional=professional,
            form_response_id=form_response_id,
            defaults={
                'form_data': form_data,
                'availability_slots': availability_slots,
                'preferred_days': form_data.get('preferred_days', []),
                'time_zone': form_data.get('time_zone', 'UTC'),
                'start_date': start_date_obj,
                'end_date': end_date_obj,
                'notes': form_data.get('notes', ''),
                'is_active': True
            }
        )
        
        return Response({
            "message": f"Availability {'created' if created else 'updated'} for {professional.name}",
            "availability_id": availability.id,
            "professional": professional.name,
            "valid_period": f"{start_date} to {end_date}",
            "slots_count": len(availability_slots)
        })
    
    def _find_time_overlaps(self, student_times, professional_times):
        """Simple time overlap detection - can be enhanced with better parsing"""
        overlaps = []
        
        # Convert to lowercase for easier matching
        student_times_lower = [t.lower() for t in student_times if t]
        professional_times_lower = [t.lower() for t in professional_times if t]
        
        # Look for common days/times
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        times = ['morning', 'afternoon', 'evening', '9', '10', '11', '12', '1', '2', '3', '4', '5']
        
        for student_time in student_times_lower:
            for professional_time in professional_times_lower:
                # Check for exact matches or partial matches
                if student_time == professional_time:
                    overlaps.append(student_time)
                else:
                    # Check for day/time component matches
                    for day in days:
                        if day in student_time and day in professional_time:
                            for time in times:
                                if time in student_time and time in professional_time:
                                    overlap = f"{day} {time}"
                                    if overlap not in overlaps:
                                        overlaps.append(overlap)
        
        return overlaps

    def _validate_discord_user(self, request):
        """Validate Discord username against server membership (called by bot)"""
        discord_username = request.data.get("discord_username")
        
        if not discord_username:
            return Response({"error": "discord_username is required"}, status=400)
        
        # Use the same Discord API validation logic
        validation_result = self._validate_with_discord_api(discord_username)
        
        if validation_result['success']:
            return Response({
                "valid": validation_result['valid'],
                "message": validation_result['message'],
                "discord_id": validation_result.get('discord_id'),
                "discord_username": validation_result.get('discord_username')
            }, status=200)
        else:
            return Response({
                "valid": False,
                "message": validation_result['message']
            }, status=200)

    def _submit_resource(self, request):
        """Submit a resource for admin review"""
        discord_id = request.data.get("discord_id")
        description = request.data.get("description")
        
        if not discord_id or not description:
            return Response({"error": "discord_id and description are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        if len(description.strip()) < 10:
            return Response({"error": "Description must be at least 10 characters"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Create resource submission
        submission = ResourceSubmission.objects.create(
            user=user,
            description=description.strip(),
            status='pending'
        )
        
        return Response({
            "success": True,
            "submission_id": submission.id,
            "message": "Resource submitted for review"
        }, status=status.HTTP_201_CREATED)

    def _approve_resource(self, request):
        """Approve a resource submission and award points"""
        submission_id = request.data.get("submission_id")
        points = request.data.get("points", 10)
        notes = request.data.get("notes", "")
        
        if not submission_id:
            return Response({"error": "submission_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            submission = ResourceSubmission.objects.get(id=submission_id, status='pending')
        except ResourceSubmission.DoesNotExist:
            return Response({"error": "Pending resource submission not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Update submission status
        submission.status = 'approved'
        submission.points_awarded = points
        submission.admin_notes = notes
        submission.reviewed_at = timezone.now()
        submission.save()
        
        # Award points via admin adjustment
        activity = Activity.objects.filter(activity_type='resource_share', is_active=True).first()
        if not activity:
            return Response({"error": "resource_share activity not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        with transaction.atomic():
            PointsLog.objects.create(
                user=submission.user,
                activity=activity,
                points_earned=points,
                details=f"Resource approved: {submission.description[:100]}",
            )
            submission.user.total_points += points
            submission.user.save(update_fields=["total_points"])
            status_row, _ = UserStatus.objects.get_or_create(user=submission.user)
            status_row.last_activity = timezone.now()
            status_row.save(update_fields=["last_activity"])
        
        return Response({
            "success": True,
            "submission_id": submission.id,
            "user_id": submission.user.discord_id,
            "points_awarded": points,
            "total_points": submission.user.total_points,
            "message": "Resource approved and points awarded"
        })

    def _reject_resource(self, request):
        """Reject a resource submission"""
        submission_id = request.data.get("submission_id")
        reason = request.data.get("reason", "No reason provided")
        
        if not submission_id:
            return Response({"error": "submission_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            submission = ResourceSubmission.objects.get(id=submission_id, status='pending')
        except ResourceSubmission.DoesNotExist:
            return Response({"error": "Pending resource submission not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Update submission status
        submission.status = 'rejected'
        submission.admin_notes = reason
        submission.reviewed_at = timezone.now()
        submission.save()
        
        return Response({
            "success": True,
            "submission_id": submission.id,
            "user_id": submission.user.discord_id,
            "message": "Resource rejected"
        })

    def _pending_resources(self, request):
        """Get all pending resource submissions - OPTIMIZED"""
        # OPTIMIZED: Use select_related to fetch user data in single query
        pending_submissions = ResourceSubmission.objects.filter(
            status='pending'
        ).select_related('user').order_by('-submitted_at')
        
        # OPTIMIZED: Build list in single pass, avoiding N+1 queries
        submissions_data = []
        for submission in pending_submissions:
            submissions_data.append({
                "id": submission.id,
                "discord_id": submission.user.discord_id,
                "username": submission.user.username,
                "description": submission.description,
                "submitted_at": submission.submitted_at.isoformat(),
            })
        
        return Response({
            "success": True,
            "pending_count": len(submissions_data),  # Use len() instead of count() query
            "submissions": submissions_data
        })

    def _submit_event(self, request):
        """Submit an event attendance for admin review"""
        discord_id = request.data.get("discord_id")
        event_name = request.data.get("event_name", "Event Attendance")
        description = request.data.get("description", "User claims to have attended an event")
        
        if not discord_id:
            return Response({"error": "discord_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Create event submission
        submission = EventSubmission.objects.create(
            user=user,
            event_details=f"{event_name}: {description}",
            status='pending'
        )
        
        return Response({
            "success": True,
            "submission_id": submission.id,
            "message": "Event attendance submitted for review"
        }, status=status.HTTP_201_CREATED)

    def _approve_event(self, request):
        """Approve an event submission and award points - OPTIMIZED"""
        submission_id = request.data.get("submission_id")
        points = request.data.get("points", 15)
        notes = request.data.get("notes", "")
        
        if not submission_id:
            return Response({"error": "submission_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            submission = EventSubmission.objects.get(id=submission_id, status='pending')
        except EventSubmission.DoesNotExist:
            return Response({"error": "Pending event submission not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Update submission status
        submission.status = 'approved'
        submission.points_awarded = points
        submission.admin_notes = notes
        submission.reviewed_at = timezone.now()
        submission.save()
        
        # Award points via admin adjustment
        activity = Activity.objects.filter(activity_type='event_attendance', is_active=True).first()
        if not activity:
            return Response({"error": "event_attendance activity not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        with transaction.atomic():
            PointsLog.objects.create(
                user=submission.user,
                activity=activity,
                points_earned=points,
                details=f"Event approved: {submission.event_details}",
            )
            submission.user.total_points += points
            submission.user.save(update_fields=["total_points"])
            status_row, _ = UserStatus.objects.get_or_create(user=submission.user)
            status_row.last_activity = timezone.now()
            status_row.save(update_fields=["last_activity"])
        
        return Response({
            "success": True,
            "submission_id": submission.id,
            "user_id": submission.user.discord_id,
            "points_awarded": points,
            "total_points": submission.user.total_points,
            "message": "Event approved and points awarded"
        })

    def _reject_event(self, request):
        """Reject an event submission - OPTIMIZED"""
        submission_id = request.data.get("submission_id")
        reason = request.data.get("reason", "No reason provided")
        
        if not submission_id:
            return Response({"error": "submission_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            submission = EventSubmission.objects.get(id=submission_id, status='pending')
        except EventSubmission.DoesNotExist:
            return Response({"error": "Pending event submission not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Update submission status
        submission.status = 'rejected'
        submission.admin_notes = reason
        submission.reviewed_at = timezone.now()
        submission.save()
        
        return Response({
            "success": True,
            "submission_id": submission.id,
            "user_id": submission.user.discord_id,
            "message": "Event rejected"
        })

    def _pending_events(self, request):
        """Get all pending event submissions - OPTIMIZED"""
        # OPTIMIZED: Use select_related to fetch user data in single query
        pending_submissions = EventSubmission.objects.filter(
            status='pending'
        ).select_related('user').order_by('-submitted_at')
        
        # OPTIMIZED: Build list in single pass, avoiding N+1 queries
        submissions_data = []
        for submission in pending_submissions:
            submissions_data.append({
                "id": submission.id,
                "discord_id": submission.user.discord_id,
                "username": submission.user.username,
                "event_name": "Event Attendance",  # Default since we don't have separate event_name field
                "description": submission.event_details,
                "submitted_at": submission.submitted_at.isoformat(),
            })
        
        return Response({
            "success": True,
            "pending_count": len(submissions_data),  # Use len() instead of count() query
            "submissions": submissions_data
        })

    def _submit_linkedin(self, request):
        """Submit a LinkedIn update for admin review"""
        discord_id = request.data.get("discord_id")
        description = request.data.get("description", "User claims to have posted a LinkedIn update")
        
        if not discord_id:
            return Response({"error": "discord_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(discord_id=str(discord_id))
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Create LinkedIn submission
        submission = LinkedInSubmission.objects.create(
            user=user,
            linkedin_url=description,
            status='pending'
        )
        
        return Response({
            "success": True,
            "submission_id": submission.id,
            "message": "LinkedIn update submitted for review"
        }, status=status.HTTP_201_CREATED)

    def _approve_linkedin(self, request):
        """Approve a LinkedIn submission and award points - OPTIMIZED"""
        submission_id = request.data.get("submission_id")
        points = request.data.get("points", 5)
        notes = request.data.get("notes", "")
        
        if not submission_id:
            return Response({"error": "submission_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            submission = LinkedInSubmission.objects.get(id=submission_id, status='pending')
        except LinkedInSubmission.DoesNotExist:
            return Response({"error": "Pending LinkedIn submission not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Update submission status
        submission.status = 'approved'
        submission.points_awarded = points
        submission.admin_notes = notes
        submission.reviewed_at = timezone.now()
        submission.save()
        
        # Award points via admin adjustment
        activity = Activity.objects.filter(activity_type='linkedin_post', is_active=True).first()
        if not activity:
            return Response({"error": "linkedin_post activity not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        with transaction.atomic():
            PointsLog.objects.create(
                user=submission.user,
                activity=activity,
                points_earned=points,
                details=f"LinkedIn update approved: {submission.linkedin_url[:100]}",
            )
            submission.user.total_points += points
            submission.user.save(update_fields=["total_points"])
            status_row, _ = UserStatus.objects.get_or_create(user=submission.user)
            status_row.last_activity = timezone.now()
            status_row.save(update_fields=["last_activity"])
        
        return Response({
            "success": True,
            "submission_id": submission.id,
            "user_id": submission.user.discord_id,
            "points_awarded": points,
            "total_points": submission.user.total_points,
            "message": "LinkedIn update approved and points awarded"
        })

    def _reject_linkedin(self, request):
        """Reject a LinkedIn submission - OPTIMIZED"""
        submission_id = request.data.get("submission_id")
        reason = request.data.get("reason", "No reason provided")
        
        if not submission_id:
            return Response({"error": "submission_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            submission = LinkedInSubmission.objects.get(id=submission_id, status='pending')
        except LinkedInSubmission.DoesNotExist:
            return Response({"error": "Pending LinkedIn submission not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Update submission status
        submission.status = 'rejected'
        submission.admin_notes = reason
        submission.reviewed_at = timezone.now()
        submission.save()
        
        return Response({
            "success": True,
            "submission_id": submission.id,
            "user_id": submission.user.discord_id,
            "message": "LinkedIn update rejected"
        })

    def _pending_linkedin(self, request):
        """Get all pending LinkedIn submissions - OPTIMIZED"""
        # OPTIMIZED: Use select_related to fetch user data in single query
        pending_submissions = LinkedInSubmission.objects.filter(
            status='pending'
        ).select_related('user').order_by('-submitted_at')
        
        # OPTIMIZED: Build list in single pass, avoiding N+1 queries
        submissions_data = []
        for submission in pending_submissions:
            submissions_data.append({
                "id": submission.id,
                "discord_id": submission.user.discord_id,
                "username": submission.user.username,
                "description": submission.linkedin_url,
                "submitted_at": submission.submitted_at.isoformat(),
            })
        
        return Response({
            "success": True,
            "pending_count": len(submissions_data),  # Use len() instead of count() query
            "submissions": submissions_data
        })


class LinkView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Start linking: issue a 6-digit code valid for 10 minutes."""
        from random import randint
        from datetime import timedelta

        # invalidate previous unused codes for this user
        DiscordLinkCode.objects.filter(user=request.user, used_at__isnull=True).delete()

        # generate 6-digit code
        code = f"{randint(0, 999999):06d}"
        expires_at = timezone.now() + timedelta(minutes=10)
        link = DiscordLinkCode.objects.create(user=request.user, code=code, expires_at=expires_at)
        return Response(DiscordLinkCodeSerializer(link).data)

    def get(self, request):
        """Link status for current user."""
        return Response({
            "linked": bool(request.user.discord_id),
            "discord_id": request.user.discord_id,
        })

    pass


def _check_and_record_unlocks(user: User):
    """Create UserIncentiveUnlock records for any incentives the user just qualified for.
    Idempotent: uses unique_together to avoid duplicates.
    """
    qualifying = Incentive.objects.filter(is_active=True, points_required__lte=user.total_points)
    existing = set(UserIncentiveUnlock.objects.filter(user=user, incentive__in=qualifying).values_list('incentive_id', flat=True))
    to_create = [UserIncentiveUnlock(user=user, incentive=inc) for inc in qualifying if inc.id not in existing]
    if to_create:
        UserIncentiveUnlock.objects.bulk_create(to_create, ignore_conflicts=True)


class FormSubmissionView(APIView):
    """Endpoint to receive Google Form submissions via Apps Script webhook"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.conf import settings
        
        # Check webhook authentication token
        webhook_secret = request.headers.get("X-Form-Secret", "")
        expected_secret = getattr(settings, 'FORM_WEBHOOK_SECRET', None)
        
        if not expected_secret:
            return Response({"error": "Webhook secret not configured"}, status=500)
            
        if webhook_secret != expected_secret:
            return Response({"error": "Unauthorized webhook"}, status=401)

        # Extract form data
        form_data = request.data
        student_email = form_data.get('student_email')
        responses = form_data.get('responses', {})
        timestamp = form_data.get('timestamp')

        if not student_email or not responses:
            return Response({"error": "Missing required form data"}, status=400)

        try:
            # Try to find user by email first, then by discord_id if available
            user = None
            discord_id = responses.get('Discord Username') or responses.get('Discord ID')
            
            if discord_id:
                # Clean discord ID (remove @ symbols, spaces, etc.)
                discord_id = discord_id.strip().replace('@', '').replace('<', '').replace('>', '')
                try:
                    user = User.objects.get(discord_id=discord_id)
                except User.DoesNotExist:
                    pass
            
            if not user:
                try:
                    user = User.objects.get(email=student_email)
                except User.DoesNotExist:
                    # Create new user if not found
                    username = student_email.split('@')[0]
                    user = User.objects.create(
                        username=username,
                        email=student_email,
                        role='student',
                        discord_id=discord_id if discord_id else None
                    )

            # Create or update ReviewRequest
            review_request, created = ReviewRequest.objects.get_or_create(
                student=user,
                status='pending',
                defaults={
                    'form_data': responses,
                    'target_industry': responses.get('Target Industry', ''),
                    'target_role': responses.get('Target Role', ''),
                    'experience_level': responses.get('Experience Level', ''),
                    'preferred_times': self._extract_availability(responses),
                }
            )

            if not created:
                # Update existing pending request with new data
                review_request.form_data = responses
                review_request.target_industry = responses.get('Target Industry', '')
                review_request.target_role = responses.get('Target Role', '')
                review_request.experience_level = responses.get('Experience Level', '')
                review_request.preferred_times = self._extract_availability(responses)
                review_request.save()

            return Response({
                "status": "success",
                "message": f"Form submission received for {student_email}",
                "review_request_id": review_request.id,
                "created": created
            })

        except Exception as e:
            # Log the error but don't expose internal details
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Form submission error: {e}")
            
            return Response({"error": "Internal server error"}, status=500)

    def _extract_availability(self, responses):
        """Extract availability data from form responses"""
        availability = []
        
        # Look for common availability field names
        availability_fields = [
            'Availability', 'Available Times', 'Preferred Times', 
            'When are you available?', 'Available Days/Times'
        ]
        
        for field in availability_fields:
            if field in responses:
                availability_data = responses[field]
                if isinstance(availability_data, str):
                    # Split by common delimiters
                    times = [time.strip() for time in availability_data.replace(',', ';').split(';')]
                    availability.extend(times)
                elif isinstance(availability_data, list):
                    availability.extend(availability_data)
        
        return availability

class ProfessionalAvailabilityFormView(APIView):
    """Endpoint to receive Professional Availability Google Form submissions"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.conf import settings
        
        # Check webhook authentication token
        webhook_secret = request.headers.get("X-Form-Secret", "")
        expected_secret = getattr(settings, 'FORM_WEBHOOK_SECRET', None)
        
        if not expected_secret:
            return Response({"error": "Webhook secret not configured"}, status=500)
            
        if webhook_secret != expected_secret:
            return Response({"error": "Unauthorized webhook"}, status=401)

        # Extract form data
        form_data = request.data
        form_type = form_data.get('form_type')
        response_id = form_data.get('response_id')
        respondent_email = form_data.get('respondent_email')
        responses = form_data.get('responses', {})
        parsed_data = form_data.get('parsed_data', {})
        timestamp = form_data.get('timestamp')

        if form_type != 'professional_availability':
            return Response({"error": "Invalid form type"}, status=400)

        if not response_id or not responses:
            return Response({"error": "Missing required form data"}, status=400)

        try:
            # Find or create professional
            professional_name = parsed_data.get('name', '')
            professional_email = parsed_data.get('email', '')
            
            if not professional_name or not professional_email:
                return Response({"error": "Professional name and email are required"}, status=400)
            
            # Get or create professional
            professional, created = Professional.objects.get_or_create(
                email=professional_email,
                defaults={
                    'name': professional_name,
                    'specialties': parsed_data.get('specializations', ''),
                    'bio': f"{parsed_data.get('professional_title', '')} at {parsed_data.get('company', '')}",
                    'is_active': True
                }
            )
            
            # Update professional info if not created
            if not created:
                professional.name = professional_name
                professional.specialties = parsed_data.get('specializations', professional.specialties)
                professional.bio = f"{parsed_data.get('professional_title', '')} at {parsed_data.get('company', '')}"
                professional.save()

            # Parse availability dates
            try:
                from datetime import datetime
                start_date_str = parsed_data.get('start_date', '')
                end_date_str = parsed_data.get('end_date', '')
                
                if start_date_str and end_date_str:
                    # Try multiple date formats
                    for date_format in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                        try:
                            start_date = datetime.strptime(start_date_str, date_format).date()
                            end_date = datetime.strptime(end_date_str, date_format).date()
                            break
                        except ValueError:
                            continue
                    else:
                        # If no format worked, use a default range
                        from datetime import date, timedelta
                        start_date = date.today()
                        end_date = start_date + timedelta(weeks=4)
                else:
                    # Default to 4 weeks from today
                    from datetime import date, timedelta
                    start_date = date.today()
                    end_date = start_date + timedelta(weeks=4)
                    
            except Exception:
                # Fallback to default dates
                from datetime import date, timedelta
                start_date = date.today()
                end_date = start_date + timedelta(weeks=4)

            # Parse availability slots
            time_slots = parsed_data.get('time_slots', [])
            preferred_days = parsed_data.get('preferred_days', [])
            specific_times = parsed_data.get('specific_times', '')
            
            # Combine structured and free-form availability
            availability_slots = time_slots.copy() if isinstance(time_slots, list) else []
            if specific_times:
                availability_slots.append(specific_times)

            # Create or update availability record
            availability, created = ProfessionalAvailability.objects.update_or_create(
                professional=professional,
                form_response_id=response_id,
                defaults={
                    'form_data': responses,
                    'availability_slots': availability_slots,
                    'preferred_days': preferred_days if isinstance(preferred_days, list) else [],
                    'time_zone': parsed_data.get('timezone', 'UTC'),
                    'start_date': start_date,
                    'end_date': end_date,
                    'notes': parsed_data.get('notes', ''),
                    'is_active': True
                }
            )

            return Response({
                "status": "success",
                "message": f"Professional availability received for {professional_name}",
                "professional_id": professional.id,
                "availability_id": availability.id,
                "created": created,
                "valid_period": f"{start_date} to {end_date}",
                "slots_count": len(availability_slots)
            })

        except Exception as e:
            # Log the error but don't expose internal details
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Professional availability form submission error: {e}")
            
            return Response({"error": "Internal server error"}, status=500)


class DiscordValidationView(APIView):
    """
    Validate Discord username against server membership
    This endpoint is called by the frontend during user registration
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Validate Discord username"""
        serializer = DiscordValidationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        discord_username = serializer.validated_data['discord_username']
        
        # Call the bot to validate server membership
        validation_result = self._validate_with_bot(discord_username)
        
        if validation_result['success']:
            response_data = {
                'valid': validation_result['valid'],
                'message': validation_result['message'],
                'discord_username': discord_username,
                'discord_id': validation_result.get('discord_id')
            }
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({
                'valid': False,
                'message': validation_result['message'],
                'discord_username': discord_username
            }, status=status.HTTP_200_OK)
    
    def _validate_with_bot(self, discord_username):
        """Call Discord REST API directly to validate username against server membership"""
        import requests
        from django.conf import settings
        
        try:
            return self._validate_with_discord_api(discord_username)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error validating Discord username with Discord API: {e}")
            return {
                'success': False,
                'message': 'Unable to validate Discord username at this time. Please try again later.'
            }
    
    def _validate_with_discord_api(self, discord_username):
        """Direct call to Discord REST API for username validation"""
        from django.conf import settings
        import requests
        
        discord_token = getattr(settings, 'DISCORD_TOKEN', '')
        guild_id = getattr(settings, 'DISCORD_GUILD_ID', '')
        
        if not discord_token:
            return {
                'success': False,
                'message': 'Discord integration not configured.'
            }
        
        if not guild_id:
            return {
                'success': False,
                'message': 'Discord server not configured.'
            }
        
        # Search for the user by username (can include discriminator)
        username_parts = discord_username.split('#')
        base_username = username_parts[0]
        discriminator = username_parts[1] if len(username_parts) > 1 else None
        
        try:
            # Call Discord API to search guild members
            headers = {
                "Authorization": f"Bot {discord_token}",
                "Content-Type": "application/json"
            }
            
            # Search for members with the username
            response = requests.get(
                f"https://discord.com/api/v10/guilds/{guild_id}/members/search",
                params={"query": base_username, "limit": 100},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                members = response.json()
                
                # Search through results for exact username match
                for member in members:
                    user = member.get('user', {})
                    member_username = user.get('username', '')
                    member_discriminator = user.get('discriminator', '0000')
                    
                    # Check against unique Discord username
                    if member_username.lower() == base_username.lower():
                        # If discriminator provided, verify it matches
                        if discriminator is not None:
                            if member_discriminator == discriminator:
                                return {
                                    'success': True,
                                    'valid': True,
                                    'message': f"User found in Discord server",
                                    'discord_id': user.get('id'),
                                    'discord_username': f"{member_username}#{member_discriminator}"
                                }
                        else:
                            # No discriminator provided, username match is sufficient
                            return {
                                'success': True,
                                'valid': True,
                                'message': f"User found in Discord server",
                                'discord_id': user.get('id'),
                                'discord_username': f"{member_username}#{member_discriminator}"
                            }
                
                return {
                    'success': True,
                    'valid': False,
                    'message': f"User '{discord_username}' not found in Discord server"
                }
                
            elif response.status_code == 401:
                logger.error("Discord API authentication failed - invalid bot token")
                return {
                    'success': False,
                    'message': 'Discord authentication failed. Please check configuration.'
                }
            elif response.status_code == 403:
                logger.error("Discord API forbidden - bot lacks permissions")
                return {
                    'success': False,
                    'message': 'Discord bot lacks required permissions.'
                }
            else:
                logger.error(f"Discord API error {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'message': f'Discord API error (status {response.status_code})'
                }
                
        except requests.exceptions.Timeout:
            logger.error("Discord API validation timed out")
            return {
                'success': False,
                'message': 'Discord validation timed out. Please try again.'
            }
        except Exception as e:
            logger.error(f"Error calling Discord API: {e}")
            return {
                'success': False,
                'message': 'Unable to connect to Discord API.'
            }


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Simple health check endpoint for deployment monitoring"""
    from django.db import connection
    
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return Response({
            "status": "healthy", 
            "timestamp": timezone.now(),
            "database": "connected",
            "service": "django+discord-bot"
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            "status": "unhealthy", 
            "timestamp": timezone.now(),
            "database": "disconnected",
            "error": str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
