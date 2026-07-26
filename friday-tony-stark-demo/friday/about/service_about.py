from __future__ import annotations

import re
import unicodedata
from calendar import monthrange
from datetime import date

from friday.about.loader_about import load_self_intro_document
from friday.about.schemas_about import AboutMatch


ABOUT_TOPIC_PRIORITY = (
    "developer",
    "birthday",
    "age",
    "capability",
    "architecture",
    "independence",
    "introduction",
)

ABOUT_FALLBACK_TRIGGERS = {
    "introduction": (
        "introduce yourself",
        "who are you",
        "what are you",
        "tell me about yourself",
        "tell me about friday",
        "gioi thieu ve ban",
        "ban la ai",
        "friday la ai",
    ),
    "developer": (
        "who created you",
        "who made you",
        "who is your developer",
        "ai tao ra ban",
        "ai phat trien ban",
    ),
    "birthday": (
        "when were you born",
        "when is your birthday",
        "what is your birthday",
        "when was friday created",
        "ngay sinh cua ban",
        "friday sinh ngay nao",
    ),
    "age": (
        "how old are you",
        "what is your age",
        "ban bao nhieu tuoi",
        "friday bao nhieu tuoi",
    ),
    "capability": (
        "what can you do",
        "what are your capabilities",
        "how can you help me",
        "ban co the lam gi",
        "friday co the lam gi",
        "friday lam duoc gi",
    ),
    "architecture": (
        "how are you built",
        "what is your architecture",
        "how does friday work",
        "friday hoat dong nhu the nao",
        "kien truc cua friday",
    ),
    "independence": (
        "are you the real friday",
        "are you marvel friday",
        "are you tony stark's friday",
        "ban co phai friday cua marvel",
    ),
}


def normalize_about_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value or "")
    without_marks = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    return " ".join(without_marks.lower().split())


def _phrase_matches(message: str, phrase: str) -> bool:
    normalized_message = normalize_about_text(message)
    normalized_phrase = normalize_about_text(phrase)
    if not normalized_phrase:
        return False
    if normalized_phrase in normalized_message:
        return True
    words = [word for word in re.split(r"\W+", normalized_phrase) if len(word) >= 3]
    if len(words) < 2:
        return False
    return all(word in normalized_message for word in words)


def _matching_topic(message: str) -> str | None:
    document = load_self_intro_document()
    for topic in ABOUT_TOPIC_PRIORITY:
        triggers = (
            *document.trigger_groups.get(topic, ()),
            *ABOUT_FALLBACK_TRIGGERS.get(topic, ()),
        )
        if any(_phrase_matches(message, trigger) for trigger in triggers):
            return topic
    return None


def _looks_vietnamese(message: str) -> bool:
    if re.search(r"[ăâđêôơưĂÂĐÊÔƠƯ]", message):
        return True
    normalized = normalize_about_text(message)
    markers = (
        "ban la ai",
        "gioi thieu",
        "ngay sinh",
        "bao nhieu tuoi",
        "ai tao ra",
        "co the lam gi",
        "kien truc",
        "hoat dong nhu the nao",
    )
    return any(marker in normalized for marker in markers)


def _response_candidates(topic: str, response_type: str, language: str) -> tuple[str, ...]:
    requested = normalize_about_text(response_type).replace(" ", "_") or "voice"
    modes = {
        "full": ("full", "voice", "short"),
        "short": ("short", "voice", "full"),
        "voice": ("voice", "short", "full"),
    }.get(requested, (requested, "voice", "short", "full"))
    candidates: list[str] = []
    if language == "vi":
        candidates.extend(f"{topic}_vi_{mode}" for mode in modes)
    candidates.extend(f"{topic}_en_{mode}" for mode in modes)
    if topic == "introduction":
        if language == "vi":
            candidates.extend(f"vi_{mode}" for mode in modes)
        candidates.extend(modes)
    return tuple(dict.fromkeys(candidates))


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _age_response(*, language: str) -> str:
    birthday = date(2026, 4, 15)
    today = date.today()
    if today < birthday:
        if language == "vi":
            return "Ngày 15 tháng 4 năm 2026 là ngày sinh chính thức dự kiến của tôi, boss."
        return "April 15, 2026 is my planned official birthday, boss."

    years = today.year - birthday.year
    anniversary = _add_months(birthday, years * 12)
    if anniversary > today:
        years -= 1
        anniversary = _add_months(birthday, years * 12)
    months = 0
    while _add_months(anniversary, months + 1) <= today:
        months += 1
    month_anchor = _add_months(anniversary, months)
    days = (today - month_anchor).days
    if language == "vi":
        return (
            "Tôi chính thức ra đời vào ngày 15 tháng 4 năm 2026. "
            f"Tính đến hôm nay, tôi được {years} năm, {months} tháng và {days} ngày tuổi, boss."
        )
    return (
        "I was officially born on April 15, 2026. "
        f"As of today, I am {years} years, {months} months, and {days} days old, boss."
    )


def _response_for_topic(
    topic: str,
    *,
    response_type: str,
    language: str,
) -> str:
    if topic == "age":
        return _age_response(language=language)
    document = load_self_intro_document()
    for key in _response_candidates(topic, response_type, language):
        response = document.responses.get(key)
        if response:
            return response.strip()
    return ""


def is_self_intro_request(message: str) -> bool:
    return _matching_topic(message) is not None


def get_friday_self_intro(response_type: str = "voice") -> str:
    return _response_for_topic(
        "introduction",
        response_type=response_type,
        language="en",
    )


def match_about_response(message: str, *, response_type: str = "voice") -> AboutMatch:
    topic = _matching_topic(message)
    if topic is None:
        return AboutMatch(matched=False, response_type=response_type)
    response = _response_for_topic(
        topic,
        response_type=response_type,
        language="vi" if _looks_vietnamese(message) else "en",
    )
    if not response:
        return AboutMatch(matched=False, response_type=response_type)
    return AboutMatch(
        matched=True,
        document_id=load_self_intro_document().id,
        response_type=response_type,
        response=response,
        trigger=topic,
    )
