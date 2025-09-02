from django.urls import path, include
from .views import (
    BotIntegrationView, LinkView, FormSubmissionView, ProfessionalAvailabilityFormView, DiscordValidationView,
    DashboardStatsView, PointsTimelineView, LeaderboardView, RewardsAvailableView, RedeemRewardView, RedemptionHistoryView,
    UnifiedActivityFeedView, health_check
)
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, ActivityViewSet, PointsLogViewSet,
    IncentiveViewSet, RedemptionViewSet, UserStatusViewSet,
    ProfessionalViewSet, ReviewRequestViewSet, ScheduledSessionViewSet, ProfessionalAvailabilityViewSet,
    UserPreferencesViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'activities', ActivityViewSet)
router.register(r'points-logs', PointsLogViewSet, basename='pointslog')
router.register(r'incentives', IncentiveViewSet)
router.register(r'redemptions', RedemptionViewSet, basename='redemption')
router.register(r'user-status', UserStatusViewSet, basename='userstatus')
router.register(r'professionals', ProfessionalViewSet)
router.register(r'review-requests', ReviewRequestViewSet, basename='reviewrequest')
router.register(r'scheduled-sessions', ScheduledSessionViewSet, basename='scheduledsession')
router.register(r'professional-availability', ProfessionalAvailabilityViewSet, basename='professionalavailability')
router.register(r'user-preferences', UserPreferencesViewSet, basename='userpreferences')

urlpatterns = [
    # IMPORTANT: Specific API endpoints MUST come BEFORE router.urls to avoid conflicts
    
    # Health check endpoint
    path('health/', health_check, name='health-check'),
    
    # New frontend API endpoints
    path('api/dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('api/points/timeline/', PointsTimelineView.as_view(), name='points-timeline'),
    path('api/leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    path('api/rewards/available/', RewardsAvailableView.as_view(), name='rewards-available'),
    path('api/rewards/redeem/', RedeemRewardView.as_view(), name='redeem-reward'),
    path('api/redemptions/history/', RedemptionHistoryView.as_view(), name='redemption-history'),
    path('api/activity/feed/', UnifiedActivityFeedView.as_view(), name='unified-activity-feed'),
    
    # Existing endpoints
    path('api/bot/', BotIntegrationView.as_view(), name='bot-integration'),
    path('api/validate-discord-user/', DiscordValidationView.as_view(), name='discord-validation'),
    path('api/link/start', LinkView.as_view(), name='link-start'),
    path('api/link/status', LinkView.as_view(), name='link-status'),
    path('api/form-submission/', FormSubmissionView.as_view(), name='form-submission'),
    path('api/forms/professional-availability/', ProfessionalAvailabilityFormView.as_view(), name='professional-availability-form'),
    
    # Router URLs (MUST come last to avoid conflicts with specific endpoints)
    path('api/', include(router.urls)),
] 