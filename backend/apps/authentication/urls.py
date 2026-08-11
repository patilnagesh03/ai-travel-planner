from django.urls import path

from backend.apps.authentication.views.register_view import RegisterView
from backend.apps.authentication.views.login_view import LoginView
from backend.apps.authentication.views.profile_view import ProfileView
from backend.apps.authentication.views.refresh_token_view import RefreshTokenView
from backend.apps.authentication.views.logout_view import LogoutView
from backend.apps.authentication.views.change_password_view import ChangePasswordView

urlpatterns = [
    path(
        "signup/",
        RegisterView.as_view(),
        name="signup",
    ),

    path(
        "signin/",
        LoginView.as_view(),
        name="signin",
    ),

    path(
        "profile/",
        ProfileView.as_view(),
        name="profile",
    ),

    path(
        "refresh-token/",
        RefreshTokenView.as_view(),
        name="refresh-token",
    ),

    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),

    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),


]