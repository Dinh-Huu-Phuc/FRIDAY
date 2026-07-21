from __future__ import annotations

NEWS_API_ENDPOINT = "https://newsdata.io/api/1/latest"
DEFAULT_NEWS_LANGUAGE = "en"
DEFAULT_NEWS_COUNTRY = "vn"
DEFAULT_NEWS_LIMIT = 6
DEFAULT_NEWS_REQUEST_TIMEOUT = 8.0
MAX_NEWS_LIMIT = 20
NEWS_INTENT_KEYWORDS = ("news", "latest news", "news update", "breaking news", "headlines", "news summary")
TOPIC_ALIAS_TO_API_CATEGORY = {
    "world": "world", "international": "world", "global": "world",
    "finance": "business", "business": "business", "stocks": "business", "investment": "business",
    "technology": "technology", "tech": "technology", "ai": "technology", "artificial intelligence": "technology",
    "science": "science", "sports": "sports", "entertainment": "entertainment",
    "health": "health", "medicine": "health", "politics": "politics",
}
COUNTRY_ALIAS_TO_CODE = {
    "vietnam": "vn", "vn": "vn", "united states": "us", "usa": "us", "us": "us",
    "united kingdom": "gb", "uk": "gb", "japan": "jp", "south korea": "kr",
    "korea": "kr", "singapore": "sg", "thailand": "th",
}
LANGUAGE_ALIAS_TO_CODE = {"english": "en", "en-us": "en", "en-gb": "en"}
