#!/usr/bin/env bash
# cservice Ubuntu 部署 — bootstrap + configure + deploy + health
set -euo pipefail

die() { echo "[cs-deploy] 错误: $*" >&2; exit 1; }
log() { echo "[cs-deploy] $*" ; }

_script_realpath() {
  local p="${BASH_SOURCE[0]}"
  if command -v realpath >/dev/null 2>&1; then
    realpath "$p"
  else
    readlink -f "$p" 2>/dev/null || echo "$p"
  fi
}

DEPLOY_DIR="$(cd "$(dirname "$(_script_realpath)")" && pwd)"
APP_ROOT="${APP_ROOT:-/opt/cservice}"
CS_USER="${CS_USER:-cs}"
CS_HOME="${CS_HOME:-/var/lib/cs}"
CS_PORT="${CS_PORT:-8093}"
SKSTUDIO_ENV="${SKSTUDIO_ENV:-/etc/skstudio/skstudio.env}"
CS_ENV="/etc/cservice/cservice.env"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=11

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "缺少命令: $1"; }

ensure_sudo() {
  [[ "$(id -u)" -eq 0 ]] && return 0
  sudo -v || die "需要 sudo 权限"
}

resolve_python_bin() {
  local candidate ver major minor
  for candidate in python3.12 python3.11 python3; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    ver="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    major="${ver%%.*}"
    minor="${ver#*.}"
    if (( major > MIN_PYTHON_MAJOR || (major == MIN_PYTHON_MAJOR && minor >= MIN_PYTHON_MINOR) )); then
      printf '%s' "$candidate"
      return 0
    fi
  done
  die "未找到 Python >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}"
}

render_service_unit() {
  local src="$DEPLOY_DIR/cservice.service.in"
  local out="$1"
  [[ -f "$src" ]] || die "缺少 $src"
  sed -e "s|__APP_ROOT__|${APP_ROOT}|g" \
    -e "s|__PORT__|${CS_PORT}|g" \
    "$src" >"$out"
}

read_env_value() {
  local file=$1 key=$2
  [[ -f "$file" ]] || return 1
  grep -E "^${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true
}

is_placeholder_token() {
  local value="${1:-}"
  [[ -z "$value" ]] && return 0
  [[ "$value" == *"替换"* ]] && return 0
  [[ "$value" == *"change-me"* ]] && return 0
  [[ "$value" == "dev-cservice-service-token" ]] && return 0
  ! printf '%s' "$value" | LC_ALL=C grep -q '^[A-Za-z0-9._-]\+$'
}

set_env_key() {
  local file=$1 key=$2 value=$3
  local tmp
  tmp="$(mktemp)"
  if [[ -f "$file" ]]; then
    grep -vE "^${key}=" "$file" >"$tmp" || true
  else
    : >"$tmp"
  fi
  printf '%s=%s\n' "$key" "$value" >>"$tmp"
  mv "$tmp" "$file"
}

check_env_file() {
  ensure_sudo
  sudo test -f "$CS_ENV" || die "缺少 $CS_ENV（先 bootstrap 或 configure）"
  local token_line
  token_line="$(sudo grep -E '^CSERVICE_SERVICE_TOKEN=' "$CS_ENV" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  if is_placeholder_token "$token_line"; then
    die "请在 $CS_ENV 设置 CSERVICE_SERVICE_TOKEN（运行 cs-deploy configure）"
  fi
}

preflight() {
  log "Preflight"
  need_cmd curl
  command -v systemctl >/dev/null 2>&1 || die "缺少 systemctl"
  resolve_python_bin >/dev/null
  id "$CS_USER" >/dev/null 2>&1 || die "系统用户 ${CS_USER} 不存在（先 bootstrap）"
  [[ -d "$APP_ROOT/app" ]] || die "未找到 app/（APP_ROOT=$APP_ROOT）"
  log "Preflight OK"
}

bootstrap() {
  ensure_sudo
  log "Bootstrap — 用户 ${CS_USER}、目录、systemd、env 模板"
  if ! id "$CS_USER" >/dev/null 2>&1; then
    sudo useradd --system --home "$CS_HOME" --shell /usr/sbin/nologin "$CS_USER" \
      || sudo useradd --system --home "$CS_HOME" --shell /bin/false "$CS_USER"
  fi
  sudo mkdir -p "$CS_HOME" "$APP_ROOT" "${CS_HOME}/cservice/data"
  sudo chown -R "${CS_USER}:${CS_USER}" "$CS_HOME"
  sudo mkdir -p /etc/cservice
  if [[ ! -f /etc/cservice/cservice.env ]]; then
    sudo install -m 0600 -o root -g root \
      "$DEPLOY_DIR/cservice.env.example" "$CS_ENV"
    log "已创建 $CS_ENV — 请 configure 或手工编辑密钥后再 deploy"
  fi
  local tmp
  tmp="$(mktemp)"
  render_service_unit "$tmp"
  sudo install -m 0644 "$tmp" /etc/systemd/system/cservice.service
  rm -f "$tmp"
  sudo systemctl daemon-reload
  log "Bootstrap 完成"
}

