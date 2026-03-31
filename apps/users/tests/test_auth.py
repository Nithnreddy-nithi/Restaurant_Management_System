"""
Comprehensive test suite for the Users authentication module.
Tests cover: registration, login, logout, token refresh, profile, RBAC.
"""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import AuditLog, CustomUser, Role


def make_user(email='test@example.com', password='Test@1234', role=Role.WAITER, **kwargs):
    """Helper: create and return a CustomUser."""
    return CustomUser.objects.create_user(email=email, password=password, role=role, **kwargs)


def auth_headers(user):
    """Helper: return Authorization header dict for a given user."""
    refresh = RefreshToken.for_user(user)
    return {'HTTP_AUTHORIZATION': f'Bearer {str(refresh.access_token)}'}


class RegisterViewTests(APITestCase):
    url = '/api/users/register/'

    def test_register_success(self):
        data = {
            'email': 'newuser@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'StrongPass@1',
            'password_confirm': 'StrongPass@1',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(CustomUser.objects.filter(email='newuser@example.com').exists())

    def test_register_duplicate_email(self):
        make_user(email='dup@example.com')
        data = {
            'email': 'dup@example.com',
            'password': 'StrongPass@1',
            'password_confirm': 'StrongPass@1',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password(self):
        data = {
            'email': 'weak@example.com',
            'password': 'password',          # no uppercase, no digit, no special char
            'password_confirm': 'password',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_mismatch(self):
        data = {
            'email': 'mismatch@example.com',
            'password': 'StrongPass@1',
            'password_confirm': 'StrongPass@2',
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_creates_audit_log(self):
        data = {
            'email': 'audit@example.com',
            'password': 'StrongPass@1',
            'password_confirm': 'StrongPass@1',
        }
        self.client.post(self.url, data, format='json')
        user = CustomUser.objects.get(email='audit@example.com')
        self.assertTrue(
            AuditLog.objects.filter(user=user, action=AuditLog.Action.REGISTER).exists()
        )


class LoginViewTests(APITestCase):
    url = '/api/users/login/'

    def setUp(self):
        self.user = make_user(email='login@example.com', password='Test@1234')

    def test_login_success(self):
        response = self.client.post(
            self.url, {'email': 'login@example.com', 'password': 'Test@1234'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password(self):
        response = self.client.post(
            self.url, {'email': 'login@example.com', 'password': 'WrongPass@1'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_email(self):
        response = self.client.post(
            self.url, {'email': 'noone@example.com', 'password': 'Test@1234'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.url, {'email': 'login@example.com', 'password': 'Test@1234'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TokenRefreshViewTests(APITestCase):
    url = '/api/users/token/refresh/'

    def setUp(self):
        self.user = make_user(email='refresh@example.com', password='Test@1234')
        self.refresh_token = str(RefreshToken.for_user(self.user))

    def test_refresh_returns_new_access(self):
        response = self.client.post(self.url, {'refresh': self.refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_refresh_with_invalid_token(self):
        response = self.client.post(self.url, {'refresh': 'invalidtoken'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutViewTests(APITestCase):
    url = '/api/users/logout/'

    def setUp(self):
        self.user = make_user(email='logout@example.com', password='Test@1234')
        self.refresh = RefreshToken.for_user(self.user)

    def test_logout_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(self.refresh.access_token)}')
        response = self.client.post(
            self.url, {'refresh': str(self.refresh)}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertTrue(response.data['success'])

    def test_logout_blacklists_refresh_token(self):
        """After logout, same refresh token must be rejected."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(self.refresh.access_token)}')
        self.client.post(self.url, {'refresh': str(self.refresh)}, format='json')

        # Try refreshing with the now-blacklisted token
        response = self.client.post('/api/users/token/refresh/', {'refresh': str(self.refresh)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_requires_authentication(self):
        response = self.client.post(self.url, {'refresh': str(self.refresh)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserProfileViewTests(APITestCase):
    url = '/api/users/profile/'

    def setUp(self):
        self.user = make_user(
            email='profile@example.com',
            password='Test@1234',
            first_name='Jane',
            last_name='Doe',
        )

    def test_get_profile_authenticated(self):
        self.client.credentials(**auth_headers(self.user))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['email'], 'profile@example.com')

    def test_get_profile_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_profile(self):
        self.client.credentials(**auth_headers(self.user))
        response = self.client.patch(self.url, {'first_name': 'Janet'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['first_name'], 'Janet')

    def test_patch_profile_cannot_change_role(self):
        """Non-admin users should not be able to change their own role."""
        self.client.credentials(**auth_headers(self.user))
        response = self.client.patch(self.url, {'role': Role.ADMIN}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.role, Role.ADMIN)


class ChangePasswordViewTests(APITestCase):
    url = '/api/users/change-password/'

    def setUp(self):
        self.user = make_user(email='chpw@example.com', password='OldPass@1')

    def test_change_password_success(self):
        self.client.credentials(**auth_headers(self.user))
        response = self.client.post(self.url, {
            'old_password': 'OldPass@1',
            'new_password': 'NewPass@2',
            'new_password_confirm': 'NewPass@2',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass@2'))

    def test_change_password_wrong_old(self):
        self.client.credentials(**auth_headers(self.user))
        response = self.client.post(self.url, {
            'old_password': 'WrongOld@1',
            'new_password': 'NewPass@2',
            'new_password_confirm': 'NewPass@2',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_weak_new(self):
        self.client.credentials(**auth_headers(self.user))
        response = self.client.post(self.url, {
            'old_password': 'OldPass@1',
            'new_password': 'weak',
            'new_password_confirm': 'weak',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AdminUserListViewTests(APITestCase):
    list_url = '/api/users/'

    def setUp(self):
        self.admin = make_user(email='admin@example.com', password='Admin@1234', role=Role.ADMIN)
        self.waiter = make_user(email='waiter@example.com', password='Waiter@1234', role=Role.WAITER)

    def test_admin_can_list_users(self):
        self.client.credentials(**auth_headers(self.admin))
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)

    def test_non_admin_cannot_list_users(self):
        self.client.credentials(**auth_headers(self.waiter))
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list_users(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_deactivate_user(self):
        self.client.credentials(**auth_headers(self.admin))
        response = self.client.delete(f'{self.list_url}{self.waiter.pk}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.waiter.refresh_from_db()
        self.assertFalse(self.waiter.is_active)
