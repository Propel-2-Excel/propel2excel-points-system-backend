from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import User, Activity, PointsLog, Incentive, Redemption, UserStatus

User = get_user_model()

class PointsSystemTestCase(APITestCase):
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test activities with unique types (within 20 char limit)
        self.resume_activity = Activity.objects.create(
            name="Test Resume Upload",
            activity_type="test_resume",
            points_value=50,
            description="Upload your resume"
        )
        
        self.event_activity = Activity.objects.create(
            name="Test Event Attendance",
            activity_type="test_event",
            points_value=30,
            description="Attend a career event"
        )
        
        # Create test incentive
        self.incentive = Incentive.objects.create(
            name="Test Resume Review",
            description="Get your resume reviewed by a professional",
            points_required=100,
            sponsor="Career Services"
        )
        
        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role="student"
        )
        
        # Create user status
        self.user_status = UserStatus.objects.create(user=self.user)

    def test_user_registration(self):
        """Test user registration endpoint"""
        url = reverse('user-register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'role': 'student'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)

    def test_user_login(self):
        """Test user login endpoint"""
        url = reverse('user-login')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)

    def test_add_points(self):
        """Test adding points to a user"""
        self.client.force_authenticate(user=self.user)
        url = reverse('user-add-points', kwargs={'pk': self.user.pk})
        data = {
            'activity_type': 'test_resume',
            'details': 'Test resume upload'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_points'], 50)
        
        # Verify points log was created
        points_log = PointsLog.objects.filter(user=self.user).first()
        self.assertIsNotNone(points_log)
        self.assertEqual(points_log.points_earned, 50)

    def test_redeem_incentive(self):
        """Test redeeming an incentive"""
        # First add points to user
        self.user.total_points = 150
        self.user.save()
        
        self.client.force_authenticate(user=self.user)
        url = reverse('redemption-redeem')
        data = {
            'incentive_id': self.incentive.id
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['remaining_points'], 50)
        
        # Verify redemption was created
        redemption = Redemption.objects.filter(user=self.user).first()
        self.assertIsNotNone(redemption)
        self.assertEqual(redemption.points_spent, 100)

    def test_insufficient_points_for_redemption(self):
        """Test redemption with insufficient points"""
        self.client.force_authenticate(user=self.user)
        url = reverse('redemption-redeem')
        data = {
            'incentive_id': self.incentive.id
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient points', response.data['error'])

    def test_get_user_profile(self):
        """Test getting user profile"""
        self.client.force_authenticate(user=self.user)
        url = reverse('user-profile')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

    def test_get_activities(self):
        """Test getting available activities"""
        url = reverse('activity-list')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have at least our 2 test activities plus any existing ones
        self.assertGreaterEqual(len(response.data), 2)

    def test_get_incentives(self):
        """Test getting available incentives"""
        self.client.force_authenticate(user=self.user)
        url = reverse('incentive-list')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have at least our 1 test incentive plus any existing ones
        self.assertGreaterEqual(len(response.data), 1)

class ModelTestCase(TestCase):
    def test_user_creation(self):
        """Test user model creation"""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            role="student"
        )
        
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.role, "student")
        self.assertEqual(user.total_points, 0)

    def test_activity_creation(self):
        """Test activity model creation"""
        activity = Activity.objects.create(
            name="Test Activity",
            activity_type="test_activity",
            points_value=25
        )
        
        self.assertEqual(activity.name, "Test Activity")
        self.assertEqual(activity.points_value, 25)
        self.assertTrue(activity.is_active)

    def test_points_log_creation(self):
        """Test points log creation"""
        user = User.objects.create_user(username="testuser", password="testpass")
        activity = Activity.objects.create(
            name="Test Activity",
            activity_type="test_activity",
            points_value=25
        )
        
        points_log = PointsLog.objects.create(
            user=user,
            activity=activity,
            points_earned=25,
            details="Test points"
        )
        
        self.assertEqual(points_log.points_earned, 25)
        self.assertEqual(points_log.user, user)
        self.assertEqual(points_log.activity, activity)
