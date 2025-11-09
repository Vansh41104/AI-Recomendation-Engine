import time
import re
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
import pandas as pd


BASE_URL = "https://www.shl.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
REQUEST_DELAY_SECONDS = 1.0
REQUEST_TIMEOUT = 20

CATEGORY_KEYWORDS = {
    "A": [
        "ability", "aptitude", "cognitive", "reasoning", 
        "numerical", "verbal", "quantitative", "logical"
    ],
    "B": [
        "situational judgement", "situational judgment", "biodata",
        "situational", "scenario", "judgement", "judgment"
    ],
    "C": [
        "competency", "competencies", "competence", "capability",
        "leadership", "managerial", "collaboration"
    ],
    "D": [
        "development", "360", "feedback", "coaching",
        "growth", "learning journey"
    ],
    "E": [
        "assessment exercise", "assessment centre", "assessment center",
        "case study", "in-basket", "inbasket", "role-play"
    ],
    "K": [
        "knowledge", "skill", "skills", "technical", "coding",
        "programming", "automation", "sql", "python", "excel",
        "marketing", "finance", "sales", "data", "analysis"
    ],
    "P": [
        "personality", "behavior", "behaviour", "trait",
        "motivation", "opq", "preferences"
    ],
    "S": [
        "simulation", "simulated", "virtual experience", "immersive"
    ],
}

TEST_TYPE_DESCRIPTIONS = {
    "A": "Ability & Aptitude Tests",
    "B": "Behavioral & Situational Judgment Tests",
    "C": "Competency Assessments",
    "D": "Development & Feedback Tools",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills Tests",
    "P": "Personality Assessments",
    "S": "Simulations & Interactive Assessments",
}


@dataclass
class Assessment:
    url: str
    adaptive_support: bool
    description: str
    duration: str
    remote_support: bool
    test_type: List[str]

    def to_dict(self, test_type_descriptions: dict[str, str]) -> dict[str, object]:
        test_type_with_desc = []
        for letter in self.test_type:
            desc = test_type_descriptions.get(letter, "Unknown")
            test_type_with_desc.append(f"{letter}: {desc}")
        
        return {
            "url": self.url,
            "adaptive_support": bool(self.adaptive_support),
            "description": self.description.strip(),
            "duration": self.duration.strip(),
            "remote_support": bool(self.remote_support),
            "test_type": "; ".join(test_type_with_desc) if test_type_with_desc else "",
        }


def fetch_html(url: str, session: requests.Session | None = None) -> str:
    requester = session or requests
    response = requester.get(
        url, 
        headers={"User-Agent": USER_AGENT}, 
        timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.text


def normalize_url(url: str) -> str:
    if url.startswith("http"):
        return url
    return BASE_URL.rstrip("/") + "/" + url.lstrip("/")


def clean_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_text_sections(soup: BeautifulSoup) -> str:
    chunks: List[str] = []
    selectors = ["p", "li"]
    for selector in selectors:
        for node in soup.select(selector):
            text = clean_whitespace(node.get_text(" ", strip=True))
            if len(text) > 20:
                chunks.append(text)
    return " \n ".join(chunks)


def detect_flags(soup: BeautifulSoup) -> dict[str, bool]:
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
    for letter, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            type_entries.append(letter)
    
    return type_entries or ["K"]


def parse_assessment(url: str, session: requests.Session) -> Optional[Assessment]:
    try:
        html = fetch_html(url, session=session)
    except Exception as exc:
        return None

    soup = BeautifulSoup(html, "html.parser")
    description = ""

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        description = meta_desc["content"]
    
    if not description:
        intro = soup.find(
            ["p", "div"],
            attrs={"class": lambda x: x and "intro" in x.lower() or "summary" in x.lower()}
        )
        if intro:
            description = intro.get_text(" ", strip=True)
    
    if not description:
        description = clean_whitespace(parse_text_sections(soup)[:500])

    description = description[:1000]
    flag_values = detect_flags(soup)
    duration = extract_duration(soup)
    test_types = extract_test_types(soup)

    return Assessment(
        url=url,
        adaptive_support=flag_values["adaptive_support"],
        description=description,
        duration=duration,
        remote_support=flag_values["remote_support"],
        test_type=test_types or ["Unspecified"],
    )


def load_seed_urls(seed_path: Path) -> List[str]:
    if not seed_path.exists():
        return []

    try:
        df = pd.read_csv(seed_path)
    except Exception as exc:
        return []

    column_candidates = ["Assessment_url", "assessment_url", "url", "URL"]
    url_column = next((col for col in column_candidates if col in df.columns), None)
    
    if not url_column:
        return []

    urls = []
    for value in df[url_column].dropna().tolist():
        cleaned = str(value).strip()
        if not cleaned or "shl.com" not in cleaned:
            continue
        normalized = normalize_url(cleaned)
        if normalized not in urls:
            urls.append(normalized)

    return urls


def scrape_assessments(
    limit: Optional[int] = None,
    seed_urls: Optional[List[str]] = None,
    session: requests.Session = None
) -> List[Assessment]:
    candidate_urls: List[str] = []

    if seed_urls:
        candidate_urls.extend(seed_urls)

    seen: set[str] = set()
    deduped: List[str] = []
    for url in candidate_urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)

    candidate_urls = deduped
    
    if not candidate_urls:
        return []

    if limit:
        candidate_urls = candidate_urls[:limit]

    assessments: List[Assessment] = []
    for idx, url in enumerate(candidate_urls, start=1):
        assessment = parse_assessment(url, session)
        if assessment:
            assessments.append(assessment)
        time.sleep(REQUEST_DELAY_SECONDS)
    
    return assessments


def scrape_and_save_from_dataset(
    dataset_path: str,
    limit: Optional[int] = None,
    output_path: str = "data/shl_assessments.csv",
    session: requests.Session = None
) -> dict:

    seed_urls = load_seed_urls(Path(dataset_path))
    
    if not seed_urls:
        return {
            "message": "No valid URLs found in dataset",
            "saved": False,
            "unique_urls": 0
        }
    
    output_path_obj = Path(output_path)
    if not output_path_obj.is_absolute():
        output_path_obj = Path("data") / output_path_obj.name

    try:
        assessments = scrape_assessments(
            limit=limit,
            seed_urls=seed_urls,
            session=session
        )
        
        if not assessments:
            return {
                "message": "No assessments scraped",
                "saved": False,
                "unique_urls": len(seed_urls)
            }

        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        df = pd.DataFrame([
            assessment.to_dict(TEST_TYPE_DESCRIPTIONS)
            for assessment in assessments
        ])
        df.to_csv(output_path_obj, index=False)
        
        return {
            "message": f"Successfully saved {len(df)} assessments",
            "path": str(output_path_obj),
            "count": len(df),
            "unique_urls": len(seed_urls),
            "saved": True
        }
    
    except Exception as e:
        raise


if __name__ == "__main__":
    session = requests.Session()
    dataset_path = "dataset/Gen_AI Dataset.csv"
    
    result = scrape_and_save_from_dataset(
        dataset_path=dataset_path,
        limit=5,
        output_path="data/shl_assessments.csv",
        session=session
    )
    
    print(f"Scraping result: {result}")
    session.close()
