# Hub architecture — maker-first, cloud-portable

EmberForge is a **hub** (brain) plus optional **thin clients** (Mac voice app, ESP32). Release 1.0 optimizes for makers running the hub locally. The codebase is structured so the same hub can later run on **AWS** as a hosted, multi-tenant service without rewriting the device API.

## Design principles

1. **Maker/DIY is the default** — filesystem layout (`personas/`, `prompts/`, `.env`, `.emberforge/`), `./start_ember.sh`, Docker on a home LAN.
2. **Devices stay thin** — no API keys, no LLM on ESP32; `/device/v1/` contract is stable.
3. **One composition root** — `HubRuntime` wires settings, layout, personas, and `ConverseService` for one logical tenant.
4. **Explicit deployment profile** — `EMBER_DEPLOYMENT` gates behavior (setup writes, state backends) instead of hard-coding “localhost assumptions” everywhere.
5. **Tenant seam without multi-tenancy yet** — `tenant_key` and `scoped_session_id()` are empty for makers today; cloud fills them later.

## Deployment profiles

| `EMBER_DEPLOYMENT` | Typical use | Setup writes `.env` | Security state | Conversation memory |
|--------------------|-------------|---------------------|----------------|---------------------|
| `local` (default) | Mac venv, `./start_ember.sh` | Yes | `.emberforge/` on disk | In-process |
| `docker` | `docker compose` home hub | Yes (mounted `.env`) | Named volume / mount | In-process |
| `cloud` | Future AWS / ECS / Lambda+ALB | **No** — env/secrets from platform | **External** (DynamoDB, Redis) | **External** (Redis) |

Set in `.env`:

```bash
EMBER_DEPLOYMENT=local   # default
# EMBER_DEPLOYMENT=docker
# EMBER_DEPLOYMENT=cloud   # reserved; blocks setup UI .env writes today
```

## Code map

```
emberforge/hub/
  deployment.py   # DeploymentProfile enum + capability flags
  layout.py       # ProjectLayout — personas, prompts, .env, .emberforge paths
  tenancy.py      # scoped_session_id() for future multi-tenant memory
  runtime.py      # HubRuntime, build_hub(), get_hub()
  storage/
    protocols.py  # ConfigStore, SecurityStore, ConversationStore, PersonaCatalog
    local.py      # Filesystem + in-memory maker implementations
    factory.py    # build_hub_stores(), get_process_security_store()
```

**Integration points (today):**

- `create_app()` builds a `HubRuntime` and stores `app.state.hub`
- `GET /device/v1/capabilities` returns a `hub` object (deployment, backends)
- `/setup/v1/status` includes the same `hub` metadata
- `EMBER_DEPLOYMENT=cloud` returns HTTP 501 on setup config mutations

## What stays on the hub (not the device)

| Concern | Maker hub (now) | Cloud hub (later) |
|---------|-----------------|-------------------|
| LLM keys | `.env` | Secrets Manager / per-tenant vault |
| Personas & prompts | `personas/`, `prompts/` | S3 or DB per tenant |
| Whisper STT | Hub CPU | Same, scaled horizontally |
| ElevenLabs TTS | Hub → device MP3 | Same |
| Device pairing | `.emberforge/devices.json` | Registry per `tenant_id` |
| Conversation memory | In-memory by `session_id` | Redis keyed by `tenant:session` |
| User context / RSS | `.env` + `prompts/user_context.md` | Tenant profile store |

## Maker workflow (unchanged)

```bash
./start_ember.sh --text-only --open-setup
# EMBER_DEPLOYMENT=local (default)
# Configure via /setup → writes .env
# Pair devices → token in .emberforge/
# ESP32 → POST /device/v1/converse
```

## Path to AWS / commercial hosting

Recommended order — each step keeps makers working:

### Phase 1 — Composition & flags ✅ (this document)

- `HubRuntime`, `ProjectLayout`, `DeploymentProfile`
- Device capabilities expose deployment metadata
- Cloud profile disables unsafe setup writes

### Phase 2 — Storage protocols ✅

Abstract behind interfaces; local implementations wired through `HubStores`:

- `ConfigStore` — `.env` today; SSM/Secrets Manager later
- `SecurityStore` — file registry + in-memory pairing; DynamoDB + Redis later
- `ConversationStore` — `ConversationHistoryStore` today; Redis with TTL later
- `PersonaCatalog` — filesystem today; S3/DB later

`build_hub()` injects stores into `ConverseService` and exposes them on `HubRuntime.stores`. AWS backends replace the local classes in `factory.py` when `EMBER_DEPLOYMENT=cloud` without touching device routes.

### Phase 3 — Tenant middleware

- Account signup, `tenant_id` on device registry and session keys
- Device pairing bound to user account (cloud issues codes; device confirms on LAN)
- Rate limits and admin auth without `is_trusted_local()` behind ALB

### Phase 4 — AWS topology

Typical split:

```
Route 53 → ALB → ECS/Fargate (emberforge serve, EMBER_DEPLOYMENT=cloud)
              → ElastiCache Redis (sessions, pairing, conversation)
              → DynamoDB (device registry)
              → S3 (persona assets, optional)
              → Secrets Manager (platform LLM keys; optional BYOK per tenant)
```

Devices point at `https://api.emberforge.example` instead of `http://192.168.x.x:8000`. Firmware provisioning stores hub URL + `device_token` in NVS.

### Phase 5 — Hybrid SKU (differentiator)

Same account can link a **home hub** (`EMBER_DEPLOYMENT=docker` on LAN) for low latency and offline-adjacent use, while cloud handles accounts and billing. One device API; two brain URLs per policy.

## Processor requirements

**No change for ESP32-S3** as long as the device remains a thin client. Cloud vs local hub is a **network and provisioning** decision, not a silicon change.

## Related docs

- [`ROADMAP.md`](ROADMAP.md) — product north star: maker path, AWS phases, explicit non-goals
- [`device/README.md`](../device/README.md) — device API contract
- [`M7_SECURITY.md`](M7_SECURITY.md) — pairing and production auth
- [`deploy/README.md`](../deploy/README.md) — Docker home hub
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — development setup