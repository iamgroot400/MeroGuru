from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.resource import Resource, SourceDocument
from app.schemas.resource import ManualResourceCreate, ResourceOut
from app.services.resource_service import ResourceCreationError, create_manual_resource

router = APIRouter(prefix="/resources", tags=["resources"])


@router.post("/manual", response_model=ResourceOut, status_code=201)
def add_manual_resource(payload: ManualResourceCreate, db: Session = Depends(get_db)) -> dict:
    try:
        resource = create_manual_resource(db, payload)
    except ResourceCreationError as exc:
        raise HTTPException(404, str(exc)) from exc

    has_content = db.query(SourceDocument).filter(SourceDocument.resource_id == resource.id).first() is not None
    return {
        "id": resource.id,
        "provider": resource.provider,
        "url": resource.url,
        "title": resource.title,
        "content_type": resource.content_type,
        "content_access": resource.content_access,
        "has_stored_content": has_content,
    }


@router.get("/{resource_id}", response_model=ResourceOut)
def get_resource(resource_id: UUID, db: Session = Depends(get_db)) -> dict:
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(404, "resource not found")
    has_content = db.query(SourceDocument).filter(SourceDocument.resource_id == resource.id).first() is not None
    return {
        "id": resource.id,
        "provider": resource.provider,
        "url": resource.url,
        "title": resource.title,
        "content_type": resource.content_type,
        "content_access": resource.content_access,
        "has_stored_content": has_content,
    }
