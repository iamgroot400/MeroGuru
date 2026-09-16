"""Regression tests for the provider base_url SSRF guard.

Before this guard, a base_url supplied through POST /api/v1/credentials (or
through the brain's request body) reached httpx unvalidated, letting a caller
point the deployment at cloud metadata or sibling containers and read the
response back out via job.error_summary.
"""
from __future__ import annotations

import pytest

from packages.ai_providers.registry import build_provider
from packages.ai_providers.url_guard import ProviderUrlError, validate_provider_url


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data",   # AWS/GCP/Azure IMDS
        "https://169.254.169.254/",
        "http://[fe80::1]/",
    ],
)
def test_link_local_refused_for_every_provider(url):
    """Instance metadata has no legitimate provider use, local or remote."""
    for provider in ("openai_compatible", "ollama"):
        with pytest.raises(ProviderUrlError, match="link-local"):
            validate_provider_url(url, provider=provider)


@pytest.mark.parametrize(
    "url",
    ["https://127.0.0.1/v1", "https://10.0.0.5/v1", "https://192.168.1.1/v1", "https://[::1]/v1"],
)
def test_internal_addresses_refused_for_remote_providers(url):
    with pytest.raises(ProviderUrlError, match="non-public"):
        validate_provider_url(url, provider="openai_compatible")


@pytest.mark.parametrize("url", ["http://127.0.0.1:11434", "http://192.168.1.50:11434"])
def test_internal_addresses_allowed_for_ollama(url):
    """Reaching a local inference server is the entire point of this provider."""
    assert validate_provider_url(url, provider="ollama") == url


def test_remote_provider_requires_https():
    with pytest.raises(ProviderUrlError, match="https"):
        validate_provider_url("http://api.example.com/v1", provider="openai_compatible")


@pytest.mark.parametrize("url", ["file:///etc/passwd", "gopher://x/", "ftp://x/"])
def test_non_http_schemes_refused(url):
    with pytest.raises(ProviderUrlError, match="scheme"):
        validate_provider_url(url, provider="openai_compatible")


def test_missing_hostname_refused():
    with pytest.raises(ProviderUrlError):
        validate_provider_url("https:///v1", provider="openai_compatible")


def test_unresolvable_host_is_allowed():
    """A name that does not resolve cannot be an internal target -- the request
    fails the same way moments later -- and offline/dev configs depend on it."""
    url = "http://unreachable.invalid:11434"
    assert validate_provider_url(url, provider="ollama") == url


def test_build_provider_rejects_metadata_endpoint():
    """The guard is wired into the single choke point both services use."""
    with pytest.raises(ProviderUrlError):
        build_provider(
            provider="openai_compatible",
            api_key="k",
            base_url="http://169.254.169.254/latest",
        )


def test_build_provider_still_accepts_public_defaults():
    provider = build_provider(provider="groq", api_key="gsk_test")
    assert provider.base_url == "https://api.groq.com/openai/v1"
