from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.db import transaction, models
from django.utils import timezone
from .models import User, Activity, PointsLog, Incentive, Redemption, UserStatus, UserIncentiveUnlock, DiscordLinkCode, Professional, ReviewRequest, ScheduledSession, ProfessionalAvailability
from .serializers import (
    UserSerializer, ActivitySerializer, PointsLogSerializer,
    IncentiveSerializer, RedemptionSerializer, UserStatusSerializer, DiscordLinkCodeSerializer,
    ProfessionalSerializer, ReviewRequestSerializer, ReviewRequestCreateSerializer,
    ScheduledSessionSerializer, ProfessionalAvailabilitySerializer
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        """Register a new user"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(request.data.get('password'))
            user.save()
            
            # Create user status
            UserStatus.objects.create(user=user)
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': serializer.data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
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
    
    @action(detail=False, methods=['get'])
    def profile(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
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
            
            return Response({
                'message': f'Added {activity.points_value} points for {activity.name}',
                'total_points': user.total_points,
                'points_log': PointsLogSerializer(points_log).data
            })
            
        except Activity.DoesNotExist:
            return Response({'error': 'Activity not found'}, status=status.HTTP_404_NOT_FOUND)

class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Activity.objects.filter(is_active=True)
    serializer_class = ActivitySerializer
    permission_classes = [permissions.AllowAny]

class PointsLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PointsLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only see their own points logs"""
        if self.request.user.role == 'admin':
            return PointsLog.objects.all()
        return PointsLog.objects.filter(user=self.request.user)

class IncentiveViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Incentive.objects.filter(is_active=True)
    serializer_class = IncentiveSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

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

        return Response({
            "message": f"Added {activity.points_value} points for {activity.name}",
            "total_points": user.total_points,
            "points_log_id": points_log.id,
        })

    def _link_discord(self, request):
        code = request.data.get("code")
        discord_id = request.data.get("discord_id")
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
            user.discord_id = str(discord_id)
            user.save(update_fields=["discord_id"])
            link.used_at = timezone.now()
            link.save(update_fields=["used_at"])

        return Response({"linked": True, "discord_id": str(discord_id)})

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
        page = int(request.data.get("page", 1))
        page_size = int(request.data.get("page_size", 10))
        qs = User.objects.exclude(discord_id__isnull=True).exclude(discord_id="").order_by('-total_points')
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        items = [
            {
                "position": (page_obj.start_index() + idx),
                "discord_id": u.discord_id,
                "username": u.username,
                "total_points": u.total_points,
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
