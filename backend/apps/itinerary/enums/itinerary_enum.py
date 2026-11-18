from django.db import models


class ActivityType(models.TextChoices):
    MEAL = "meal", "Meal"
    ATTRACTION = "attraction", "Attraction"
    ACTIVITY = "activity", "Activity"
    TRANSPORT = "transport", "Transport"
    ACCOMMODATION = "accommodation", "Accommodation"
    FREE_TIME = "free_time", "Free Time"
    OTHER = "other", "Other"