generate_kf_aes_key() {
  python3 - <<'PY'
import base64, os, re
for _ in range(10000):
    key = base64.b64encode(os.urandom(32)).decode()[:-1]
    if len(key) == 43 and re.fullmatch(r"[A-Za-z0-9]+", key):
        print(key)
        break
else:
    raise SystemExit("failed to generate alnum EncodingAESKey")
PY
}

configure() {
  ensure_sudo
  sudo test -f "$SKSTUDIO_ENV" || die "缺少 $SKSTUDIO_ENV"
  [[ -f "$CS_ENV" ]] || bootstrap
  local jwt sk_token cs_token
  jwt="$(read_env_value "$SKSTUDIO_ENV" JWT_SECRET)"
  [[ -n "$jwt" ]] || die "无法从 $SKSTUDIO_ENV 读取 JWT_SECRET"

  sk_token="$(read_env_value "$SKSTUDIO_ENV" CSERVICE_SERVICE_TOKEN)"
  cs_token="$(read_env_value "$CS_ENV" CSERVICE_SERVICE_TOKEN)"
  if is_placeholder_token "$sk_token"; then sk_token=""; fi
  if is_placeholder_token "$cs_token"; then cs_token=""; fi
  if [[ -z "$sk_token" && -z "$cs_token" ]]; then
    sk_token="$(openssl rand -hex 24)"
    cs_token="$sk_token"
    log "已生成 CSERVICE_SERVICE_TOKEN"
  elif [[ -n "$sk_token" ]]; then
    cs_token="$sk_token"
  elif [[ -n "$cs_token" ]]; then
    sk_token="$cs_token"
  fi

  sudo cp "$CS_ENV" "${CS_ENV}.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
  set_env_key "$CS_ENV" CSERVICE_JWT_SECRET "$jwt"
  set_env_key "$CS_ENV" CSERVICE_SERVICE_TOKEN "$cs_token"
  set_env_key "$CS_ENV" CSERVICE_DB_PATH "${CS_HOME}/cservice/data/cservice.db"
  set_env_key "$CS_ENV" CSERVICE_DATA_ROOT "${CS_HOME}/cservice"
  set_env_key "$CS_ENV" HOST "127.0.0.1"
  set_env_key "$CS_ENV" PORT "$CS_PORT"
  local wecom_corp wecom_secret demo_outbound
  wecom_corp="$(read_env_value "$CS_ENV" CSERVICE_WECOM_CORP_ID)"
  wecom_secret="$(read_env_value "$CS_ENV" CSERVICE_WECOM_SECRET)"
  if [[ -n "$wecom_corp" && -n "$wecom_secret" ]]; then
    demo_outbound="0"
  else
    demo_outbound="1"
  fi
  set_env_key "$CS_ENV" CSERVICE_DEMO_OUTBOUND "$demo_outbound"
  sudo chmod 600 "$CS_ENV"
  sudo chown root:root "$CS_ENV"

  sudo cp "$SKSTUDIO_ENV" "${SKSTUDIO_ENV}.bak.$(date +%Y%m%d%H%M%S)"
  set_env_key "$SKSTUDIO_ENV" CSERVICE_ENABLED "1"
  set_env_key "$SKSTUDIO_ENV" CSERVICE_URL "http://127.0.0.1:${CS_PORT}"
  set_env_key "$SKSTUDIO_ENV" CSERVICE_SERVICE_TOKEN "$sk_token"
  sudo chmod 600 "$SKSTUDIO_ENV"

  log "已同步 JWT / CSERVICE_SERVICE_TOKEN · CSERVICE_ENABLED=1（cservice ↔ skstudio）"
  log "configure 完成 — 下一步: cs-publish 或 cs-deploy deploy"
}

run_as_cs() {
  sudo -u "$CS_USER" env HOME="$CS_HOME" TMPDIR="${TMPDIR:-/tmp}" bash -lc "set -euo pipefail; cd \"$APP_ROOT\"; $*"
}

install_app() {
  log "安装 Python 依赖"
  local py_bin
  py_bin="$(resolve_python_bin)"
  ensure_sudo
  if [[ ! -x "$APP_ROOT/.venv/bin/python" ]]; then
    run_as_cs "$py_bin" -m venv .venv
  fi
  run_as_cs ".venv/bin/pip install --upgrade pip setuptools wheel"
  run_as_cs ".venv/bin/pip install -e '.[dev]' --prefer-binary"
}

