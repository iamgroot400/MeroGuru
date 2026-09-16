from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret, encrypt_secret, mask_secret
from app.models.credential import ProviderCredential
from app.schemas.credential import CredentialCreate
from packages.ai_providers.base import AIProvider
from packages.ai_providers.registry import build_provider
from packages.ai_providers.url_guard import validate_provider_url


AI_PROVIDERS = {"openai", "anthropic", "groq", "openai_compatible", "ollama"}


def create_credential(db: Session, payload: CredentialCreate) -> ProviderCredential:
    # Screen the URL here as well as in build_provider: this rejects a hostile
    # base_url at the API boundary instead of storing it and only refusing it
    # later, when a background job tries to use it.
    if payload.base_url:
        validate_provider_url(payload.base_url, provider=payload.provider)

    if payload.provider in AI_PROVIDERS:
        db.query(ProviderCredential).filter(
            ProviderCredential.provider.in_(AI_PROVIDERS)
        ).update({"is_active_provider": False})

    credential = ProviderCredential(
        provider=payload.provider,
        encrypted_secret=encrypt_secret(payload.api_key),
        masked_label=mask_secret(payload.api_key),
        base_url=payload.base_url,
        chat_model=payload.chat_model,
        embedding_model=payload.embedding_model,
        is_active_provider=payload.provider in AI_PROVIDERS,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


def get_provider_for(db: Session, credential_id: UUID) -> AIProvider:
    from app.core.config import settings

    credential = db.get(ProviderCredential, credential_id)
    if credential is None:
        raise ValueError("credential not found")
    api_key = None if credential.provider == "ollama" else decrypt_secret(credential.encrypted_secret)
    # A saved Ollama credential may not specify a model (the settings form only
    # asks for a base URL); fall back to the deployment's configured model rather
    # than an arbitrary hardcoded one, so it matches what's actually documented
    # and likely pulled.
    chat_model = credential.chat_model
    embedding_model = credential.embedding_model
    if credential.provider == "ollama":
        chat_model = chat_model or settings.ollama_chat_model
        embedding_model = embedding_model or settings.ollama_embedding_model
    return build_provider(
        provider=credential.provider,
        api_key=api_key,
        base_url=credential.base_url,
        chat_model=chat_model,
        embedding_model=embedding_model,
    )


def get_active_ai_provider(db: Session) -> AIProvider:
    """Returns the learner's configured AI credential, or falls back to the
    deployment's local Ollama instance so the app works with zero paid keys."""
    from app.core.config import settings

    credential = (
        db.query(ProviderCredential)
        .filter(
            ProviderCredential.is_active_provider.is_(True),
            ProviderCredential.provider.in_(list(AI_PROVIDERS)),
        )
        .first()
    )
    if credential is not None:
        return get_provider_for(db, credential.id)
    return build_provider(
        provider=settings.ai_provider,
        base_url=settings.ollama_base_url,
        chat_model=settings.ollama_chat_model,
        embedding_model=settings.ollama_embedding_model,
    )


def get_active_ai_provider_config(db: Session) -> dict:
    """Same resolution order as get_active_ai_provider(), but returns the raw
    provider settings instead of a constructed AIProvider -- the brain service
    lives in a separate process, so its provider must be rebuilt there from a
    serialized config sent over HTTP rather than passed as a live object."""
    from app.core.config import settings

    credential = (
        db.query(ProviderCredential)
        .filter(
            ProviderCredential.is_active_provider.is_(True),
            ProviderCredential.provider.in_(list(AI_PROVIDERS)),
        )
        .first()
    )
    if credential is not None:
        api_key = None if credential.provider == "ollama" else decrypt_secret(credential.encrypted_secret)
        chat_model = credential.chat_model
        embedding_model = credential.embedding_model
        if credential.provider == "ollama":
            chat_model = chat_model or settings.ollama_chat_model
            embedding_model = embedding_model or settings.ollama_embedding_model
        return {
            "provider": credential.provider,
            "api_key": api_key,
            "base_url": credential.base_url,
            "chat_model": chat_model,
            "embedding_model": embedding_model,
        }
    return {
        "provider": settings.ai_provider,
        "api_key": None,
        "base_url": settings.ollama_base_url,
        "chat_model": settings.ollama_chat_model,
        "embedding_model": settings.ollama_embedding_model,
    }


def get_youtube_api_key(db: Session) -> str | None:
    from app.core.config import settings

    credential = db.query(ProviderCredential).filter(ProviderCredential.provider == "youtube").first()
    if credential is not None:
        return decrypt_secret(credential.encrypted_secret)
    return settings.youtube_api_key or None
