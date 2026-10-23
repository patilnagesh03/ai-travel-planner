"""
Builds the prompt that is sent to the model.

The prompt has one job: give the model everything it needs, and nothing it
must not invent. The model is given:

* the trip (destination, dates, travellers, budget);
* the travel preferences and interests;
* the list of places it is allowed to use, each with a stable id.

The stable id is the important part. Every activity the model proposes must
reference one of the ids we supplied, so the model can only ever talk about
places we have actually found. It cannot invent a restaurant that does not
exist, and it never has to state a coordinate.
"""

from backend.apps.itinerary.enums import ActivityType
from backend.apps.trips.enums import TravelPace


# How many activities a day should hold, per travel pace.
ITEMS_PER_DAY_BY_PACE = {
    TravelPace.SLOW: 3,
    TravelPace.MODERATE: 4,
    TravelPace.FAST: 6,
}

DEFAULT_ITEMS_PER_DAY = 4


SYSTEM_PROMPT = (
    "You are a careful travel planner. You plan realistic day-by-day "
    "itineraries using only the places you are given. "
    "You always answer with a single JSON object and nothing else."
)


class PromptService:

    @staticmethod
    def build_system_prompt():
        return SYSTEM_PROMPT

    @staticmethod
    def items_per_day(pace):
        """Return how many activities a day should hold for a pace."""

        if not pace:
            return DEFAULT_ITEMS_PER_DAY

        return ITEMS_PER_DAY_BY_PACE.get(
            pace,
            DEFAULT_ITEMS_PER_DAY,
        )

    @staticmethod
    def build_prompt(trip, preferences=None, places=None):
        """Build the user prompt for one trip."""

        places = places or []

        lines = []

        lines.append("Plan a day-by-day itinerary for the following trip.")
        lines.append("")

        lines.append("TRIP")
        lines.append("- Title: {title}".format(title=trip.title))
        lines.append(
            "- Destination: {destination}".format(
                destination=trip.destination,
            )
        )
        lines.append(
            "- Dates: {start} to {end} ({days} day(s))".format(
                start=trip.start_date.isoformat(),
                end=trip.end_date.isoformat(),
                days=PromptService.trip_length(trip),
            )
        )
        lines.append(
            "- Travellers: {travellers}".format(
                travellers=trip.travelers,
            )
        )
        lines.append(
            "- Budget: {budget} {currency}".format(
                budget=trip.budget,
                currency=trip.currency,
            )
        )

        lines.append("")
        lines.append("PREFERENCES")
        lines.append(
            PromptService._preference_lines(preferences),
        )

        lines.append("")
        lines.append("PLACES YOU MAY USE")
        lines.append(
            "These are the only places you may schedule. Every activity "
            "must reference one of their `id` values."
        )

        if places:
            for place in places:
                lines.append(
                    "- {id} | {name} | {category} | {address}".format(
                        id=place.source_id,
                        name=place.name,
                        category=place.category.value,
                        address=place.address or "address unknown",
                    )
                )
        else:
            lines.append(
                "- (no places were found for this destination)"
            )

        lines.append("")
        lines.append("RULES")
        lines.append(
            "- Produce exactly {days} day(s), one entry in `days` per "
            "day, in order.".format(
                days=PromptService.trip_length(trip),
            )
        )
        lines.append(
            "- Each day must contain about {items} activities.".format(
                items=PromptService.items_per_day(
                    getattr(preferences, "pace", None),
                ),
            )
        )
        lines.append(
            "- Use realistic times in 24 hour `HH:MM` format, for example "
            "\"09:30\" and \"11:00\". Times may be left out."
        )
        lines.append(
            "- Vary the `activity_type` across the day. Allowed values: "
            "{types}.".format(
                types=", ".join(
                    choice.value
                    for choice in ActivityType
                    if choice != ActivityType.OTHER
                ),
            )
        )
        lines.append(
            "- Only use places from the list above. Never invent a place."
        )
        lines.append(
            "- Do not include dates. The dates are assigned afterwards."
        )
        lines.append(
            "- Do not include coordinates. They are taken from the place."
        )

        lines.append("")
        lines.append("ANSWER FORMAT")
        lines.append(
            "Reply with a single JSON object and nothing else, in exactly "
            "this shape:"
        )
        lines.append("{")
        lines.append('  "title": "Short itinerary title",')
        lines.append('  "description": "One or two sentences.",')
        lines.append('  "days": [')
        lines.append("    {")
        lines.append('      "items": [')
        lines.append("        {")
        lines.append('          "title": "Activity title",')
        lines.append('          "description": "What to do there.",')
        lines.append('          "start_time": "09:30",')
        lines.append('          "end_time": "11:00",')
        lines.append('          "activity_type": "attraction",')
        lines.append('          "place": "the id of a place from the list"')
        lines.append("        }")
        lines.append("      ]")
        lines.append("    }")
        lines.append("  ]")
        lines.append("}")

        return "\n".join(lines)

    @staticmethod
    def trip_length(trip):
        """Return the number of days in the trip."""

        return (trip.end_date - trip.start_date).days + 1

    @staticmethod
    def _preference_lines(preferences):
        if preferences is None:
            return "- (no preferences were recorded)"

        lines = []

        lines.append(
            "- Travel style: {style}".format(
                style=preferences.travel_style,
            )
        )

        if preferences.accommodation:
            lines.append(
                "- Accommodation: {accommodation}".format(
                    accommodation=preferences.accommodation,
                )
            )

        lines.append("- Pace: {pace}".format(pace=preferences.pace))

        interests = list(preferences.interests.all())

        if interests:
            lines.append(
                "- Interests: {interests}".format(
                    interests=", ".join(
                        interest.name for interest in interests
                    ),
                )
            )
        else:
            lines.append("- Interests: (none recorded)")

        return "\n".join(lines)


__all__ = [
    "PromptService",
    "ITEMS_PER_DAY_BY_PACE",
    "DEFAULT_ITEMS_PER_DAY",
    "SYSTEM_PROMPT",
]
