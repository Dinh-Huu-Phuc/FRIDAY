"""Shared Windows app launcher domain service."""

from friday.app.windows_launcher.intent import extract_windows_app_query
from friday.app.windows_launcher.service import open_app, search_apps

__all__ = ["extract_windows_app_query", "open_app", "search_apps"]
