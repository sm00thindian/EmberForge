# EmberForge roadmap — maker-first, cloud-portable

This document is the **product and engineering north star** after Release 1.0. It describes where EmberForge is headed without committing to dates. Makers and DIY builders remain the default audience; commercial hosting on AWS is a deliberate second track that reuses the same hub and device APIs.

**Related docs**

- [`HUB_ARCHITECTURE.md`](HUB_ARCHITECTURE.md) — hub composition, deployment profiles, storage seams (implementation detail)
- [`RELEASE_1.0.md`](RELEASE_1.0.md) — what shipped in 1.0 (M1–M9)
- [`device/README.md`](../device/README.md) — stable `/device/v1/` contract
- [`deploy/README.md`](../deploy/README.md) — Docker home hub

---

## Strategic direction

| Principle | What it means |
|-----------|----------------|
| **Thin clients** | Mac voice app and ESP32-S3 stay dumb: mic, speaker, button, display. No API keys or LLM on device silicon. |
| **One hub brain** | Personas, STT, LLM, TTS, memory, pairing, and context live on the hub — local today, hosted tomorrow. |
| **Stable device API** | `/device/v1/` remains backward-compatible. Cloud migration changes **where** the hub runs, not **what** firmware sends. |
| **Maker default** | Filesystem layout, `./start_ember.sh`, Docker on a home LAN, setup UI writing `.env`. Zero cloud account required. |
| **Portable by design** | Storage and deployment are behind protocols (`HubStores`, `EMBER_DEPLOYMENT`). AWS backends plug in at the factory layer. |

---

## Shipped — v1.1.0 (portability layer)

Release **1.1.0** adds the hub composition root without changing maker workflows:

- **`HubRuntime`** — single wiring point for settings, layout, personas, and `ConverseService`
- **`EMBER_DEPLOYMENT`** — `local` (default), `docker`, `cloud` profiles gate setup writes and capability metadata
- **Storage protocols** — `ConfigStore`, `SecurityStore`, `ConversationStore`, `PersonaCatalog` with local implementations
- **Device visibility** — `GET /device/v1/capabilities` returns a `hub` object (deployment, backends, tenant mode)
- **Tenant seam** — `scoped_session_id()` for future multi-tenant memory; empty tenant preserves today's behavior
- **Docker** — `docker-compose.yml` sets `EMBER_DEPLOYMENT=docker` for home-LAN hubs

Makers: no action required. `EMBER_DEPLOYMENT=local` is the default.

---

## Near term (post-1.1)

Work that strengthens the DIY path and prepares commercial options without forcing either:

### Consumer device firmware

- ESP32-S3 push-to-talk loop against `/device/v1/converse`
- NVS provisioning for hub URL + `device_token` (pairing flow from M7)
- Boot sequence: capabilities → personas → converse
- MP3 playback from `voice.audio_base64` (ElevenLabs path)

### Hub hardening (maker-hosted)

- Route setup config mutations through `HubStores.config` (single code path)
- Optional hub health dashboard beyond `/setup` status
- Documented backup/restore for `.env`, `.emberforge/`, `prompts/`

### Documentation & DX

- Firmware bring-up guide tied to `device/README.md`
- Example hybrid LAN setup (Mac client → Docker hub on NAS/mini-PC)

---

## Phase 3 — Tenant middleware (commercial prerequisite)

**Goal:** Multiple customer accounts on one hosted hub without cross-tenant data leaks.

| Area | Maker (today) | Cloud (target) |
|------|---------------|----------------|
| Identity | Single operator | Account signup, `tenant_id` on all scoped state |
| Device pairing | Localhost codes → `.emberforge/` | Account-bound pairing; cloud issues codes, device confirms |
| Sessions | `session_id` only | `scoped_session_id(tenant_id, session_id)` everywhere |
| Admin auth | Localhost trust + TOTP | JWT/OAuth behind ALB; no `is_trusted_local()` assumption |
| Rate limits | Per-IP | Per-tenant + per-device quotas |

**Exit criteria:** Two isolated tenants on one hub process; device tokens cannot access another tenant's personas or history.

---

## Phase 4 — AWS hosted hub

**Goal:** Run `emberforge serve` with `EMBER_DEPLOYMENT=cloud` on managed infrastructure.

Typical topology:

```
Route 53 → ALB → ECS/Fargate (emberforge serve)
              → ElastiCache Redis   (conversation memory, pairing TTL, admin sessions)
              → DynamoDB            (device registry per tenant)
              → S3                  (persona assets, optional)
              → Secrets Manager     (platform LLM keys; optional BYOK per tenant)
```

**Implementation approach:** New classes in `emberforge/hub/storage/` (e.g. `cloud.py`) selected by `build_hub_stores()` when `EMBER_DEPLOYMENT=cloud`. Device routes and `ConverseService` unchanged.

**Firmware change:** Hub URL in NVS moves from `http://192.168.x.x:8000` to `https://api.<domain>`. Token format and `/device/v1/*` payloads stay the same.

**Exit criteria:** Staging environment passes contract tests + multi-tenant isolation tests; setup UI does not write `.env` (already blocked for `cloud` profile).

---

## Phase 5 — Hybrid SKU (differentiator)

**Goal:** One customer account, two brain options — best latency at home, accounts and billing in cloud.

| Mode | Hub location | Use case |
|------|--------------|----------|
| **Home hub** | `EMBER_DEPLOYMENT=docker` on LAN | Low latency, local Whisper, offline-adjacent |
| **Cloud hub** | `EMBER_DEPLOYMENT=cloud` on AWS | Travel, multi-device sync, managed keys |

Same device API. Policy layer chooses brain URL per device or per user preference. This is the primary commercial story for makers who already self-host.

---

## Explicit non-goals (for now)

- Running LLM inference on ESP32-S3
- Breaking `/device/v1/` without a new major API version
- Requiring cloud accounts for local-only makers
- Multi-region active-active (single-region AWS is enough for first commercial launch)

---

## How to contribute against this roadmap

1. **Maker features** — personas, voice, setup UX, Mac client, firmware: land directly; no cloud dependency.
2. **Portability** — new persistence or config paths should implement or consume `emberforge/hub/storage/` protocols.
3. **Commercial features** — tenant isolation and external stores behind `EMBER_DEPLOYMENT=cloud`; keep `local`/`docker` behavior identical.

See [`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`HUB_ARCHITECTURE.md`](HUB_ARCHITECTURE.md) for code layout and PR expectations.

---

## Version alignment

| Component | Policy |
|-----------|--------|
| Python package | Semver in `emberforge/__init__.py` — **1.1.0** adds portability layer |
| Device API | `/device/v1/` until a breaking change forces `/device/v2/` |
| Capabilities | `hub` object in capabilities response is additive; firmware should tolerate unknown fields |

**Changelog:** [`CHANGELOG.md`](../CHANGELOG.md)