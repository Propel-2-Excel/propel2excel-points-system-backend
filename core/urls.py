from django.urls import path, include
from .views import BotIntegrationView
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, ActivityViewSet, PointsLogViewSet,
    IncentiveViewSet, RedemptionViewSet, UserStatusViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'activities', ActivityViewSet)
router.register(r'points-logs', PointsLogViewSet, basename='pointslog')
router.register(r'incentives', IncentiveViewSet)
router.register(r'redemptions', RedemptionViewSet, basename='redemption')
router.register(r'user-status', UserStatusViewSet, basename='userstatus')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/bot/', BotIntegrationView.as_view(), name='bot-integration'),
] 