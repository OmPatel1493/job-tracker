from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SuggestionItem(BaseModel):
    category: str
    priority: str
    suggestion: str
    example: str

    model_config = ConfigDict(from_attributes=True)


class SuggestionResponse(BaseModel):
    id: int
    application_id: int
    suggestions: list[SuggestionItem]
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
