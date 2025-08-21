from django.urls import path, include
from .views import BotIntegrationView, LinkView, FormSubmissionView
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, ActivityViewSet, PointsLogViewSet,
    IncentiveViewSet, RedemptionViewSet, UserStatusViewSet,
    ProfessionalViewSet, ReviewRequestViewSet
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

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/bot/', BotIntegrationView.as_view(), name='bot-integration'),
    path('api/link/start', LinkView.as_view(), name='link-start'),
    path('api/link/status', LinkView.as_view(), name='link-status'),
    path('api/form-submission/', FormSubmissionView.as_view(), name='form-submission'),
] 