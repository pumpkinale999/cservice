# cservice

WeCom **微信客服** backend — independent repo/process (同构 [`knowledge_base`](https://github.com/pumpkinale999/knowledge_base) / [`goal_execution`](https://github.com/pumpkinale999/goal_execution)).

**M1（当前）**: repo 脚手架 · `GET /api/v1/cservice/health` · Alembic `001_cservice_mvp` · JWT/service 鉴权骨架。

skstudio **UI 壳 + BFF** 在 [`skstudio`](https://github.com/pumpkinale999/skstudio) 仓库（`frontend/src/cservice/` · `routes_cservice_bff.py`）。

## Architecture

```text
skstudio UI (JWT)  ──► skstudio BFF ──► cservice REST (:8093)
企微 kf 回调      ──► Nginx ──► cservice webhook
Hermes GW         ──► cservice WSS (gateway_role=cservice)
                              │
                              ▼
                    ~/.hermes/cservice/data/cservice.db
```

## Mac / Linux 开发

| 依赖 | macOS | Linux (Ubuntu) |
| ---- | ----- | -------------- |
| Python ≥3.11 | `brew install python@3.11` | `apt install python3.11 python3.11-venv` |

**一键开发**（默认 `~/.hermes/cservice/`）：

```bash
./scripts/dev-cservice.sh
./scripts/dev-cservice.sh --check-only
```

**与 skstudio 三联调**（待 skstudio BFF 落地）：见 [skstudio `cservice-产品设计.md` §2.3](https://github.com/pumpkinale999/skstudio/blob/main/docs/cservice-产品设计.md)。

## Spec

| 文档 | 说明 |
| --- | --- |
| [cservice-产品设计.md](https://github.com/pumpkinale999/skstudio/blob/main/docs/cservice-产品设计.md) | 产品 + 架构 + Milestone M1–M5 · CS-xx |
