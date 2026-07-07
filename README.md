# cservice

WeCom **微信客服** backend — independent repo/process (同构 [`knowledge_base`](https://github.com/pumpkinale999/knowledge_base) / [`goal_execution`](https://github.com/pumpkinale999/goal_execution)).

**M1 · 地基 ✅**

- Alembic `001_cservice_mvp`（12 表）
- §13 ORM 模型（`app/models/entities.py`）
- `GET /api/v1/cservice/health`（含 `open_kfid_count`）
- Service token 鉴权骨架（`app/api/deps.py` · `/_internal/auth-check`）
- Seed CLI：`scripts/load_cservice_seed.py`
- 门禁：`scripts/verify_cservice_m1.sh`

**M2 · 入站管道 ✅**

- 企微 kf 回调验签解密（`app/services/wecom_kf_crypto.py`）
- `GET/POST /api/v1/cservice/kf/callback`（`app/routes_kf_webhook.py`）
- `sync_msg` 流水线 + webhook/`wx_msgid` 幂等（CS-01 · CS-15）
- API 分配 `service_state/trans` + retry + `agent_thread`（CS-03 · CS-14）
- health 扩展：`wecom_token` · `sync_cursor_age_seconds`
- 门禁：`scripts/verify_cservice_m2.sh`
- **M2 硬门**：零 `send_msg` · 零 Hermes uplink（`NoopUplinkHook`，M3 替换）

**M3 · Agent 起草环 ✅**

- Hermes WSS `/ws/hermes` · `gateway_role=cservice` 注册（`app/hermes/`）
- text inbound → `CserviceCustomerUplink` · downlink → `cservice_draft`（CS-04 · CS-08 · CS-12）
- GW 离线 uplink 重试（`cservice_uplink_retry` · §15.5）
- 门禁：`scripts/verify_cservice_m3.sh`
- **M3 硬门**：uplink/downlink 路径零 `send_msg`

**M4 · 出站 + BFF ✅**

- REST §14：`GET /customers` · `GET …/thread` · `POST …/send*` · `send-manual`
- `outbound_service` + 企微 `send_msg`（CS-02 · CS-06 · CS-07 · CS-13）
- `msg_send_fail` 角标回滚（CS-16）
- skstudio `routes_cservice_bff.py` JWT → service token 转发
- 门禁：`scripts/verify_cservice_m4.sh`

**M5 · skstudio UI ✅**

- [`skstudio`](https://github.com/pumpkinale999/skstudio) `frontend/src/cservice/` · 底 Tab「客服」· `/cservice/*`
- BFF：`GET /api/v1/cservice/health` · `auth/config.cservice_enabled`
- 门禁：[`skstudio/scripts/verify_cservice_m5.sh`](https://github.com/pumpkinale999/skstudio/blob/main/scripts/verify_cservice_m5.sh) · E2E `e2e/cservice/happy-path.spec.ts`（CS-17）
- 产品规格：[platform-docs/cservice-产品设计.md](https://github.com/pumpkinale999/platform-docs/blob/main/cservice-产品设计.md) **v0.9.7** · §0.2 MVP closure **已达成**

**M6 · 客服助手闭环 ✅（后端 + skstudio UI）**

- Alembic **`003_cservice_m6`** · 富 uplink · thread 复用 · `uplink_pending` · draft CAS
- skstudio：`AssistantReplyPanel` / `ManualReplyPanel` · BFF `expected_version`
- 门禁：
  - `./scripts/verify_cservice_m6.sh`（本仓 · CS-19–24）
  - [`skstudio/scripts/verify_cservice_m6_ui.sh`](https://github.com/pumpkinale999/skstudio/blob/main/scripts/verify_cservice_m6_ui.sh)（CS-22–24）
  - [`skstudio/scripts/verify_cservice_m6.sh`](https://github.com/pumpkinale999/skstudio/blob/main/scripts/verify_cservice_m6.sh)（编排）
  - `deploy/ubuntu/cs-deploy.sh verify-m6` · CS-25 步骤 1（health + GW）
- **CS-25** 真微信 smoke：§30.4 步骤 2–6（运维手工）

**M7 · 接待配置 + Tab 门禁 ✅**

- Alembic **`004_cservice_m7_servicer_user_id`** · internal servicer 治理 API · 企微 sync
- 门禁：`./scripts/verify_cservice_m7.sh`（本仓）
- skstudio：`routes_cservice_admin_bff` · Tab 门禁 · `ServicerSettingsDrawer` · [`verify_cservice_m7.sh`](https://github.com/pumpkinale999/skstudio/blob/main/scripts/verify_cservice_m7.sh)
- 生产部署前：**§30.4.1** migration 004 `user_id` 回填 SOP（skstudio 产品 doc）

## Architecture

```text
skstudio UI (JWT)  ──► skstudio BFF ──► cservice REST (:8093)
企微 kf 回调      ──► Nginx ──► cservice webhook (/api/v1/cservice/kf/callback)
Hermes GW         ──► cservice WSS `/ws/hermes` (M3 ✅)
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

**加载种子数据**：

```bash
alembic upgrade head
python scripts/load_cservice_seed.py --file data/cservice_seed.yaml
```

**企微 env（M2 webhook / sync）**：

| 变量 | 说明 |
| --- | --- |
| `CSERVICE_WECOM_CORP_ID` | 企业 ID |
| `CSERVICE_WECOM_SECRET` | 应用 Secret（`gettoken`） |
| `CSERVICE_KF_CALLBACK_TOKEN` | kf 回调 Token |
| `CSERVICE_KF_CALLBACK_AES_KEY` | 43 字符 EncodingAESKey |
| `CSERVICE_HERMES_WS_PATH` | WSS 路径（默认 `/ws/hermes`） |
| `CSERVICE_SERVICE_TOKEN` | REST + WSS Bearer（与 skstudio `CSERVICE_SERVICE_TOKEN` 同值） |

**Hermes Gateway 联调（M3）**：

```bash
./scripts/dev-cservice.sh
cd ../skstudio/backend && python scripts/install_cservice_assistant_profile.py
hermes -p cservice-assistant gateway install && hermes -p cservice-assistant gateway start
curl -s http://127.0.0.1:8093/api/v1/cservice/health | jq .hermes_cservice_gateway
```

**BFF 联调（M4）**：

```bash
# skstudio backend/.env
CSERVICE_ENABLED=1
CSERVICE_URL=http://127.0.0.1:8093
CSERVICE_SERVICE_TOKEN=<same as cservice CSERVICE_SERVICE_TOKEN>

# 员工 JWT → BFF
curl -H "Authorization: Bearer $JWT" http://127.0.0.1:8000/api/v1/cservice/customers
```

**验收**：

```bash
./scripts/verify_cservice_m1.sh   # M1
./scripts/verify_cservice_m2.sh   # M2 · CS-01/03/14/15
./scripts/verify_cservice_m3.sh   # M3 · CS-04/08/12
./scripts/verify_cservice_m4.sh   # M4 · CS-02/06/07/13/16
./scripts/verify_cservice_m6.sh   # M6 · CS-19–24
./scripts/verify_cservice_p4_m1.sh   # P4-M1
./scripts/verify_cservice_p4_m2.sh   # P4-M2 · CS-30–34/38/39
# skstudio：verify_cservice_p4_m3.sh · verify_cservice_p4_m4.sh（M3+M4 编排）
# 生产 CS-25 步骤 1：deploy/ubuntu/cs-deploy.sh verify-m6
# 生产 CS-33 步骤 1：deploy/ubuntu/cs-deploy.sh verify-p4-m4 · skstudio verify_cservice_p4_m4_health.sh
pytest -q
```

**本地 mock 联调（无真企微）**：fixture 在 `tests/fixtures/cservice/`；集成测覆盖 webhook → sync → draft → send。

**与 skstudio 三联调**：见 [skstudio `cservice-产品设计.md` §2.3](https://github.com/pumpkinale999/skstudio/blob/main/docs/cservice-产品设计.md)。

## Spec

| 文档 | 说明 |
| --- | --- |
| [cservice-产品设计.md](https://github.com/pumpkinale999/skstudio/blob/main/docs/cservice-产品设计.md) | 产品 + 架构 + Milestone M1–M5 · CS-xx |

## Next · M5

skstudio Tab「客服」· List/详情 UI · E2E（见产品设计 §10.1 M5）。
