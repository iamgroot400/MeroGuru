# Security policy

MeroGuru is a self-hosted, single-user application. Threats to think about when
deploying it:

- **Your provider API keys** are encrypted at rest with a master key
  (`CREDENTIAL_ENCRYPTION_KEY`) you control via `.env`. Never commit `.env` or share
  this key. If it leaks, rotate it and re-enter your provider keys.
- **Network exposure**: every published port in `docker-compose.yml` is bound to
  `127.0.0.1` explicitly. This matters: a bare `"8000:8000"` mapping would bind
  `0.0.0.0`, and Docker's DNAT rules are evaluated *before* the firewall chain
  `ufw` manages, so a host firewall would not contain it. If you change those
  mappings or expose the stack beyond your own machine, put it behind a reverse
  proxy with HTTPS and your own access control — MeroGuru has no login of its own
  by design, so the network boundary *is* the access control.
- **Origin allowlist**: the API accepts cross-origin requests only from
  `APP_BASE_URL` (plus `CORS_EXTRA_ORIGINS`). Because there is no login, widening
  this to `*` would let any page you visit read and write your data.
- **Provider URLs**: `base_url` values you supply are screened before use —
  link-local metadata addresses are always refused, and private/loopback targets
  are refused for remote providers (Ollama excepted, since local inference is its
  purpose).
- **Brain service**: `BRAIN_SHARED_SECRET` must be set. The brain makes outbound
  calls using the provider config it is handed, so it refuses unauthenticated
  requests rather than acting as an open proxy.
- **Uploaded/pasted content**: user-provided transcripts and notes are stored as-is;
  don't paste secrets into lesson content.

## Reporting a vulnerability

Please open a private security advisory on GitHub (or email the maintainer listed in
the repository) rather than a public issue. Include:

- A description of the vulnerability and its impact.
- Steps to reproduce.
- Any suggested fix, if you have one.

We'll acknowledge reports as quickly as we can and credit reporters in release notes
unless you prefer otherwise.
