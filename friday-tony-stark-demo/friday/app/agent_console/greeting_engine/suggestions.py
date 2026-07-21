from __future__ import annotations

from .periods import DayPeriodName
from .weather import WeatherMood

SCHEDULE_QUESTIONS: dict[DayPeriodName, str] = {
    "morning": "Would you like me to organize today's schedule?",
    "noon": "Would you like me to reorder this afternoon's priorities?",
    "afternoon": "Should I review what remains before the end of the day?",
    "evening": "Would you like a summary of today and a plan for tomorrow?",
    "night": "Should I save your unfinished tasks for tomorrow?",
}

WEATHER_ADVICE: dict[WeatherMood, str] = {
    "rainy": "Indoor, focused work may suit the weather best.",
    "hot": "Stay hydrated and avoid unnecessary outdoor activity during peak heat.",
    "cold": "Keep warm and settle into a steady work rhythm.",
    "pleasant": "The weather looks suitable for a short walk or some fresh air.",
    "cloudy": "A short outdoor break may help if conditions remain dry.",
    "unknown": "Weather details are uncertain, so we can keep the plan flexible.",
}

PERIOD_ADVICE: dict[DayPeriodName, str] = {
    "morning": "Start with the most important task while your energy is fresh.",
    "noon": "Take a light lunch and a short break before returning to work.",
    "afternoon": "Group related tasks and finish them in focused sessions.",
    "evening": "Slow the pace and prepare a clean handoff for tomorrow.",
    "night": "It is late; prioritize rest and save anything unfinished for morning.",
}

MEAL_SUGGESTIONS: dict[DayPeriodName, str] = {
    "morning": "I can also suggest a light breakfast.",
    "noon": "I can suggest a balanced lunch based on the weather.",
    "afternoon": "I can suggest a light snack to maintain your energy.",
    "evening": "I can suggest a light dinner that will not disrupt your rest.",
    "night": "Avoid a heavy meal now; choose a warm drink or a very light snack.",
}


def get_schedule_question(period: DayPeriodName) -> str:
    return SCHEDULE_QUESTIONS[period]


def get_lifestyle_suggestion(period: DayPeriodName, mood: WeatherMood) -> str:
    return f"{WEATHER_ADVICE[mood]} {PERIOD_ADVICE[period]}"


def get_meal_suggestion(period: DayPeriodName) -> str:
    return MEAL_SUGGESTIONS[period]
