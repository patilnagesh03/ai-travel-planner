from django.urls import path

from backend.apps.authentication.views.register_view import RegisterView

urlpatterns = [
    path(
        "signup/",
        RegisterView.as_view(),
        name="signup",
    ),
]