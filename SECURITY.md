# Security policy

MeroGuru is a self-hosted, single-user application. Threats to think about when
deploying it:

- **Your provider API keys** are encrypted at rest with a master key
  (`CREDENTIAL_ENCRYPTION_KEY`) you control via `.env`. Never commit `.env` or share
  this key. If it leaks, rotate it and re-enter your provider keys.
- **Network exposure**: by default the app binds to localhost via Docker port
  mapping. If you expose it beyond your own machine (e.g. on a home server reachable
  from the internet), put it behind a reverse proxy with HTTPS and your own access
  control — MeroGuru has no login of its own by design.
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
