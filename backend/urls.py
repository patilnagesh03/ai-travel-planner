"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from backend.apps.trips.views.interest_view import InterestListView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path(
        'api/auth/', 
        include("backend.apps.authentication.urls")
    ),

    path(
        "api/v1/interests/",
        InterestListView.as_view(),
        name="interest-list",
    ),

     path(
        "api/v1/trips/",
        include("backend.apps.trips.urls"),
    ),

    path(
        "api/v1/",
        include("backend.apps.itinerary.urls"),
    ),

    path(
        "api/v1/",
        include("backend.apps.expenses.urls"),
    ),

    path(
        "api/v1/",
        include("backend.apps.notifications.urls"),
    ),

    path(
        "api/v1/",
        include("backend.apps.integrations.urls"),
    ),

    path(
        "api/v1/",
        include("backend.apps.ai.urls"),
    ),
]

# In development Django serves uploaded media itself. In production this is
# the web server's job (or a storage backend), so the route is DEBUG-only
# and never becomes a way to read files on the server.
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
