import re
import hashlib
import requests
from .config import settings


def fetch_html(url: str, session: requests.Session | None = None) -> str:
    requester = session or requests
    response = requester.get(
        url, 
        headers={"User-Agent": settings.USER_AGENT}, 
        timeout=settings.REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.text


def normalize_url(url: str) -> str:
    if url.startswith("http"):
        return url
    return settings.BASE_URL.rstrip("/") + "/" + url.lstrip("/")


def clean_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def slugify(value: str) -> str:
    safe = (
        value.lower()
        .replace("https://", "")
        .replace("http://", "")
        .replace("/", "-")
        .replace("_", "-")
    )
    safe = re.sub(r"[^a-z0-9-]", "", safe)
    safe = re_collapse_hyphens(safe)

    hash_suffix = hashlib.md5(value.encode()).hexdigest()[:8]
    
    if len(safe) > 48:
        return f"{safe[:48]}-{hash_suffix}"
    else:
        return f"{safe}-{hash_suffix}"


def re_collapse_hyphens(value: str) -> str:
    result = []
    previous_hyphen = False
    for char in value:
        if char == "-":
            if not previous_hyphen:
                result.append(char)
            previous_hyphen = True
        else:
            previous_hyphen = False
            result.append(char)
    return "".join(result).strip("-")


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    try:
        import pandas as pd
        if pd.isna(value):
            return False
    except ImportError:
        pass
    normalized = str(value).strip().lower()
    return normalized in {"true", "1", "yes", "y"}
