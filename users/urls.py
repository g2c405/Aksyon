from django.urls import path
from .views import (
    RegisterView, 
    LogoutView, 
    MeView, 
    AdminUserListView, 
    AdminUserView, 
    LoginView, 
    VerifyEmailView, 
    ForgotPasswordView, 
    ResetPasswordView,
    ChangePasswordView,
    AdminCreateView,
    AdminListView,
    AdminRetrieveUpdateView
)
from rest_framework.authtoken.views import obtain_auth_token
urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("verify-email/<int:user_id>/<str:token>/", VerifyEmailView.as_view(), name="verify-email"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path('me/', MeView.as_view(), name="me"),
    path('admin/', AdminUserListView.as_view(), name="admin-user-list"),
    path('admin/<int:pk>/', AdminUserView.as_view(), name="admin-user-detail"),
    path("privileged-admin/register/",AdminCreateView.as_view(), name="admin-register"),
    path('privileged-admin/', AdminListView.as_view(), name='admin-list'),
    path('privileged-admin/<int:pk>/', AdminRetrieveUpdateView.as_view(), name='privileged-admin-detail')
]