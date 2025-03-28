from urllib.parse import urlparse, urlunparse
from datetime import datetime, timezone


def clean_meeting_link(link: str) -> str:
    parsed = urlparse(link)
    cleaned_link = urlunparse(parsed)
    return cleaned_link


def convert_timestamp_to_utc(js_timestamp):
    return datetime.fromtimestamp(js_timestamp / 1000, tz=timezone.utc)