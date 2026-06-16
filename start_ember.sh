#!/usr/bin/env bash
#
# EmberForge — Mac startup script
#
# Usage:
#   ./start_ember.sh
#   ./start_ember.sh --persona hal_9000
#   ./start_ember.sh --text-only
#   ./start_ember.sh --env .env.local
#   ./start_ember.sh --non-interactive
#

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
VOICE_DIR="$ROOT_DIR/phase-0-brain"
ENV_FILE=""
BACKEND_PORT="${EMBER_BACKEND_PORT:-8000}"
BACKEND_PID=""
TEXT_ONLY=-1
PERSONA=""
NONINTERACTIVE=0
RUN_MODE_CHOSEN=0
PERSONA_CHOSEN=0

usage() {
  cat <<'EOF'
Usage: ./start_ember.sh [options]

Options:
  --env <file>         Environment file to load (default: auto-select)
  --persona <id>       Persona id (ember, hal_9000, ...)
  --text-only          Start backend only (no voice companion)
  --voice              Start backend + Mac voice companion (default)
  --non-interactive    Fail instead of prompting for missing config
  -h, --help           Show this help

Without flags, the script will:
  - Pick or create an environment file (.env)
  - Prompt for missing required secrets (XAI_API_KEY)
  - Ask how you want to run (voice vs backend-only) if not specified
  - Ask which persona to use if not specified
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --text-only)
      TEXT_ONLY=1
      RUN_MODE_CHOSEN=1
      shift
      ;;
    --voice)
      TEXT_ONLY=0
      RUN_MODE_CHOSEN=1
      shift
      ;;
    --persona)
      PERSONA="${2:-}"
      PERSONA_CHOSEN=1
      if [[ -z "$PERSONA" ]]; then
        echo "Usage: ./start_ember.sh --persona <id>"
        exit 1
      fi
      shift 2
      ;;
    --env)
      ENV_FILE="${2:-}"
      if [[ -z "$ENV_FILE" ]]; then
        echo "Usage: ./start_ember.sh --env <file>"
        exit 1
      fi
      shift 2
      ;;
    --non-interactive)
      NONINTERACTIVE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo ""
    echo "Stopping EmberForge backend..."
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

prompt_yes_no() {
  local question="$1"
  local default="${2:-y}"
  local reply=""

  if [[ "$default" == "y" ]]; then
    read -rp "$question [Y/n] " reply
    reply="${reply:-y}"
  else
    read -rp "$question [y/N] " reply
    reply="${reply:-n}"
  fi

  [[ "$reply" =~ ^[Yy] ]]
}

read_nonempty() {
  local prompt="$1"
  local silent="${2:-0}"
  local value=""

  while [[ -z "$value" ]]; do
    if [[ "$silent" -eq 1 ]]; then
      read -rsp "$prompt" value
      echo ""
    else
      read -rp "$prompt" value
    fi
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    if [[ -z "$value" ]]; then
      echo "A value is required."
    fi
  done

  printf '%s' "$value"
}

