import os
from pydantic_settings import BaseSettings


class SharedSettings(BaseSettings):
    BASE_URL: str = "https://www.shl.com"
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
    REQUEST_DELAY_SECONDS: float = 1.0
    REQUEST_TIMEOUT: int = 20
    
    CHROMA_COLLECTION_NAME: str = os.environ.get("CHROMA_COLLECTION_NAME", "shl_assessments")
    CHROMA_PERSIST_DIR: str = os.environ.get("CHROMA_PERSIST_DIR", "chroma_db")
    SENTENCE_TRANSFORMER_MODEL: str = os.environ.get("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
    
    CATEGORY_KEYWORDS: dict[str, list[str]] = {
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
    
    TEST_TYPE_DESCRIPTIONS: dict[str, str] = {
        "A": "Ability & Aptitude Tests",
        "B": "Behavioral & Situational Judgment Tests",
        "C": "Competency Assessments",
        "D": "Development & Feedback Tools",
        "E": "Assessment Exercises",
        "K": "Knowledge & Skills Tests",
        "P": "Personality Assessments",
        "S": "Simulations & Interactive Assessments",
    }
    
    GATEWAY_HOST: str = os.environ.get("GATEWAY_HOST", "0.0.0.0")
    GATEWAY_PORT: int = int(os.environ.get("GATEWAY_PORT", "8000"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = SharedSettings()