migrate_db() {
  log "Database：alembic upgrade head"
  ensure_sudo
  check_env_file
  sudo mkdir -p "${CS_HOME}/cservice/data"
  sudo chown -R "${CS_USER}:${CS_USER}" "${CS_HOME}/cservice" 2>/dev/null || true
  sudo bash -lc "
    set -euo pipefail
    command -v runuser >/dev/null 2>&1 || { echo '缺少 runuser（util-linux）' >&2; exit 1; }
    set -a
    source \"${CS_ENV}\"
    set +a
    cd \"${APP_ROOT}\"
    runuser -u ${CS_USER} -- env HOME=\"${CS_HOME}\" TMPDIR=/tmp ./.venv/bin/alembic upgrade head
  "
}

load_demo_ui() {
  [[ "${CSERVICE_LOAD_DEMO_UI:-1}" == "1" ]] || { log "CSERVICE_LOAD_DEMO_UI!=1，跳过 demo 数据"; return 0; }
  log "加载 demo UI 数据（CSERVICE_DEMO_SERVICERS=${CSERVICE_DEMO_SERVICERS:-victor}）"
  ensure_sudo
  sudo bash -lc "
    set -euo pipefail
    set -a
    source \"${CS_ENV}\"
    set +a
    cd \"${APP_ROOT}\"
    runuser -u ${CS_USER} -- env HOME=\"${CS_HOME}\" TMPDIR=/tmp \
      CSERVICE_DEMO_SERVICERS=\"${CSERVICE_DEMO_SERVICERS:-victor}\" \
      ./.venv/bin/python scripts/load_cservice_demo_ui.py
  "
}

purge_sessions() {
  local keep_name="${1:-}"
  [[ -n "$keep_name" ]] || die "用法: cs-deploy purge-sessions <保留的 display_name>"
  log "purge 会话，保留 display_name=${keep_name}"
  ensure_sudo
  sudo bash -lc "
    set -euo pipefail
    set -a
    source \"${CS_ENV}\"
    set +a
    cd \"${APP_ROOT}\"
    runuser -u ${CS_USER} -- env HOME=\"${CS_HOME}\" TMPDIR=/tmp \
      ./.venv/bin/python scripts/purge_cservice_sessions.py \
      --keep-display-name $(printf '%q' "$keep_name")
  "
}

start_service() {
  ensure_sudo
  check_env_file
  sudo chown -R "${CS_USER}:${CS_USER}" "$APP_ROOT" 2>/dev/null || true
  sudo chown -R "${CS_USER}:${CS_USER}" "${CS_HOME}/cservice" 2>/dev/null || true
  sudo systemctl enable cservice.service
  sudo systemctl restart cservice.service
  sudo systemctl is-active --quiet cservice.service || {
    sudo journalctl -u cservice.service -n 40 --no-pager >&2 || true
    die "cservice.service 未 active"
  }
}

verify_health() {
  local url="http://127.0.0.1:${CS_PORT}/api/v1/cservice/health"
  log "健康检查: $url"
  local i out
  for i in $(seq 1 20); do
    if out="$(curl -sf "$url" 2>/dev/null)"; then
      echo "$out" | grep -q '"ok"' || die "health 响应异常: $out"
      log "✓ health OK"
      return 0
    fi
    sleep 1
  done
  die "health 检查失败: $url"
}

print_checklist() {
  log "---------- skstudio 对照清单 ----------"
  log "skstudio.env 须含:"
  log "  CSERVICE_ENABLED=1"
  log "  CSERVICE_URL=http://127.0.0.1:${CS_PORT}"
  log "  CSERVICE_SERVICE_TOKEN=<与 $CS_ENV 同值>"
  log "重启: sudo systemctl restart skstudio cservice"
}

deploy() {
  preflight
  install_app
  migrate_db
  load_demo_ui
  start_service
  verify_health
  print_checklist
  log "Deploy 完成"
}

usage() {
  cat <<EOF
用法: deploy/ubuntu/cs-deploy.sh <bootstrap|configure|deploy|health|demo|purge-sessions>

  bootstrap    创建 cs 用户、数据目录、systemd unit、env 模板
  configure    从 /etc/skstudio/skstudio.env 同步 JWT + token · 开启 CSERVICE_ENABLED
  deploy       pip install + alembic + demo UI + 启动 cservice.service + health
  demo         仅加载 demo UI 数据（幂等）
  purge-sessions <display_name>  删除除指定客户外的全部会话（运维清理）
  health       仅 curl /api/v1/cservice/health

环境变量: APP_ROOT CS_PORT CS_USER SKSTUDIO_ENV CSERVICE_DEMO_SERVICERS CSERVICE_LOAD_DEMO_UI
EOF
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    bootstrap) bootstrap ;;
    configure) configure ;;
    deploy) deploy ;;
    demo) load_demo_ui ;;
    purge-sessions) purge_sessions "${2:-}" ;;
    health) verify_health ;;
    -h|--help|help) usage ;;
    *) die "用法: $0 bootstrap|configure|deploy|health|demo|purge-sessions" ;;
  esac
}

if [[ "${CS_DEPLOY_TEST_MODE:-}" == 1 ]]; then
  :
elif [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi
