"""SSRF guard for user-supplied provider base URLs.

Provider `base_url` values arrive from the credentials API (apps/api) and from
the brain service's request body (apps/brain). Both reach httpx, so an
unvalidated value lets a caller point the deployment at arbitrary internal
hosts -- cloud metadata endpoints, sibling containers, router admin panels --
and, because upstream errors surface in job/validation fields, read the
response back out. This module is the single choke point both services call.

Policy:
  - Only http/https. Remote providers must use https.
  - Link-local (169.254.0.0/16, fe80::/10) is refused for every provider: it
    carries cloud instance metadata and has no legitimate provider use.
  - Loopback/private/reserved addresses are refused for remote providers
    (openai, anthropic, groq, openai_compatible) but permitted for ollama,
    whose entire purpose is to reach a local inference server.

Every DNS answer for the host is checked, not just the first, so a name that
resolves to one public and one internal address is still refused.
"""
from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})

# Providers whose base_url legitimately points at the operator's own machine.
LOCAL_PROVIDERS = frozenset({"ollama"})

_ALLOW_PRIVATE_ENV = "MEROGURU_ALLOW_PRIVATE_PROVIDER_URLS"


class ProviderUrlError(ValueError):
    """Raised when a provider base_url is refused by policy."""


def _allow_private_override() -> bool:
    """Escape hatch for operators running a self-hosted OpenAI-compatible
    gateway on their own LAN. Off by default: opting in re-enables the SSRF
    reach this module exists to remove."""
    return os.environ.get(_ALLOW_PRIVATE_ENV, "").strip().lower() in {"1", "true", "yes"}


def _is_link_local(ip: ipaddress._BaseAddress) -> bool:
    return ip.is_link_local


def _is_internal(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_link_local
    )


def validate_provider_url(raw_url: str, *, provider: str) -> str:
    """Return the URL unchanged if policy permits it, else raise ProviderUrlError."""
    if not raw_url or not raw_url.strip():
        raise ProviderUrlError("base_url must not be empty")

    url = raw_url.strip()
    parts = urlsplit(url)

    if parts.scheme not in ALLOWED_SCHEMES:
        raise ProviderUrlError(
            f"base_url scheme {parts.scheme!r} is not allowed; use http or https"
        )

    hostname = parts.hostname
    if not hostname:
        raise ProviderUrlError("base_url must include a hostname")

    allow_private = provider in LOCAL_PROVIDERS or _allow_private_override()

    # Address checks run before the https requirement so that a metadata-range
    # target is always reported as such, whichever scheme it was written with.
    # A literal IP needs no resolution; a name may map to several addresses and
    # every one of them has to pass.
    try:
        candidates = [ipaddress.ip_address(hostname)]
    except ValueError:
        try:
            infos = socket.getaddrinfo(hostname, parts.port or 0, proto=socket.IPPROTO_TCP)
        except socket.gaierror:
            # A name that does not resolve cannot be an internal target: the
            # outbound request will fail the same way moments later. Allowing it
            # keeps offline/dev configs working. Residual risk: a rebinding
            # attacker could make it resolve between this check and the request.
            candidates = []
        else:
            candidates = [ipaddress.ip_address(info[4][0]) for info in infos]

    for ip in candidates:
        if _is_link_local(ip):
            raise ProviderUrlError(
                f"base_url resolves to link-local address {ip} (cloud metadata range); refused"
            )
        if not allow_private and _is_internal(ip):
            raise ProviderUrlError(
                f"base_url resolves to non-public address {ip}; refused for provider {provider!r}"
            )

    if parts.scheme == "http" and not allow_private:
        raise ProviderUrlError(f"base_url for provider {provider!r} must use https")

    return url
