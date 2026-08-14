from django.db import models

class TravelStyle(models.TextChoices):
    RELAXED = "relaxed", "Relaxed"
    BALANCED = "balanced", "Balanced"
    ADVENTUROUS = "adventurous", "Adventurous"


class AccommodationType(models.TextChoices):
    BUDGET = "budget", "Budget"
    MID_RANGE = "mid_range", "Mid-range"
    LUXURY = "luxury", "Luxury"


class TravelPace(models.TextChoices):
    SLOW = "slow", "Slow"
    MODERATE = "moderate", "Moderate"
    FAST = "fast", "Fast"