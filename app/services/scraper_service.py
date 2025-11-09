import time
from pathlib import Path
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
import pandas as pd
from app.shared.config import settings
from app.shared.models import Assessment
from app.shared.utils import fetch_html, normalize_url, clean_whitespace
from app.shared.parser import parse_text_sections, detect_flags, extract_duration, extract_test_types


class ScraperService:
    
    def __init__(self):
        self.session = requests.Session()
    
    def parse_assessment(self, url: str) -> Optional[Assessment]:
        try:
            html = fetch_html(url, session=self.session)
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
    
    def load_seed_urls(self, seed_path: Path) -> List[str]:
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
        self,
        limit: Optional[int] = None,
        seed_urls: Optional[List[str]] = None
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
            assessment = self.parse_assessment(url)
            if assessment:
                assessments.append(assessment)
            time.sleep(settings.REQUEST_DELAY_SECONDS)
        
        return assessments
    
    def scrape_and_save_from_dataset(
        self,
        dataset_path: str,
        limit: Optional[int] = None,
        output_path: str = "data/shl_assessments.csv"
    ) -> dict:

        seed_urls = self.load_seed_urls(Path(dataset_path))
        
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
            assessments = self.scrape_assessments(
                limit=limit,
                seed_urls=seed_urls
            )
            
            if not assessments:
                return {
                    "message": "No assessments scraped",
                    "saved": False,
                    "unique_urls": len(seed_urls)
                }

            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            df = pd.DataFrame([
                assessment.to_dict(settings.TEST_TYPE_DESCRIPTIONS)
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
    
    def close(self):
        """Close scraper session"""
        self.session.close()
