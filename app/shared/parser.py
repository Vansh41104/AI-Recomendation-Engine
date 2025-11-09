import re
from typing import Dict, List
from bs4 import BeautifulSoup
from .config import settings
from .utils import clean_whitespace


def parse_text_sections(soup: BeautifulSoup) -> str:
    chunks: List[str] = []
    selectors = ["p", "li"]
    for selector in selectors:
        for node in soup.select(selector):
            text = clean_whitespace(node.get_text(" ", strip=True))
            if len(text) > 20:
                chunks.append(text)
    return " \n ".join(chunks)


def detect_flags(soup: BeautifulSoup) -> Dict[str, bool]:
    remote = False
    remote_circle = soup.find('span', class_='catalogue__circle')
    if remote_circle:
        classes = remote_circle.get('class', [])
        remote = '-yes' in classes
    else:
        text_lower = soup.get_text(" ", strip=True).lower()
        remote = bool(re.search(r"remote|online|proctoring|virtual", text_lower))
    
    text_lower = soup.get_text(" ", strip=True).lower()
    adaptive = bool(re.search(r"adaptive|ai-powered|ai powered|personalized", text_lower))
    
    return {"adaptive_support": adaptive, "remote_support": remote}


def extract_duration(soup: BeautifulSoup) -> str:
    assessment_length_container = soup.find('h4', string=lambda x: x and 'assessment length' in x.lower())
    if assessment_length_container:
        container_parent = assessment_length_container.parent
        if container_parent:
            duration_text = container_parent.get_text(" ", strip=True)
            match = re.search(r"in minutes\s*=\s*((?:max\s+)?\d+(?:\s*to\s*\d+)?)", duration_text, re.IGNORECASE)
            if match:
                return f"{match.group(1)} minutes"
    
    text = soup.get_text(" ", strip=True)
    duration_match = re.search(
        r"(?:duration|time to complete|completion time|approx\.? time)\s*[:\-–]?\s*([^\n\.]+)",
        text,
        flags=re.IGNORECASE,
    )
    if duration_match:
        sanitized = sanitize_duration(duration_match.group(1))
        if sanitized:
            return sanitized
    quick_match = re.search(r"(\d+\s*(?:minutes|min|hours|hrs))", text, flags=re.IGNORECASE)
    if quick_match:
        return clean_whitespace(quick_match.group(1))
    return ""


def sanitize_duration(raw_value: str) -> str:
    cleaned = clean_whitespace(raw_value)
    if not cleaned:
        return ""

    stop_tokens = [
        "test type", "remote testing", "downloads", "product fact sheet",
        "sample report", "accelerate", "speak to our team",
    ]
    lower_cleaned = cleaned.lower()
    for token in stop_tokens:
        idx = lower_cleaned.find(token)
        if idx != -1:
            cleaned = cleaned[:idx]
            break

    cleaned = cleaned.strip(" -:;,")
    if not cleaned:
        return ""

    match_max = re.search(r"max\s*(\d+)", cleaned, flags=re.IGNORECASE)
    if match_max and "minute" not in cleaned.lower():
        return f"max {match_max.group(1)} minutes"

    return cleaned


def extract_test_types(soup: BeautifulSoup) -> List[str]:
    assessment_section = soup.find('h4', string=lambda x: x and 'assessment length' in x.lower())
    if assessment_section and assessment_section.parent:
        container = assessment_section.parent
        test_type_spans = container.find_all('span', class_='product-catalogue__key')
        if test_type_spans:
            test_types = [span.get_text(strip=True) for span in test_type_spans]
            return sorted(set(test_types))
    
    text = soup.get_text(" ", strip=True).lower()
    type_entries = []
    for letter, keywords in settings.CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            type_entries.append(letter)
    
    return type_entries or ["K"]
