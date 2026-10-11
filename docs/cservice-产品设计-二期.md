# cservice · 二期 · 企微客户群（agent-inside）

- **文档类型**：~~二期产品共识 + 架构验收真源~~ → **历史存档**
- **版本**：**v0.3.8**
- **状态**：**废止为运行真源**（2026-07-31 · 随 cservice **P0** 一并拆除）· 见 [平台控制面与Postgres迁移共识.md](../../platform_docs/平台控制面与Postgres迁移共识.md) **D1/D19** · 一期历史 [cservice-产品设计.md](./cservice-产品设计.md)
- **产品定位（历史）**：企微客户群 · 多对1 · 与一期 kf 同构的人机协同

**关联文档**

| 文档 | 用途 |
| ---- | ---- |
| [cservice-产品设计.md](./cservice-产品设计.md) | **一期真源**：微信客服 kf · 1:1 · M1–M7 |
| [TODO.md](../../platform_docs/TODO.md) | 实现勾选 · [§ P4](../../platform_docs/TODO.md#cservice-p4) |
| [Personal-Assistant产品设计.md](../../platform_docs/hermes-self/Personal-Assistant产品设计.md) | Hermes profile / `gateway_role` 隔离 |
| [企微 · 智能机器人 · 接收消息](https://developer.work.weixin.qq.com/document/path/100719) | `aibot_*` 回调 · 群 `chatid` |
| [企微 · 智能机器人 · 主动回复](https://developer.work.weixin.qq.com/document/path/101138) | `response_url` · 群 reply 模式 |

**代码仓库（normative · 与一期同构）**

| Repo | 二期增量 |
| ---- | -------- |
| **`cservice`** | **`cservice_wg_*` 域表** · internal ingress · **`WecomAibotClient` 出站（HTTP `response_url`）** · WSS `gateway_role=cservice-group` |
| **`skstudio`** | Tab「客服」内 **私聊 \| 客户群** · BFF `…/groups/*` · 复用回复区组件 |
| **`hermes-agent`** | **`hermes-gateway-cservice-assistant`**（kf WSS + **复用** 群 aibot ingress）+ **`cservice-group-assistant` GW**（群起草 WSS） |

---

## 文档地图

| 部分 | 章节 | 读谁 |
| ---- | ---- | ---- |
| 范围与一句话 | §0 | 全员 |
| 产品目标与非目标 | §1 | 产品、研发 |
| 与一期关系 | §2 | 架构、PM |
| 架构决策（冻结） | §3 | 架构、后端 |
| 与其他模块边界 | §4 | 全员 |
| 企微 · 智能机器人 | §5 | 运维、后端 |
| Hermes · 群助手 Agent | §6 | 研发、运维 |
| skstudio · 群客服 UI | §7 | 产品、前端 |
| 数据流 | §8 | 后端、架构 |
| 默认行为 | §9 | 产品、研发 |
| 领域模型 · migration 005 | §10 | 后端 |
| Milestone · P4 | §11 | 研发、PM |
| 验收 CS-29+ | §12 | QA |
| WSS 协议 delta | §13 | 后端 |
| REST API 纲要 | §14 | 前后端 |
| 运维与环境变量 | §15 | 运维 |
| 生产试点 checklist | §17 | 运维、QA |
| 修订记录 | §18 | 全员 |

---

## 0. 范围

### 0.1 一句话

**在 skstudio「客服」Tab 内新增「客户群」子视图：** **1 个 Bot 服务多个群**（每群原则上对应 **1 个客户**）；成员 **@ Bot** 的 **text** 消息经 **ingress GW → cservice** 入库 → **群助手** Hermes 起草（**复用健管 Agent 大脑**）→ 接待在 UI **审后发** → **cservice** 调企微 **`response_url`** 出站，Bot **「数坤坤健康助手」** 在群内可见回复（§5.6 · D-P4-13）。**

> **P4 范围**：**仅群 `@ Bot` 入站 · 仅 text**。**不含** A 类定时广播（**P4+** · §9.1）。单聊 Bot **P4+**（§9.5）。

### 0.2 与一期（微信客服 kf）对照

| 维度 | 一期 · kf | 二期 · 企微群 |
| ---- | --------- | ------------- |
| **拓扑** | **1 客户 : 1 客服号** | **多成员 : 1 Bot**（真人同事可选同在群内） |
| **企微 API** | 微信客服 `kf_*` | **智能机器人** `aibot_*` |
| **Ingress** | kf webhook → **cservice** | aibot WSS → **ingress GW** → cservice internal |
| **身份键** | `(open_kfid, external_userid)` | **`(ibot_id, chatid)`** + `sender_userid` |
| **智能服务** | agent-inside | **同一套** agent-inside |
| **UI** | List 按 **客户会话** | List 按 **群**（`chatid`）· **公共池**（D-P4-14） |
| **出站** | cservice · `WecomKfClient.send_msg` | cservice · **`WecomAibotClient` POST `response_url`**（D-P4-13） |
| **对外显示名** | **数坤坤健管师**（人像前台 · AI 辅助） | **数坤坤健康助手**（Bot 前台 · 透明智能体） |
| **MVP 消息** | text（一期） | **text only**（P4） |

**Normative**：并列通道 · **不**合并 List · **不**共用 kf 表写入路径（`cservice_wg_*` 分表 · D-P4-11）。

### 0.3 二期 closure 定义（normative）

同时满足：

| 类 | 含义 | 验收 |
| --- | --- | --- |
| **管道** | ingress GW 收 aibot → cservice 入库 → 人审后 Bot 出站 | CS-29 · CS-30 |
| **Agent** | `cservice-group-assistant` · 禁止未 UI 审批被动回复 | CS-31 · CS-34 |
| **UI** | 「客户群」子视图 List + 详情 + 助手/人工区（交互 **复用 kf 回复区**） | CS-35 · CS-36 |
| **消息类型** | **仅 text** 入站/出站 | CS-29 · CS-30 |
| **隔离** | 与 kf GW / Master / PA **零路由共享** | CS-31 |
| **生产试点** | 真实客户群 @ Bot → 人审 → 群可见 Bot 文本回复 | CS-33 |

**不纳入 P4 closure**：**A/B 类定时广播**（§9.1 · 生产后续 **正式开关** 启用 · **P4+**）· 真·冷启动群广播 · 单聊 Bot · 图片/语音 · 会话存档。

### 0.4 明确不在二期

| 项 | 说明 |
| --- | --- |
| 替代一期 kf 1:1 | 并列；转 kf 私聊链 **P4+** |
| 全群旁听 / 截获员工客户端 | **不**做 |
| 会话内容存档 | **不**作 ingress |
| A 类 cron / 群广播任务 | **P4+**（§9.1 · 表/开关可预留 · **本期不实现**） |
| 无锚点冷启动群广播 | **P4+**（§9.3 策略 3） |
| 非 text 消息 | **P4+** |
| M8 运营 | 见 [一期 §10 P3](./cservice-产品设计.md) |

---

## 1. 产品目标

1. **统一智能服务**：kf 与企微群均为 agent-inside。
2. **多对1 社群接待**：Bot 为群内正式接待成员。
3. **人机协同**：被动 **必须 UI 审后发**（与 kf 同构）；Bot 发出前 **不**自动出站。
4. **品牌分场景**：kf **健管师**（人像前台）· 群 **健康助手**（Bot 前台）。
5. **可扩展**：UI/回复区复用 kf；域与 ingress **分表分 GW**；定时广播 **P4+**。

---

## 2. 与一期文档的引用关系

| 一期章节 | 二期用法 |
| -------- | -------- |
| §0.2 MVP closure | **前提** |
| §2 双仓 · D-CS-17 | **继承** |
| §2.5 One Reality | BFF join `users` 展示名 |
| §3 · CS-08 | **扩展** `gateway_role=cservice-group` |
| §5 · §6.4 回复区 | **复用** UI 模式 |
| §6.1.1 Tab 门禁 | **复用** `can_access_tab`（§7.1） |
| §14 BFF 模式 | **扩展** `…/groups/*`（§14） |
| §8.1 kf 分配 | **不适用** |

---

## 3. 架构决策（冻结 · D-P4）

| ID | 决策 | 说明 |
| ---- | ---- | ---- |
| **D-P4-1** | **双通道、一智能服务** | kf 与 `wecom_group` 并列 |
| **D-P4-2** | **多对1 · Bot 即接待面** | List 按 `chatid` |
| **D-P4-3** | **Bot 像员工** | 群内可见 · 人审后 Bot 身份回复 |
| **D-P4-4** | **ingress = @ Bot（群）** | v1 不旁听 |
| **D-P4-5** | **Thread 键** | `(ibot_id, chatid)` |
| **D-P4-6** | **角标** | @ Bot 未覆盖轮次 0/1 |
| **D-P4-7** | **UI 子 Tab** | 私聊 \| 客户群 |
| **D-P4-8** | **主动 A/B** | **P4+** · 设计见 §9.1–§9.3 · 生产 **正式开关** 后续启用 |
| **D-P4-9** | **双 GW 硬隔离** | ingress GW ≠ 起草 GW ≠ kf GW |
| **D-P4-10** | **真人原生发言** | 不入 cservice transcript |
| **D-P4-11** | **分表** | `cservice_wg_*` · **不**改 kf message 写入链 |
| **D-P4-12** | **Ingress 在 Hermes GW** | aibot WSS **仅** ingress unit 订阅；cservice **不**直连 openws |
| **D-P4-13** | **cservice 统一出站** | 人审后 **cservice** `WecomAibotClient` **HTTP POST `response_url`**；ingress GW **只收不写** |
| **D-P4-14** | **公共池 List** | 与 kf **D-CS-18** 同构 · `can_access_tab` 可见 **全部已注册群** |
| **D-P4-15** | **多 @ 合并** | 同群未 outbound 期间多成员/连发 @ → **一轮** draft · 锚点取 **最新** `response_url` |
| **D-P4-16** | **同一健管大脑** | skills/知识 **复用** `cservice-assistant` · **独立** profile/GW/thread（D-P4-9） |
| **D-P4-17** | **P4 仅 text** | 入站/出站/UI **仅** text |
| **D-P4-18** | **1 Bot 多群** | 单 `ibot_id` · 每群 `chatid` · 原则上 **一群一客户** |
| **D-P4-19** | **群入网 · 方案 A** | **生产**：Bot 已入群 + 首次 @ → **自动建档** · **无需** 逐群手填 `chatid`（§9.4） |

---

## 4. 与其他模块边界

（同 v0.1 · §4.1 反模式保留）

| 反模式 | 原因 |
| ------ | ---- |
| cservice 与 ingress GW 双订阅同一 `bot_id` | 重复消费 / 竞态 |
| kf `send_msg` 发群 | API 域错误 |
| 改 `open_kfid` 塞 `chatid` | 键污染 |

---

## 5. 企微 · 智能机器人

### 5.1 角色与 ID

| 概念 | ID | 说明 |
| ---- | ---- | ---- |
| 智能机器人 | `ibot_id` | 企微 AI Bot |
| 群 | `chatid` | `chattype=group` |
| 发送方 | `sender_userid` | 回调 `from.userid`；展示名见 §5.5 |
| 接待人员 | `users.id` | BFF `X-Actor-User-Id` |

### 5.2 二期交互面

| 阶段 | 组件 |
| ---- | ---- |
| 收消息 | **ingress GW** · `aibot_subscribe` / `aibot_msg_callback` |
| 写域 | **cservice** · `POST /internal/wecom-group/ingress` |
| 起草 | **cservice-group-assistant GW** ↔ cservice WSS |
| 被动出站 | 人审后 **cservice** · `WecomAibotClient.post_response(response_url)`（§5.6 · D-P4-13） |
| 主动 A 类 | **P4+** · cservice 读 anchor · §9.3 |

### 5.3 与 kf 差异

| 项 | kf | 企微群 |
| --- | --- | --- |
| 入站 | kf webhook | aibot WSS → ingress GW |
| 出站 API | `kf/send_msg` HTTP | **`response_url` HTTP POST**（非 kf · 非 GW 代发） |
| 群冷发 | — | 企微 **禁止** 群内 `aibot_send_msg` 无锚冷发 |
| 显示名策略 | `kf_account_short_name` | **`bot_display_name` = 数坤坤健康助手** |
| 分配 | servicer 轮询 + trans | **无** · 公共池（D-P4-14） |

### 5.4 Ingress 与 GW 分工（normative · v0.3.7）

**原则（D-P4-12）**：**一个 `bot_id` 仅一个 aibot WSS 订阅进程** — 与 kf 共用 **`hermes-gateway-cservice-assistant`**（**非**独立 ingress GW · **非**独立 Bot 凭证）。

```text
┌─────────────────────────────────────────────────────────────────┐
│ 企微 openws (aibot WSS)                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ aibot_msg_callback
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ hermes-gateway-cservice-assistant（复用 kf 客服 GW）             │
│  · skstudio WSS → cservice（role=cservice · kf 起草）            │
│  · wecom + cservice_ingress_mode（群 @ text → cservice HTTP）    │
│  · 同一 WECOM_BOT_ID/SECRET · WECOM_GROUP_POLICY=open            │
│  · **不**代发出站（D-P4-13）                                       │
└────────────┬───────────────────────────────┬────────────────────┘
             │ HTTP + service token          │ kf uplink/downlink
             ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│ cservice :8093                                                   │
│  · cservice_wg_* 入库 · uplink · draft · REST/BFF                │
│  · 人审后 WecomAibotClient → POST response_url（同 kf 出站层）   │
│  · WSS /ws/hermes?role=cservice-group                            │
└────────────┬────────────────────────────────────────────────────┘
             │ WSS uplink/downlink（群）
             ▼
┌────────────────────────────┐
│ hermes-gateway-cservice-   │
│ group-assistant            │
│  · 仅群起草 · 零 Tool        │
│  · 复用健管 skills（D-P4-16）│
└────────────────────────────┘
```

| 单元 | systemd 建议名 | 连接 | **禁止** |
| ---- | -------------- | ---- | -------- |
| **kf + 群 ingress GW** | `hermes-gateway-cservice-assistant` | cservice WSS kf role + WeCom openws 群 ingress | 独立第二 aibot 订阅 · 代发出站 |
| **群 Assistant GW** | `hermes-gateway-cservice-group-assistant` | cservice WSS `cservice-group` only | 订阅 aibot · 连 Master WSS |

**internal ingress 载荷（最小）**：

```json
{
  "ibot_id": "ibotxxx",
  "chatid": "wrxxx",
  "chattype": "group",
  "msgid": "…",
  "sender_userid": "…",
  "text": "…",
  "response_url": "…",
  "reply_req_id": "…（可选 · debug/raw）",
  "raw": { }
}
```

### 5.5 发送方显示名（normative）

1. **首选**：BFF 调 skstudio `users` / 企微 **userid → 明文** 映射（若 sender 为员工且可解析）。  
2. **外部联系人**：cservice 缓存 `cservice_wg_member(display_name)`；首次 @ 时 userid 占位，后台 **异步** 调企微 contact API  enrichment（P4-M2 可降级为 userid 尾缀）。  
3. **UI / uplink【发送者】**：BFF join 后下发 `sender_display_name`；**不**在 cservice 存员工 org_path。

### 5.6 出站 · cservice 统一发送（normative · D-P4-13）

与一期 kf **`outbound_service` + `WecomKfClient`** 同构：

1. ingress 入库时写入 **`cservice_wg_reply_anchor`**：`response_url` · `expires_at`（企微默认 **约 1h** · **每 URL 仅可 POST 一次**）。
2. 接待 UI 发送 → cservice **`wg_outbound_service`** → **`WecomAibotClient.post_response(url, text)`**。
3. 成功 → `cservice_wg_message` outbound · `delivery_status=sent` · audit。
4. **ingress GW 不参与出站**；cservice **不**为出站再开 aibot WSS（D-P4-12）。

**合并 @ 与锚点（D-P4-15）**：多 @ 合并为一轮 uplink；出站消耗 **最新** 一次 @ 的 `response_url`；更早 URL 作废可接受。

---

## 6. Hermes · 群助手 Agent

### 6.1 与 kf 助手关系（D-P4-16）

| 层 | 约定 |
| --- | --- |
| **大脑** | **复用** 健康管理 skills · 知识库 · 领域 prompt（与 `cservice-assistant` 同源） |
| **运行时** | **独立** profile `cservice-group-assistant` · 独立 GW · 独立 `cservice_wg_agent_thread` |
| **uplink** | 群上下文模板（§6.3）· 与 kf 客户 uplink **不同形** · **同一能力域** |

### 6.2 行为约束

- **禁止**未 UI 审批的被动自动回复（与 kf 相同）。
- **零 Tool** · 仅起草。

### 6.3 Uplink 上下文（normative）

```text
【群名称】{group_display_name}
【智能机器人】数坤坤健康助手
【发送者】{sender_display_name}
【近期对话】（最近 **10** 条 text inbound/outbound · 同 kf §5.4 截断规则 · 仅 `cservice_wg_message` · **不含** `draft_only`）
…
【本轮待回复】
{merged_pending_inbound_text}（§9.6 · 同轮多 @ 合并）

【起草要求】
- 只回复「本轮待回复」
- 输出可直接发送的正文，无前后缀
```

### 6.4 Gateway

| 项 | 约定 |
| --- | ---- |
| 起草 GW | `gateway_role=cservice-group` |
| WSS URL | `CSERVICE_HERMES_WS_URL` + `?role=cservice-group`（与 kf 分 role） |
| Profile | `cservice-group-assistant`（skills **对齐** kf 助手 · GW **隔离**） |

---

## 7. skstudio · 群客服 UI

### 7.1 Tab 与权限

```text
底 Tab「客服」
├── 子 Tab「私聊」   → 一期 kf
└── 子 Tab「客户群」 → 二期
```

- 路由：`/cservice` · `/cservice/s/:sessionId` · `/cservice/groups` · `/cservice/groups/s/:sessionId`
- **权限**：复用 **`GET /api/v1/cservice/access`** · `can_access_tab` · **公共池**（D-P4-14 · 同 kf **D-CS-18**：不按群绑接待过滤 List）
- **WG 门禁**：`GET /cservice/health` · `wecom_group_ingress=true` 时展示「客户群」子 Tab；cservice `CSERVICE_WG_ENABLED=0` 时 BFF 透传 `503 wg_disabled`

### 7.2 群 List

| 元素 | 说明 |
| ---- | ---- |
| 主标题 | `group_display_name`（**群名** · seed 或 chatid 占位） |
| 副标题 | **数坤坤健康助手** + 最后 Bot 通道消息摘要 |
| 角标 | @ Bot 待回复 0/1 |

> **产品确认（Normative）**：List **主标题用群名即可**，不单独再列「主客户姓名」字段；「一群一客户」由运营在 seed **群名** 中体现（如「张三 · VIP 健管群」）。消息流 inbound 仍用 `sender_display_name` 区分 **谁 @ 了 Bot**。

### 7.3 群详情 · 消息流

Transcript 标签（与一期 MessageThread 对齐）：

| 方向 | 标签 |
| --- | --- |
| inbound | `sender_display_name` |
| outbound · agent / draft_only | **数坤坤健康助手** |
| outbound · user（编辑发送） | 登录用户 `currentUserDisplayName` |

**回复区**：复用 `AssistantReplyPanel` / `ManualReplyPanel` · `expected_version` CAS · **人审后 Bot 出站**（D-P4-13）。

### 7.4 testid

`cservice-channel-tabs` · `cservice-group-list-panel` · `cservice-group-row-{chat_id}` · `cservice-group-detail-view` · `cservice-broadcast-task-*`（**P4+**）

---

## 8. 数据流

### 8.1 被动 · @ Bot

```text
成员 @ Bot
  → ingress GW（aibot WSS）
  → POST /internal/wecom-group/ingress
  → cservice_wg_* 入库 + anchor 更新
  → uplink → cservice-group-assistant GW
  → draft → BFF 轮询
  → 人审 → cservice POST response_url（WecomAibotClient）
  → outbound + audit
```

### 8.2 主动 · A 类定时（P4+ · 本期不实现）

```text
（P4+）cron → anchor 有效 → 模板 → cservice POST response_url
```

### 8.3 架构图

**Normative 架构图见 §5.4**（ASCII）。一期 mermaid 总览见 [cservice-产品设计.md §8](./cservice-产品设计.md) · 群通道以本文 §5.4 为准。

---

## 9. 默认行为

| 项 | 约定 |
| ---- | ---- |
| 入站 | 群 **@ Bot** |
| 连发合并 | 同群连续 @ 未 outbound → **一轮** draft（D-P4-15） |
| 多成员 @ | **合并**为一轮 · uplink 聚合文本 · 锚点 **最新** `response_url` |
| 出站审批 | 被动必须 UI 发送 · **cservice** 出站 |
| 消息类型 | **text only**（D-P4-17） |
| 真人原生发言 | 不入库 |

### 9.1 主动消息 A/B（P4+ · 本期不实现）

A 类模板 cron · B 类 Agent 预览 — **设计保留** · **开发关闭** · 生产后续经 **`CSERVICE_WG_BROADCAST_ENABLED`** 等 **正式开关** 启用（migration/API **P4+** · 见 §9.3）。

### 9.2 群广播任务（P4+ 设计草案）

| 字段 | 说明 |
| ---- | ---- |
| `chatid` | 目标群 |
| `schedule` | cron |
| `body` | A 类模板 |
| `enabled` | 开关 |
| `require_anchor` | 默认 **true** |
| `last_run_at` / `last_status` | 审计 |

### 9.3 群主动发送 · 锚点策略（normative）

**传输层（P4+ 已落地）**：`cservice_group_send` → ingress GW → 企微 `aibot_send_msg`（`chat_type=2`）。**manual / cron / alert** 等 trigger 共用此路径；UI「人工直发」是 `trigger=manual` 的一种，**不**复用已消耗的 `response_url`。

| 优先级 | 策略 | P4 |
| ------ | ---- | --- |
| 1 | **Follow-up 窗**：`response_url` 有效期内发 A 类 | **P4+ 验收** |
| 2 | 引导 kf 私聊 | 产品文案 |
| 3 | 冷广播 API | **P4+** |

### 9.4 群入网（normative · D-P4-19）

**企微侧（不可省）**：每个客户群须 **群主/管理员在企微客户端把 Bot 拉进群** 一次；无「Bot 自动加入全部客户群」API。

**系统侧（方案 A · 产品确认）**：Bot 已在群内且有人 **@ Bot** 时，**自动入网** — **不要求** 运营事先填 `chatid`。

```text
群主把「数坤坤健康助手」拉进客户群（每群一次 · 企微客户端）
  ↓
成员 @ Bot（text）
  ↓
ingress GW 收到 aibot 回调（chatid 在 payload 里）
  ↓
cservice：未知 chatid → upsert cservice_wg_group（display_name 暂 chatid 短码 · 可后补）
  ↓
skstudio「客户群」List 自动出现 · 正常起草/人审/出站
```

| 模式 | 配置 | 用途 |
| ---- | ---- | ---- |
| **生产（默认）** | `CSERVICE_WG_AUTO_REGISTER=1` · ingress `WECOM_GROUP_POLICY=open` | 新群 **只拉 Bot + @**，不填 chatid |
| **试点/白名单** | `CSERVICE_WG_AUTO_REGISTER=0` + seed 或 ingress `allowlist` | 仅允许已知 chatid（§17 首跑可用） |

**两层门禁（生产方案 A）**

| 层 | 配置 | 作用 |
| --- | --- | --- |
| **企微** | Bot **是否在群内** | 不在群 = 收不到 @ |
| **ingress GW** | `WECOM_GROUP_POLICY=open` | Bot 已进的 **任意群** @ 都转发 cservice（**不**维护 `WECOM_GROUP_ALLOW_FROM` 逐群列表） |
| **cservice** | `CSERVICE_WG_AUTO_REGISTER=1` | 首次 @ **自动** `upsert cservice_wg_group` |

> **勿混用**：生产若 `AUTO_REGISTER=1` 但 GW 仍 `allowlist` 且未加 chatid，新群 @ 会在 **ingress 被挡**，List 永远不会出现。

**seed YAML（可选）**：仅用于 **预填群显示名** 或 **试点白名单**，**非** 生产逐群必填。

```yaml
# cservice/data/cservice_wg_seed.yaml（可选 · 生产可空文件或只写 ibot_id）
ibot_id: "ibot_REPLACE_ME"
bot_display_name: "数坤坤健康助手"
groups: []   # 生产方案 A：留空；试点可列 1～N 个 chatid + display_name
```

**P4+ 增强（非阻塞）**：cron 调 `externalcontact/groupchat/list` **同步群名** · 仍 **不** 替代「Bot 入群 + @」触发建档。

### 9.5 单聊 Bot（P4+）

不在 P4 closure；spec 预留 `chattype=single` · List 仍仅群。

### 9.6 多 @ 合并规则（normative · D-P4-15）

| 场景 | 行为 |
| --- | --- |
| 同成员连发两条 @，未 outbound | 合并【本轮待回复】· **不**新建 thread |
| 成员 A @ 后成员 B @，未 outbound | **一轮** draft · uplink 含 A+B 文本（或结构化列表） |
| 出站 | 使用 **最后一次** @ 携带的 `response_url` |
| 角标 | 仍为 0/1 · outbound 后清零 |

---

## 10. 领域模型 · migration 005（normative）

**Revision**：`005_cservice_p4_wecom_group`（`down_revision=004_cservice_m7_servicer_user_id`）

**原则（D-P4-11）**：**平行表** · kf 迁移与 ORM **零行为变化**。

### 10.1 表概要

**`cservice_wg_group`**

| 字段 | 说明 |
| ---- | ---- |
| `chatid` | PK |
| `ibot_id` | FK 逻辑 |
| `display_name` | 群名 |
| `status` | `active` / `disabled` |
| `created_at` | |

**`cservice_wg_session`**

| 字段 | 说明 |
| ---- | ---- |
| `id` | PK uuid |
| `chatid` | FK |
| `pending_reply_count` | 0/1 轮次 |
| `last_activity_at` | List 排序 |

**`cservice_wg_message`**

| 字段 | 说明 |
| ---- | ---- |
| `id` | PK |
| `session_id` | FK |
| `direction` | inbound/outbound |
| `sender_userid` | inbound |
| `sender_type` | agent/user（outbound） |
| `content` | text |
| `delivery_status` | sent/failed/draft_only/… |
| `created_at` | |

**`cservice_wg_draft`** · **`cservice_wg_audit_log`** — 同 kf 语义。

**`cservice_wg_agent_thread`**

| 字段 | 说明 |
| ---- | ---- |
| `id` | int PK · Hermes thread_id |
| `ibot_id` + `chatid` | **UNIQUE** |
| `uplink_pending` | 同 kf |

**`cservice_wg_reply_anchor`**

| 字段 | 说明 |
| ---- | ---- |
| `chatid` | PK |
| `response_url` | 出站用 · ingress 入库时写入 |
| `expires_at` | 约 1h（以企微为准） |
| `source_msgid` | 最近一次 @ 的 msgid |
| `updated_at` | |

> **`cservice_wg_broadcast_task`**：**不在 migration 005** · **P4+** migration 006 或配置 YAML。

**`cservice_wg_member`**（可选 P4-M2）

| 字段 | 说明 |
| ---- | ---- |
| `chatid` + `userid` | PK |
| `display_name` | 缓存 |

---

## 11. Milestone · P4

| ID | 交付 | 验收 |
| ---- | ---- | ---- |
| **P4-M1** | migration 005 · internal ingress · anchor · auto-register · `WecomAibotClient` 骨架 · health | CS-29 · **CS-41** · **✅ cservice 2026-07-07** |
| **P4-M2** | ingress GW + group-assistant GW · uplink/downlink · **出站 E2E** · CAS · **多 @ 合并** | CS-30–34 · CS-38 · **CS-39** · **✅ 2026-07-07** |
| **P4-M3** | 子 Tab · BFF · UI · 复用回复区 | CS-35–36 · **✅ skstudio 2026-07-07** |
| **P4-M4** | 生产试点 §17 | CS-33 · **✅ 运维自动化 2026-07-07** |
| ~~P4-M5~~ | ~~A 类 broadcast + cron~~ | **P4+**（§9.1） |

```text
PR-1  cservice 005 + ingress internal + WecomAibotClient + verify_p4_m1.sh
PR-2  ingress GW + group-assistant GW + profile + outbound E2E + verify_p4_m2.sh
PR-3  skstudio BFF groups/* + UI + tests
PR-4  prod pilot §17 + verify_p4_m4*.sh
（P4+）PR-n  broadcast_task + cron + CS-37
```

---

## 12. 验收（CS-29–41 · normative）

| ID | 场景 | 通过标准 |
| ---- | ---- | -------- |
| CS-29 | 群 @ Bot 入站 | ingress → DB `cservice_wg_message` inbound |
| CS-30 | 人审出站 | UI 发送 → cservice POST `response_url` → 群内 Bot **text** 可见 |
| CS-31 | 通道隔离 | **无** kf `cservice_message` / kf thread 写入 |
| CS-32 | Thread 复用 | 同 `(ibot_id, chatid)` 再次 @ → 同 `wg_agent_thread.id` |
| CS-33 | 生产试点 | 真实群 E2E（§17）· **`verify_cservice_p4_m4_health.sh`** + 手工步骤 3–7 |
| CS-34 | 富 uplink | body 含【群名称】【智能机器人】【发送者】【近期对话】【本轮待回复】 |
| CS-35 | 子 Tab UI | 「私聊 \| 客户群」切换 · 路由正确 |
| CS-36 | 回复区 | `pending_draft` · generating · 编辑发送 **双条** draft_only+user |
| CS-37 | A 类广播 | **P4+** · anchor 窗内 cron 模板 |
| CS-38 | 并发发送 | 两接待同 draft 发送 → 一条 409 CAS |
| CS-39 | 多 @ 合并 | A、B 连续 @ 未 outbound → **一轮** draft · 一次出站 |
| CS-40 | 仅 text | 非 text 入站 **ingress 忽略**（debug 日志 · 不入库） |
| CS-41 | 自动建档 | 新群 **未 seed** · Bot 在群内 · 首次 @ → `cservice_wg_group` 出现 · List 可见（**D-P4-19**） |

**测试落点**：`test_cservice_wg_*.py` · `test_cservice_group_bff.py` · `frontend/src/cservice/**/*.test.tsx` · `e2e/cservice/group-*.spec.ts` · **`scripts/verify_cservice_p4_m1.sh`** · `verify_cservice_p4_m2.sh` · **`verify_cservice_p4_m3.sh`** · **`verify_cservice_p4_m4.sh`**

---

## 13. WSS 协议 delta（P4）

**真源**：一期 [§15 · §22.3](./cservice-产品设计.md) · 群通道 **仅替换 role 与 uplink 形**。

| 项 | kf | 企微群 |
| --- | --- | --- |
| WSS URL | `…/ws/hermes?role=cservice` | `…/ws/hermes?role=cservice-group` |
| `gateway_role` | `cservice` | `cservice-group` |
| Profile | `cservice-assistant` | `cservice-group-assistant` |
| Thread 键 | `(open_kfid, external_userid)` | `(ibot_id, chatid)` |
| uplink body | §5.4 kf 模板 | §6.3 群模板 |
| uplink type | `cservice_customer_uplink` | **`cservice_group_uplink`** |
| uplink trigger | `trigger_wx_msgid` | **`trigger_source_msgid`** |
| downlink | 同形 · `final`/`failed` + draft 落库 | **同形** · 写 `cservice_wg_draft` · downlink 带 `trigger_source_msgid` |

**群 uplink 帧（最小 · normative）**：

```json
{
  "type": "cservice_group_uplink",
  "protocol_version": 1,
  "thread_id": 7,
  "session_id": "uuid",
  "ibot_id": "ibotxxx",
  "chatid": "wrxxx",
  "trigger_source_msgid": "msgid_latest",
  "body": "§6.3 富文本"
}
```

**Normative**：downlink JSON · `uplink_pending` · draft `version` · CAS **不重定义** — 实现复用 cservice Hermes bridge，按 `role` 路由到 `cservice_wg_*` ORM。

---

## 14. REST API 纲要（P4）

**真源**：cservice `:8093` · BFF 同路径转发（同 [一期 §14](./cservice-产品设计.md)）。

**skstudio BFF（M3 ✅）**：`/api/v1/cservice/groups` · `/api/v1/cservice/groups/{session_id}/thread` · `/api/v1/cservice/wg/drafts/{draft_id}/send*` · `/api/v1/cservice/groups/{session_id}/send-manual` · thread inbound 经 BFF join `sender_display_name` · List 补 `bot_display_name`。

### 14.1 参与者面（员工 JWT · Tab 门禁）

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| `GET` | `/groups` | 群 List · 角标 · 摘要 |
| `GET` | `/groups/{session_id}/thread` | 消息流 + `pending_draft` + `uplink_pending` |
| `POST` | `/wg/drafts/{draft_id}/send` | 原样发送 · `expected_version` |
| `POST` | `/wg/drafts/{draft_id}/send-edited` | 编辑发送 |
| `POST` | `/groups/{session_id}/send-manual` | 人工直发（`trigger=manual`）· **主动发送 WSS** · Bot 身份 · 不经 Agent 起草 |

**List 行片段**：

```json
{
  "session_id": "uuid",
  "chatid": "wrXXX",
  "group_display_name": "数坤坤健管 VIP 群",
  "bot_display_name": "数坤坤健康助手",
  "pending_reply_count": 1,
  "last_message_preview": "@Bot 请问…",
  "last_activity_at": "2026-07-07T08:00:00Z"
}
```

**thread 片段**：与一期 thread 同形（`messages[]` · `pending_draft` · `uplink_pending` · `version`），消息多 `sender_display_name`。

### 14.2 Internal（service token · 仅 ingress GW / 运维）

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| `POST` | `/internal/wecom-group/ingress` | aibot 归一化事件入库 · **含 `response_url` → upsert anchor** |

### 14.3 广播（P4+）

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| `GET` | `/admin/wg/broadcast-tasks?chatid=` | 列表 |
| `PUT` | `/admin/wg/broadcast-tasks/{id}` | 启停/改 cron |

> **P4 不实现** · 生产启用时走 **正式开关** + 本 API 或 YAML。

### 14.4 health 扩展

```json
{
  "ok": true,
  "wecom_group_ingress": true,
  "wecom_group_assistant_gateway": true
}
```

---

## 15. 运维与环境变量

### 15.1 与 kf / OAuth 分离

| 用途 | 配置 |
| ---- | ---- |
| 员工登录 skstudio | skstudio OAuth |
| kf | `CSERVICE_WECOM_*` · callback（一期） |
| **群 Bot ingress** | **`WECOM_BOT_ID` / `WECOM_SECRET`** 写在 **`cservice-assistant` profile `.env`**（与 kf 同一智能机器人 · **非**独立 `WECOM_GROUP_*`） |
| **群助手 GW** | **`HERMES_PROFILE=cservice-group-assistant`** |

**Normative**：群 Bot **复用** kf 客服 Hermes GW（`cservice-assistant`）· **禁止**再部署独立 `cservice-group-ingress` 单元或第二套 Bot 凭证。

### 15.2 环境变量（增量）

**kf + 群 ingress GW**（`hermes-gateway-cservice-assistant.service` · profile `cservice-assistant`）

| 变量 | 说明 |
| ---- | ---- |
| `WECOM_BOT_ID` / `WECOM_SECRET` | 企微智能机器人凭证（kf 与群 **共用**） |
| `WECOM_GROUP_POLICY` | 生产 **`open`** · 试点可 `allowlist` |
| `WECOM_GROUP_ALLOW_FROM` | **仅** `allowlist` 时需要 · 方案 A 生产 **留空** |
| `CSERVICE_URL` | 默认 `http://127.0.0.1:8093` |
| `CSERVICE_SERVICE_TOKEN` | 调 internal ingress |
| `CSERVICE_WG_INGRESS_ENABLED` | `1`（`CSERVICE_WG_ENABLED=1` 时由 install 脚本写入） |

**cservice 进程**

| 变量 | 说明 |
| ---- | ---- |
| `CSERVICE_WG_ENABLED` | `1` 开启群通道 REST |
| `CSERVICE_WG_AUTO_REGISTER` | 生产 **`1`**（方案 A · D-P4-19）· 试点 **`0`** |
| `CSERVICE_WG_BROADCAST_ENABLED` | `0`（**P4 默认关** · **P4+** 生产正式开） |

**group-assistant GW**

| 变量 | 说明 |
| ---- | ---- |
| `HERMES_PROFILE` | `cservice-group-assistant` |
| `CSERVICE_HERMES_WS_URL` | `ws://127.0.0.1:8093/ws/hermes?role=cservice-group` |

> kf GW 与 group GW 以 WSS query **`role=`** 区分（同 cservice 多 role 复用 path）。

### 15.3 部署检查（增量）

**生产（方案 A）**

1. `hermes-gateway-cservice-assistant.service` **active** · profile 含 wecom `cservice_ingress_mode` · `WECOM_GROUP_POLICY=open`
2. `hermes-gateway-cservice-group-assistant.service` **active**
3. `CSERVICE_WG_ENABLED=1` · `CSERVICE_WG_AUTO_REGISTER=1`
4. `GET :8093/.../health` → `wecom_group_ingress` + `wecom_group_assistant_gateway` = true（**`verify_cservice_p4_m4_health.sh`**）
5. 目标群 **已拉 Bot 入群** → 成员 @ → List 自动出现
6. skstudio 子 Tab「客户群」可见（`can_access_tab`）

**试点（白名单，可选）**：`AUTO_REGISTER=0` + seed chatid + `allowlist` — 见 §17。

---

## 17. 生产试点 checklist（CS-33）

### 17.1 自动化前置（normative · 镜像一期 §30.4）

```bash
# skstudio repo · cservice 可达时
CSERVICE_URL=https://your-host:8093 scripts/verify_cservice_p4_m4_health.sh
# 或 cservice repo
deploy/ubuntu/cs-deploy.sh verify-p4-m4
```

| # | 检查 | 命令 / 操作 | 通过 |
| --- | ---- | ----------- | ---- |
| 1 | cservice health + GW 注册 | `verify_cservice_p4_m4_health.sh` | ☐ |
| 2 | kf + 群 ingress GW active | `systemctl is-active hermes-gateway-cservice-assistant` | ☐ |
| 3 | 群 assistant GW active | `systemctl is-active hermes-gateway-cservice-group-assistant` | ☐ |
| 4 | `CSERVICE_WG_AUTO_REGISTER=1` | `/etc/cservice/cservice.env` | ☐ |
| 5–9 | 真群 E2E | §17 步骤 3–7 手工 | ☐ |

**路径 A（与生产一致 · 推荐）**

1. `CSERVICE_WG_AUTO_REGISTER=1` · `WECOM_GROUP_POLICY=open`
2. 启动 **cservice-assistant**（含群 ingress）+ **group-assistant** GW · health 绿
3. 在 **1 个真实客户群** 拉入 Bot · 成员 **@ Bot** 发 text（**无需** 事先填 chatid）
4. ≤30s UI「客户群」List **自动出现**该群 · 角标 =1 · generating → draft
5. 接待 **原样发送** · 群内可见 Bot 回复
6. **编辑发送** · transcript 含 draft_only + user 两条
7. audit · 无 kf 表写入 · outbound 经 cservice `response_url`

**路径 B（首跑白名单 · 可选）**：`AUTO_REGISTER=0` + seed 1 个 chatid + GW `allowlist` — 其余步骤同。

---

## 18. 修订记录

| 版本 | 日期 | 说明 |
| ---- | ---- | ---- |
| v0.3.7 | 2026-07-07 | **架构修正**：群 aibot ingress **复用** `hermes-gateway-cservice-assistant`（同一 Bot 凭证）· 废弃独立 `cservice-group-ingress` 单元 · install/verify/deploy 回改 |
| v0.3.6 | 2026-07-07 | **P4-M4 运维 closure**：`verify_cservice_p4_m4_health.sh` · `verify_cservice_p4_m4.sh` · deploy 双 GW 挂钩 · §17.1 · env 样例 · CS-33 自动化前置 |
| v0.3.5 | 2026-07-07 | **P4-M3 代码 closure**：skstudio BFF `groups/*` · `wg/drafts/*` · `sender_display_name` enrich · 子 Tab UI · Vitest/E2E · `verify_cservice_p4_m3.sh` · CS-35/36 |
| v0.3.4 | 2026-07-07 | **P4-M2 代码 closure**：双 GW registry · `cservice_group_uplink` · migration 006 · REST `/groups/*` · `verify_cservice_p4_m2.sh` · hermes ingress GW · `cservice-group-assistant` profile · CS-30–34/38/39 |
| v0.3.3 | 2026-07-07 | **P4-M1 代码 closure**：cservice migration 005 · internal ingress · WecomAibotClient · health · `verify_cservice_p4_m1.sh` · CS-29/31/40/41 |
| v0.3.2 | 2026-07-07 | **D-P4-19 方案 A**：生产 `AUTO_REGISTER=1` + GW `open` · 无需逐群 chatid · CS-41 |
| v0.3.1 | 2026-07-07 | §7.2 List 群名 · §13 WSS · seed YAML · CS-29–40 · TODO P4 |
| v0.3.0 | 2026-07-07 | **规格冻结**：D-P4-13～18 · Bot **数坤坤健康助手** · 定时 P4+ · §5.6 出站 |
| v0.2.0 | 2026-07-07 | P4-M1 可开工：§5.4 双 GW · migration 005 · §14 · §15 · CS-29–38 |
| v0.1.0 | 2026-07-07 | 初版：D-P4 · P4-M 骨架 |
