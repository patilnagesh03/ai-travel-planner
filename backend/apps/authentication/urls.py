from django.urls import path

from backend.apps.authentication.views.register_view import RegisterView
from backend.apps.authentication.views.login_view import LoginView
from backend.apps.authentication.views.profile_view import ProfileView

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


]