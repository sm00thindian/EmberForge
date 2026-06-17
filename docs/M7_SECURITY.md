# M7 — Security & Multi-Factor Auth

EmberForge security is designed around one principle: **protect against misuse without nagging you on every voice turn.**

You never enter a TOTP code or scan your face before each push-to-talk utterance. MFA applies at **setup boundaries** (pairing a device, remote admin access) — not during normal conversation.

## MFA options (what to use when)

| Layer | Method | When it runs | Friction |
|-------|--------|--------------|----------|
| **Device API** | Per-device bearer token (or legacy `EMBER_DEVICE_TOKEN`) | Every `/device/v1/*` request in production | Zero after pairing — token stored on device |
| **Device pairing** | 6-character code from `emberforge pair` | Once per new hardware unit | Low — localhost-only code issuance |
| **Mac / remote admin** | Google Authenticator (TOTP) → 8h session | Remote access to `/chat`, `/personas` in production | Low — scan once, session lasts hours |
| **Mac / remote admin** | Static `EMBER_ADMIN_TOKEN` | Alternative to TOTP for scripts/CI | None after export |
| **Mac localhost** | Implicit trust (`127.0.0.1`) | Mac voice companion on same machine | None — by design |
| **Physical** | Push-to-talk button / hold SPACE | Every utterance | Natural — not a second factor popup |
| **Future: Mac pairing** | Touch ID / Face ID | Approve pairing code on Mac | Planned — not HTTP middleware yet |

### Compatible authenticator apps

TOTP (`EMBER_ADMIN_TOTP_SECRET`) works with:

- **Google Authenticator**
- **1Password** (built-in OTP)
- **Apple Passwords** (iOS 18+ / macOS Sequoia+)
- **Authy**, **Bitwarden**, or any RFC 6238 app

### What we deliberately avoid

- **Per-utterance MFA** — voice would be unusable
- **SMS OTP** — weak, carrier-dependent, annoying
- **Captcha on converse** — blocks legitimate device traffic
- **Certificate pinning on LAN** — overkill for home hub; device token is enough

## Environments

| `EMBER_ENV` | Device auth | Rate limits | Remote `/chat` |
|-------------|-------------|-------------|----------------|
| `development` (default) | Optional (`EMBER_DEVICE_TOKEN` if set) | Off unless `EMBER_RATE_LIMIT_ENABLED=true` | Open |
| `production` | Required | On | Admin token or TOTP session; localhost always trusted |

## Quick start (production home hub)

```bash
# 1. Generate admin TOTP (optional — for remote Mac access)
emberforge totp-setup --generate
# Add EMBER_ADMIN_TOTP_SECRET=... to .env

# 2. Enable production mode
export EMBER_ENV=production
export XAI_API_KEY=...

# 3. Start backend (127.0.0.1 is fine for Mac companion)
emberforge serve

# 4. Pair a device (from the Mac running the backend)
emberforge pair
# On device firmware: POST /device/v1/pair/confirm with the code
# Save the returned device_token — shown once

# 5. Remote admin session (only if accessing /chat from another machine)
curl -X POST http://hub:8000/admin/v1/session \
  -H 'Content-Type: application/json' \
  -d '{"totp":"123456"}'
# Use returned access_token as Bearer on /chat and /personas
```

## API reference

| Endpoint | Auth | Notes |
|----------|------|-------|
| `POST /admin/v1/pair/code` | Localhost only in production | Returns 6-char code, 5 min TTL |
| `POST /device/v1/pair/confirm` | None | Exchanges code for `device_token` |
| `GET /admin/v1/totp/setup` | None | Provisioning URI when TOTP configured |
| `POST /admin/v1/session` | TOTP body | Returns bearer session (~8h default) |
| `/device/v1/*` (except pair confirm) | `Authorization: Bearer <device_token>` | Required in production |
| `/chat`, `/personas` | Admin bearer or localhost | Production remote only |

## Configuration

```bash
EMBER_ENV=production                    # development | production
EMBER_DEVICE_TOKEN=                     # legacy shared token (min 16 chars) OR use pairing
EMBER_ADMIN_TOKEN=                      # static remote admin token (optional)
EMBER_ADMIN_TOTP_SECRET=                # base32 secret for Google Authenticator
EMBER_ADMIN_SESSION_TTL_SECONDS=28800     # 8 hours
EMBER_PAIRING_CODE_TTL_SECONDS=300        # 5 minutes
EMBER_RATE_LIMIT_ENABLED=false            # force on in production
EMBER_RATE_LIMIT_CONVERSE_PER_MINUTE=20
EMBER_RATE_LIMIT_DEFAULT_PER_MINUTE=120
EMBER_DEVICE_TOKEN_MIN_LENGTH=16
```

Paired device registry and salt live under `.emberforge/` (gitignored).

## Rate limiting

Sliding-window limits per IP (and per `X-Device-ID` when set). Stricter on paths containing `/converse`. `/health` and `/version` are exempt.

## Secret redaction

Log output redacts bearer tokens and known env key patterns (`XAI_API_KEY`, `EMBER_DEVICE_TOKEN`, etc.) via `SecretRedactionFilter` on the root logger.

## Binding `0.0.0.0`

Production on `0.0.0.0` or `::` requires `EMBER_ADMIN_TOKEN` or `EMBER_ADMIN_TOTP_SECRET` so remote Mac clients cannot hit `/chat` without credentials. Device endpoints still require device tokens.