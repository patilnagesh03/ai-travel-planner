from django.db import models


class ExpenseCategory(models.TextChoices):
    TRANSPORT = "transport", "Transport"
    STAY = "stay", "Stay"
    FOOD = "food", "Food"
    ACTIVITIES = "activities", "Activities"
    SHOPPING = "shopping", "Shopping"
    OTHER = "other", "Other"
