from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ManualResourceCreate(BaseModel):
    concept_id: UUID
    url: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=500)
    content_access: str = Field(
        pattern="^(user-provided-transcript|creator-authorized-transcript|openly-licensed)$"
    )
    text: str | None = Field(default=None, max_length=200_000)

    @model_validator(mode="after")
    def require_text_for_transcript_modes(self) -> "ManualResourceCreate":
        if self.content_access in ("user-provided-transcript", "creator-authorized-transcript") and not self.text:
            raise ValueError(f"'{self.content_access}' requires pasted text")
        return self


class ResourceOut(BaseModel):
    id: UUID
    provider: str
    url: str
    title: str
    content_type: str
    content_access: str
    has_stored_content: bool

    class Config:
        from_attributes = True
