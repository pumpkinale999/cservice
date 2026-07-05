#!/usr/bin/env bash
# 本地启动 cservice API（:8093 · ~/.hermes/cservice/）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
DEFAULT_PORT=8093
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=11

CHECK_ONLY=0
NO_RUN=0
INSTALL_DEPS=0
SELECTED_PYTHON=""

log() { echo "[dev-cservice] $*"; }
die() { echo "[dev-cservice] 错误: $*" >&2; exit 1; }

usage() {
  cat <<'EOF'
用法: scripts/dev-cservice.sh [选项]

  默认：创建/激活 .venv · 复制 .env · alembic upgrade · uvicorn --reload :8093

  --check-only     只检查环境
  --install-deps   强制 pip install -e ".[dev]"
  --no-run         准备环境后不启动 HTTP
  --port PORT      监听端口（默认 8093）
  -h, --help       帮助

环境变量:
  SKSTUDIO_BACKEND  同步 JWT_SECRET / CSERVICE_SERVICE_TOKEN（默认 ../skstudio/backend）
  HERMES_SHARED_ROOT  默认 $HOME/.hermes
EOF
}

pick_python_bin() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "PYTHON_BIN 不可用: $PYTHON_BIN"
    echo "$(command -v "$PYTHON_BIN")"
    return
  fi
  for c in python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1 \
      && "$c" -c "import sys; sys.exit(0 if sys.version_info[:2] >= (${MIN_PYTHON_MAJOR}, ${MIN_PYTHON_MINOR}) else 1)" 2>/dev/null; then
      echo "$(command -v "$c")"
      return
    fi
  done
  die "需要 Python >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}"
}

read_env_value() {
  local file=$1 key=$2
  [[ -f "$file" ]] || return 1
  grep -E "^${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true
}

patch_env_key() {
  local file=$1 key=$2 value=$3
  if grep -qE "^${key}=" "$file" 2>/dev/null; then
    local tmp
    tmp="$(mktemp)"
    awk -v k="$key" -v v="$value" '$1 == k { print k "=" v; next } { print }' FS='=' "$file" >"$tmp"
    mv "$tmp" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >>"$file"
  fi
}

sync_cservice_service_token() {
  local sk_backend="${SKSTUDIO_BACKEND:-$REPO_ROOT/../skstudio/backend}"
  local sk_env="$sk_backend/.env"
  local cs_env="$REPO_ROOT/.env"
  local default_token="dev-cservice-service-token"
  local sk_token="" cs_token="" final=""

  [[ -f "$sk_env" ]] && sk_token="$(read_env_value "$sk_env" CSERVICE_SERVICE_TOKEN)"
  [[ -f "$cs_env" ]] && cs_token="$(read_env_value "$cs_env" CSERVICE_SERVICE_TOKEN)"

  if [[ -n "$sk_token" ]]; then
    final="$sk_token"
  elif [[ -n "$cs_token" ]]; then
    final="$cs_token"
  else
    final="$default_token"
  fi

  patch_env_key "$cs_env" CSERVICE_SERVICE_TOKEN "$final"
  if [[ -f "$sk_env" ]]; then
    patch_env_key "$sk_env" CSERVICE_SERVICE_TOKEN "$final"
    log "已同步 CSERVICE_SERVICE_TOKEN（cservice ↔ skstudio）"
  else
    log "已设置 CSERVICE_SERVICE_TOKEN（skstudio .env 不存在，仅写入 cservice）"
  fi
}

sync_from_skstudio() {
  local sk_backend="${SKSTUDIO_BACKEND:-$REPO_ROOT/../skstudio/backend}"
  local src="$sk_backend/.env"
  [[ -f "$src" ]] || return 0
  local jwt
  jwt="$(read_env_value "$src" JWT_SECRET)"
  if [[ -n "$jwt" ]]; then
    patch_env_key "$REPO_ROOT/.env" CSERVICE_JWT_SECRET "$jwt"
    log "已从 skstudio 同步 CSERVICE_JWT_SECRET"
  fi
  sync_cservice_service_token
}

ensure_dotenv() {
  local envf="$REPO_ROOT/.env"
  local hermes_root="${HERMES_SHARED_ROOT:-$HOME/.hermes}"
  if [[ ! -f "$envf" ]]; then
    cp "$REPO_ROOT/.env.example" "$envf"
    log "已复制 .env"
  fi
  patch_env_key "$envf" CSERVICE_DB_PATH "$hermes_root/cservice/data/cservice.db"
  patch_env_key "$envf" CSERVICE_DATA_ROOT "$hermes_root/cservice"
  sync_from_skstudio
}

ensure_venv() {
  SELECTED_PYTHON="$(pick_python_bin)"
  if [[ ! -x "$REPO_ROOT/.venv/bin/python" ]]; then
    [[ "${CHECK_ONLY}" == 1 ]] && return 0
    "$SELECTED_PYTHON" -m venv "$REPO_ROOT/.venv"
    log "已创建 .venv"
  fi
}

activate_venv() {
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.venv/bin/activate"
}

ensure_pip_deps() {
  [[ "${CHECK_ONLY}" == 1 ]] && return 0
  # 始终 sync editable install，避免 pyproject 增删依赖后旧 venv 缺包（如 pycryptodome）
  if [[ "${INSTALL_DEPS}" == 1 ]] \
    || ! python -c "import fastapi, uvicorn" 2>/dev/null \
    || ! python -c "from Crypto.Cipher import AES" 2>/dev/null; then
    python -m pip install --upgrade pip setuptools wheel
    (cd "$REPO_ROOT" && pip install -e ".[dev]" --prefer-binary)
  else
    (cd "$REPO_ROOT" && pip install -q -e ".[dev]" --prefer-binary)
  fi
}

run_uvicorn() {
  [[ "${CHECK_ONLY}" == 1 || "${NO_RUN}" == 1 ]] && return 0
  log "启动 API: http://${HOST:-127.0.0.1}:${PORT}/api/v1/cservice/health"
  cd "$REPO_ROOT"
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
  exec uvicorn app.main:app --reload \
    --reload-exclude 'data/*' \
    --host "${HOST:-127.0.0.1}" --port "$PORT"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --check-only) CHECK_ONLY=1 ;;
      --install-deps) INSTALL_DEPS=1 ;;
      --no-run) NO_RUN=1 ;;
      --port) PORT="${2:?}"; shift ;;
      -h|--help) usage; exit 0 ;;
      *) die "未知参数: $1" ;;
    esac
    shift
  done
  PORT="${PORT:-$DEFAULT_PORT}"
}

main() {
  parse_args "$@"
  cd "$REPO_ROOT"
  [[ -f pyproject.toml ]] || die "未找到 pyproject.toml"
  ensure_venv
  [[ "${CHECK_ONLY}" == 1 ]] && log "检查 OK（去掉 --check-only 以启动）" && exit 0
  activate_venv
  ensure_pip_deps
  ensure_dotenv
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
  log "运行 Alembic 迁移…"
  python -m alembic upgrade head
  run_uvicorn
}

main "$@"