resolve_env_path() {
  local candidate="$1"
  if [[ "$candidate" = /* ]]; then
    printf '%s' "$candidate"
  else
    printf '%s' "$ROOT_DIR/$candidate"
  fi
}

discover_env_files() {
  local files=()
  local path=""

  for path in "$ROOT_DIR"/.env "$ROOT_DIR"/.env.local "$ROOT_DIR"/.env.development "$ROOT_DIR"/.env.production; do
    if [[ -f "$path" ]]; then
      files+=("$path")
    fi
  done

  if [[ -f "$ROOT_DIR/.env.example" ]]; then
    files+=("$ROOT_DIR/.env.example")
  fi

  printf '%s\n' "${files[@]}" | awk '!seen[$0]++'
}

set_env_var_in_file() {
  local file="$1"
  local key="$2"
  local value="$3"
  local tmp=""

  touch "$file"
  tmp="$(mktemp)"
  if grep -q "^${key}=" "$file" 2>/dev/null; then
    awk -v key="$key" -v value="$value" '
      BEGIN { updated = 0 }
      $0 ~ "^" key "=" {
        print key "=" value
        updated = 1
        next
      }
      { print }
      END {
        if (!updated) {
          print key "=" value
        }
      }
    ' "$file" >"$tmp"
  else
    cat "$file" >"$tmp"
    printf '%s=%s\n' "$key" "$value" >>"$tmp"
  fi
  mv "$tmp" "$file"
}

select_environment_file() {
  local candidates=()
  local choice=""
  local index=1
  local selected=""
  local line=""

  if [[ -n "$ENV_FILE" ]]; then
    ENV_FILE="$(resolve_env_path "$ENV_FILE")"
    if [[ ! -f "$ENV_FILE" ]]; then
      echo "Environment file not found: $ENV_FILE"
      exit 1
    fi
    return 0
  fi

  while IFS= read -r line; do
    [[ -n "$line" ]] && candidates+=("$line")
  done < <(discover_env_files)

  if [[ ${#candidates[@]} -eq 0 ]]; then
    if [[ "$NONINTERACTIVE" -eq 1 ]]; then
      echo "No environment file found. Create .env from .env.example first."
      exit 1
    fi
    echo "No environment file found."
    if [[ -f "$ROOT_DIR/.env.example" ]] && prompt_yes_no "Create .env from .env.example?" "y"; then
      cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
      ENV_FILE="$ROOT_DIR/.env"
      echo "Created $ENV_FILE"
      return 0
    fi
    echo "Create .env and try again:"
    echo "  cp .env.example .env"
    exit 1
  fi

  if [[ ${#candidates[@]} -eq 1 && "${candidates[0]##*/}" != ".env.example" ]]; then
    ENV_FILE="${candidates[0]}"
    return 0
  fi

  if [[ "$NONINTERACTIVE" -eq 1 ]]; then
    if [[ -f "$ROOT_DIR/.env" ]]; then
      ENV_FILE="$ROOT_DIR/.env"
      return 0
    fi
    ENV_FILE="${candidates[0]}"
    return 0
  fi

  echo ""
  echo "Select environment file:"
  for candidate in "${candidates[@]}"; do
    local label="${candidate#$ROOT_DIR/}"
    if [[ "$label" == ".env.example" ]]; then
      label=".env.example (template — will copy to .env)"
    fi
    echo "  $index) $label"
    index=$((index + 1))
  done
  if [[ ! -f "$ROOT_DIR/.env" ]] && [[ -f "$ROOT_DIR/.env.example" ]]; then
    echo "  $index) Create new .env from .env.example"
  fi

  while true; do
    read -rp "Choice [1]: " choice
    choice="${choice:-1}"
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#candidates[@]} )); then
      selected="${candidates[$((choice - 1))]}"
      if [[ "${selected##*/}" == ".env.example" ]]; then
        cp "$selected" "$ROOT_DIR/.env"
        ENV_FILE="$ROOT_DIR/.env"
        echo "Created $ENV_FILE from .env.example"
      else
        ENV_FILE="$selected"
      fi
      return 0
    fi
    if [[ "$choice" == "$index" && ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/.env.example" ]]; then
      cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
      ENV_FILE="$ROOT_DIR/.env"
      echo "Created $ENV_FILE"
      return 0
    fi
    echo "Invalid choice. Enter 1-${index}."
  done
}

load_env() {
  if [[ -z "$ENV_FILE" ]]; then
    select_environment_file
  fi

  echo "Using environment: ${ENV_FILE#$ROOT_DIR/}"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
}

check_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Install Python 3.10+ and try again."
    exit 1
  fi
}

setup_venv() {
  if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
  fi

  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  cd "$ROOT_DIR"

  echo "Installing EmberForge package..."
  python -m pip install --upgrade pip >/dev/null
  pip install -e ".[dev,mac]" -q
}

resolve_api_key() {
  XAI_API_KEY="${XAI_API_KEY:-${GROK_API_KEY:-}}"
  export XAI_API_KEY
}

api_key_missing() {
  [[ -z "${XAI_API_KEY:-}" || "$XAI_API_KEY" == "your_xai_api_key_here" ]]
}

ensure_api_key() {
  resolve_api_key
  if ! api_key_missing; then
    return 0
  fi

  if [[ "$NONINTERACTIVE" -eq 1 ]]; then
    echo ""
    echo "XAI_API_KEY is not set in ${ENV_FILE#$ROOT_DIR/}."
    echo "Add it to the file or export it in your shell."
    exit 1
  fi

  echo ""
  echo "XAI_API_KEY is required to run EmberForge."
  echo "Get a key from https://console.x.ai/"
  XAI_API_KEY="$(read_nonempty "Enter XAI_API_KEY: " 1)"
  export XAI_API_KEY

  if [[ "${ENV_FILE##*/}" != ".env.example" ]] && prompt_yes_no "Save XAI_API_KEY to ${ENV_FILE#$ROOT_DIR/}?" "y"; then
    set_env_var_in_file "$ENV_FILE" "XAI_API_KEY" "$XAI_API_KEY"
    echo "Saved XAI_API_KEY."
  fi
}

optional_env_status() {
  local elevenlabs="not set"
  local voice_id="not set"

  if [[ -n "${ELEVENLABS_API_KEY:-}" ]]; then
    elevenlabs="set"
  fi
  if [[ -n "${ELEVENLABS_DEFAULT_VOICE_ID:-}" ]]; then
    voice_id="set"
  fi

  local mac_tts="${EMBER_MAC_TTS:-macos_say}"
  echo "Optional config:"
  echo "  EMBER_MAC_TTS:                   $mac_tts (macos_say | elevenlabs | auto)"
  echo "  ELEVENLABS_API_KEY:              $elevenlabs (device/server TTS)"
  echo "  ELEVENLABS_DEFAULT_VOICE_ID:    $voice_id"
  if [[ "$elevenlabs" == "not set" || "$voice_id" == "not set" ]]; then
    echo "  Mac voice uses macOS say by default. ElevenLabs needs both key + voice id."
  fi
}

list_persona_ids() {
  python - <<'PY'
import json
from pathlib import Path

root = Path(".")
for path in sorted((root / "personas").glob("*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"{data['id']}\t{data.get('name', data['id'])}")
PY
}

select_persona() {
  local ids=()
  local names=()
  local line=""
  local id=""
  local name=""
  local choice=""
  local default_id="${EMBER_PERSONA:-ember}"

  if [[ "$PERSONA_CHOSEN" -eq 1 ]]; then
    PERSONA="$PERSONA"
    return 0
  fi

  if [[ -n "${EMBER_PERSONA:-}" && "$NONINTERACTIVE" -eq 1 ]]; then
    PERSONA="$EMBER_PERSONA"
    return 0
  fi

  while IFS=$'\t' read -r id name; do
    [[ -n "$id" ]] || continue
    ids+=("$id")
    names+=("$name")
  done < <(list_persona_ids)

  if [[ ${#ids[@]} -eq 0 ]]; then
    PERSONA="${default_id:-ember}"
    return 0
  fi

  if [[ "$NONINTERACTIVE" -eq 1 ]]; then
    PERSONA="${default_id:-${ids[0]}}"
    return 0
  fi

  echo ""
  echo "Select persona:"
  local index=1
  local default_choice=1
  for i in "${!ids[@]}"; do
    if [[ "${ids[$i]}" == "$default_id" ]]; then
      default_choice=$((i + 1))
    fi
    echo "  $index) ${ids[$i]} — ${names[$i]}"
    index=$((index + 1))
  done

  while true; do
    read -rp "Choice [$default_choice]: " choice
    choice="${choice:-$default_choice}"
    if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#ids[@]} )); then
      PERSONA="${ids[$((choice - 1))]}"
      return 0
    fi
    echo "Invalid choice. Enter 1-${#ids[@]}."
  done
}

select_run_mode() {
  if [[ "$RUN_MODE_CHOSEN" -eq 1 ]]; then
    return 0
  fi

  if [[ "$NONINTERACTIVE" -eq 1 ]]; then
    TEXT_ONLY=0
    return 0
  fi

  echo ""
  echo "How do you want to run EmberForge?"
  echo "  1) Full voice companion (backend + microphone)"
  echo "  2) Backend only (API / curl testing)"
  local choice=""
  while true; do
    read -rp "Choice [1]: " choice
    choice="${choice:-1}"
    case "$choice" in
      1) TEXT_ONLY=0; return 0 ;;
      2) TEXT_ONLY=1; return 0 ;;
      *) echo "Invalid choice. Enter 1 or 2." ;;
    esac
  done
}

wait_for_backend() {
  local attempts=0
  local max_attempts=40

  while (( attempts < max_attempts )); do
    if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health/ready" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
    attempts=$((attempts + 1))
  done

  echo "Backend failed to start on port ${BACKEND_PORT}."
  return 1
}

start_backend() {
  echo "Starting EmberForge backend on port ${BACKEND_PORT}..."
  (
    cd "$ROOT_DIR"
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
    export XAI_API_KEY
    export EMBER_BACKEND_PORT="$BACKEND_PORT"
    exec emberforge serve --host 127.0.0.1 --port "$BACKEND_PORT"
  ) &
  BACKEND_PID=$!

  wait_for_backend
  echo "Backend is ready at http://127.0.0.1:${BACKEND_PORT}"
}

start_voice_companion() {
  echo ""
  echo "Launching Mac voice companion..."
  echo "Press ENTER when prompted to talk."
  echo ""
  (
    cd "$VOICE_DIR"
    export EMBER_BACKEND_URL="${EMBER_BACKEND_URL:-http://127.0.0.1:${BACKEND_PORT}}"
    export EMBER_WHISPER_MODEL="${EMBER_WHISPER_MODEL:-base}"
    export EMBER_PERSONA="${PERSONA}"
    export EMBER_INPUT_DEVICE="${EMBER_INPUT_DEVICE:-}"
    exec python mac_voice_companion.py
  )
}

print_banner() {
  echo "============================================================"
  echo " EmberForge Voice Companion"
  echo " Release 1.0 backend + Mac voice client"
  echo "============================================================"
}

print_launch_summary() {
  local mode="voice companion"
  if [[ "$TEXT_ONLY" -eq 1 ]]; then
    mode="backend only"
  fi

  echo ""
  echo "Launch configuration:"
  echo "  Environment: ${ENV_FILE#$ROOT_DIR/}"
  echo "  Mode:        $mode"
  echo "  Persona:     ${PERSONA:-ember}"
  echo "  Port:        ${BACKEND_PORT}"
  echo ""
}

main() {
  print_banner
  select_environment_file
  load_env
  BACKEND_PORT="${EMBER_BACKEND_PORT:-8000}"
  check_python
  setup_venv
  ensure_api_key
  optional_env_status
  select_run_mode
  select_persona
  print_launch_summary

  if ! emberforge check; then
    exit 1
  fi

  start_backend

  if [[ "$TEXT_ONLY" -eq 1 ]]; then
    echo "Backend running in text-only mode."
    echo "Test with:"
    echo "  curl http://127.0.0.1:${BACKEND_PORT}/version"
    echo "  curl http://127.0.0.1:${BACKEND_PORT}/personas"
    echo "  curl -X POST http://127.0.0.1:${BACKEND_PORT}/chat \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"message\": \"Hello\", \"persona\": \"${PERSONA}\"}'"
    echo ""
    echo "Press Ctrl+C to stop."
    wait "$BACKEND_PID"
    BACKEND_PID=""
    return 0
  fi

  start_voice_companion
}

main "$@"