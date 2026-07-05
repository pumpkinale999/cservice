#!/usr/bin/env bash
# 运维 devops 工作副本 → rsync /opt/cservice → cs-deploy deploy
#
# 用法:
#   sudo /opt/cservice/deploy/ubuntu/cs-publish.sh
#
# 环境变量:
#   CS_SRC      默认 /home/devops/cservice
#   APP_ROOT    默认 /opt/cservice
set -euo pipefail

die() { echo "[cs-publish] 错误: $*" >&2; exit 1; }
log() { echo "[cs-publish] $*"; }

SRC="${CS_SRC:-/home/devops/cservice}"
APP_ROOT="${APP_ROOT:-/opt/cservice}"
readonly _GIT_USER="${CS_GIT_USER:-devops}"

[[ -d "${SRC}/.git" ]] || die "不是 git 仓库: ${SRC}（设置 CS_SRC）"

log "SRC=${SRC} -> APP_ROOT=${APP_ROOT}"

_git_pull_if_branch() {
  if [[ "${CS_SKIP_GIT_PULL:-0}" == "1" ]]; then
    log "CS_SKIP_GIT_PULL=1，跳过 git pull"
    return 0
  fi
  local branch
  branch="$(git symbolic-ref -q --short HEAD || true)"
  if [[ -n "$branch" ]]; then
    git pull
  else
    log "detached HEAD，跳过 git pull（已 checkout tag/commit）"
  fi
}

if [[ "$(id -u)" -eq 0 ]]; then
  log "git pull（用户 ${_GIT_USER}）"
  sudo -u "${_GIT_USER}" bash -c "set -euo pipefail; cd $(printf '%q' "$SRC"); $(declare -f _git_pull_if_branch); _git_pull_if_branch"
else
  log "git pull（当前用户）"
  ( cd "$SRC" && _git_pull_if_branch )
fi

log "rsync -> ${APP_ROOT}/"
sudo rsync -a --delete \
  --exclude=.git/ \
  --exclude=.venv/ \
  --exclude=data/ \
  --exclude=.pytest_cache/ \
  "${SRC}/" "${APP_ROOT}/"

log "chown cs:cs ${APP_ROOT}"
sudo chown -R cs:cs "$APP_ROOT"

DEPLOY="${APP_ROOT}/deploy/ubuntu/cs-deploy.sh"
[[ -f "$DEPLOY" ]] || die "未找到 ${DEPLOY}"

log "cs-deploy deploy"
sudo env APP_ROOT="$APP_ROOT" "$DEPLOY" deploy

log "完成。"
