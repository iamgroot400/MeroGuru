from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.goal import Concept
from app.models.resource import Resource, ResourceConcept, SourceChunk, SourceDocument
from app.schemas.resource import ManualResourceCreate
from packages.connectors.base import ContentAccess
from packages.connectors.manual_content import ManualContentConnector

_connector = ManualContentConnector()


class ResourceCreationError(ValueError):
    pass


def create_manual_resource(db: Session, payload: ManualResourceCreate) -> Resource:
    concept = db.get(Concept, payload.concept_id)
    if concept is None:
        raise ResourceCreationError(f"concept {payload.concept_id} not found")

    content_access = ContentAccess(payload.content_access)
    candidate = _connector.build_candidate(url=payload.url, title=payload.title, content_access=content_access)

    resource = Resource(
        provider=candidate.provider,
        external_id=candidate.external_id,
        url=candidate.url,
        title=candidate.title,
        content_type=candidate.content_type,
        language=candidate.language,
        content_access=candidate.content_access.value,
        embeddable=candidate.embeddable,
        metadata_json={},
    )
    db.add(resource)
    db.flush()

    db.add(ResourceConcept(resource_id=resource.id, concept_id=concept.id, relevance_score=1.0))

    if payload.text:
        content_hash = hashlib.sha256(payload.text.encode()).hexdigest()
        document = SourceDocument(
            resource_id=resource.id,
            content_hash=content_hash,
            permission_basis=content_access.value,
            ingestion_method="user_pasted",
        )
        db.add(document)
        db.flush()
        # Single-chunk storage for now; splitting into multiple retrievable chunks
        # is deferred until the embeddings/semantic-search pipeline is implemented.
        db.add(
            SourceChunk(
                source_document_id=document.id,
                chunk_index=0,
                text=payload.text,
                token_count=len(payload.text.split()),
                citation_locator=payload.title,
            )
        )

    db.commit()
    db.refresh(resource)
    return resource
