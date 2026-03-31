"""
URL configuration for the users app.
"""
from django.urls import path

from apps.users.views import (
    ChangePasswordView,
    LoginView,
    LogoutView,
    RegisterView,
    TokenRefreshView,
    UserDetailView,
    UserListView,
    UserProfileView,
)

app_name = 'users'

urlpatterns = [
    # Auth
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Profile
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),

    # Admin management
    path('', UserListView.as_view(), name='user-list'),
    path('<uuid:pk>/', UserDetailView.as_view(), name='user-detail'),
]
