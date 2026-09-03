from fastapi import APIRouter
from pydantic import BaseModel

from core.config import settings
from core.enums import SAMPLES_PER_CATEGORY, Category

router = APIRouter(prefix="/meta", tags=["meta"])


class CategoryInfo(BaseModel):
    value: Category
    label: str


class AppInfo(BaseModel):
    name: str
    version: str
    environment: str
    llm_enabled: bool
    llm_model: str
    samples_per_category: int
    categories: list[CategoryInfo]


@router.get("", response_model=AppInfo)
def app_info() -> AppInfo:
    """Everything the web client needs to render itself before logging in."""
    return AppInfo(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        llm_enabled=settings.llm_enabled,
        llm_model=settings.openai_model,
        samples_per_category=SAMPLES_PER_CATEGORY,
        categories=[
            CategoryInfo(value=category, label=category.label) for category in Category
        ],
    )
