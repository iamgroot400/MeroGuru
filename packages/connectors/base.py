"""Standard interface every learning-source connector implements.

The learning engine only ever talks to this interface, so YouTube, MediaWiki,
manual URLs, and future connectors are interchangeable and independently testable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ContentAccess(str, Enum):
    METADATA_ONLY = "metadata-only"
    CREATOR_AUTHORIZED_TRANSCRIPT = "creator-authorized-transcript"
    USER_PROVIDED_TRANSCRIPT = "user-provided-transcript"
    OPENLY_LICENSED = "openly-licensed"


@dataclass
class SearchRequest:
    query: str
    language: str = "en"
    max_results: int = 5


@dataclass
class ResourceCandidate:
    provider: str
    external_id: str
    title: str
    url: str
    author: str | None
    content_type: str
    language: str
    duration_seconds: int | None
    license_name: str | None
    embeddable: bool
    content_access: ContentAccess
    retrieved_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceContent:
    text: str
    permission_basis: ContentAccess


@dataclass
class ConnectorHealth:
    ok: bool
    detail: str = ""


class LearningSourceConnector(ABC):
    provider: str

    @abstractmethod
    async def search(self, request: SearchRequest) -> list[ResourceCandidate]:
        ...

    @abstractmethod
    async def fetch_permitted_content(self, candidate: ResourceCandidate) -> SourceContent | None:
        """Return processable text only when content_access permits it. Otherwise None."""

    @abstractmethod
    async def healthcheck(self) -> ConnectorHealth:
        ...
