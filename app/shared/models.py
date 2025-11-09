from dataclasses import dataclass, asdict
from typing import Any, Dict, List
from pydantic import BaseModel, Field


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


@dataclass
class EmbeddingRecord:
    id: str
    url: str
    description: str
    duration: str
    adaptive_support: bool
    remote_support: bool
    test_type: List[str]

    def to_document(self) -> str:
        bullet_types = ", ".join(self.test_type)
        return (
            f"URL: {self.url}\n"
            f"Duration: {self.duration or 'Unspecified'}\n"
            f"Adaptive Support: {'Yes' if self.adaptive_support else 'No'}\n"
            f"Remote Support: {'Yes' if self.remote_support else 'No'}\n"
            f"Test Types: {bullet_types or 'Unspecified'}\n"
            f"Description: {self.description}"
        )

    def to_metadata(self) -> dict:
        metadata = asdict(self)
        metadata.pop("id")
        if isinstance(metadata.get("test_type"), list):
            metadata["test_type"] = ", ".join(metadata["test_type"])
        return metadata


class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Natural language query")


class RecommendationItem(BaseModel):
    url: str = Field(..., description="Valid URL to the assessment resource")
    name: str = Field(..., description="Name of the assessment")
    adaptive_support: str = Field(..., description="Either 'Yes' or 'No' indicating if the assessment supports adaptive testing")
    description: str = Field(..., description="Detailed description of the assessment")
    duration: str = Field(..., description="Duration of the assessment in minutes")
    remote_support: str = Field(..., description="Either 'Yes' or 'No' indicating if the assessment can be taken remotely")
    test_type: List[str] = Field(..., description="Categories or types of the assessment")


class RecommendResponse(BaseModel):
    recommended_assessments: List[RecommendationItem]
