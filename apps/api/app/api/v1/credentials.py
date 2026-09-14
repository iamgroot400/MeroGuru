from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.credential import ProviderCredential
from app.schemas.credential import CredentialCreate, CredentialOut, CredentialTestResult
from app.services.credential_service import create_credential, get_provider_for
from packages.connectors.youtube import YouTubeConnector
from app.core.crypto import decrypt_secret

router = APIRouter(prefix="/credentials", tags=["credentials"])


@router.get("", response_model=list[CredentialOut])
def list_credentials(db: Session = Depends(get_db)) -> list[ProviderCredential]:
    return db.query(ProviderCredential).order_by(ProviderCredential.created_at.desc()).all()


@router.post("", response_model=CredentialOut, status_code=201)
def add_credential(payload: CredentialCreate, db: Session = Depends(get_db)) -> ProviderCredential:
    return create_credential(db, payload)


@router.post("/{credential_id}/test", response_model=CredentialTestResult)
async def test_credential(credential_id: UUID, db: Session = Depends(get_db)) -> CredentialTestResult:
    credential = db.get(ProviderCredential, credential_id)
    if credential is None:
        raise HTTPException(404, "credential not found")

    if credential.provider == "youtube":
        api_key = decrypt_secret(credential.encrypted_secret)
        health = await YouTubeConnector(api_key).healthcheck()
    else:
        provider = get_provider_for(db, credential_id)
        health = await provider.healthcheck()

    credential.validation_status = "ok" if health.ok else "failed"
    credential.validation_detail = health.detail
    credential.validated_at = datetime.now(timezone.utc)
    db.commit()
    return CredentialTestResult(ok=health.ok, detail=health.detail)


@router.delete("/{credential_id}", status_code=204)
def delete_credential(credential_id: UUID, db: Session = Depends(get_db)) -> None:
    credential = db.get(ProviderCredential, credential_id)
    if credential is None:
        raise HTTPException(404, "credential not found")
    db.delete(credential)
    db.commit()
