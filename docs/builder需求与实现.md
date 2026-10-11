# Agent Builder — 需求与实现

- **文档类型**：产品与研发 **规范性** 指导（normative）
- **版本**：**v1.2.8**
- **状态**：共识真源（**取代** [Agent-Builder构建路线图](./Agent-Builder构建路线图.md) 作为 Builder **产品叙事**；路线图保留为历史实施对照，**新功能以本文为准**）
- **适用对象**：skstudio 前端 / 后端、Hermes Agent Lab Plugin、`agent-builder` profile
- **产品环境**：[专业智能体规范 §1.0](./专业智能体规范.md#10-三大产品环境normative) · **开发环境** · Builder Bot

**上位规范**（冲突时服从）：

| 文档 | 职责 |
| --- | --- |
| [专业智能体规范.md](./专业智能体规范.md) | 三环境纪律、B-Def / Done、附录 B 机检 |
| [Agent定义模型.md](./Agent定义模型.md) | 八方面、L1/L2/L3、Aspect ↔ 资产映射 |
| [hermes与skstudio集成(八期).md](./hermes与skstudio集成(八期).md) | Builder 群、`BuilderStudioPanel`、HTTP 路由 |
| [hermes与skstudio集成(九期).md](./hermes与skstudio集成(九期).md) | Lab 测评、`LabEvaluationPanel`、HD-* |

**历史对照**：[Agent-Builder构建路线图.md](./Agent-Builder构建路线图.md)（Playbook P0–P6、W1/W2/W3 波次；**产品面收敛后不再扩展独立 Tab / 用户编辑**）

| 章 | 内容 |
| --- | --- |
| §1 | 产品定位与闭环 |
| §2 | 需求（A/B 右栏、@ Builder、工具、out of scope） |
| §3 | 交互规格（上下文包、scope、门禁） |
| §4 | 技术实现（锚点、API、前端收敛） |
| §5 | 迁移与对照 |
| §6 | 验收 |
| §7 | **实施路线图（PR-1～5）** · 接口约定 · **工程缺省** |
| §8 | 修订记录 |

---

## 1. 产品定位

### 1.1 一句话

> **以 Agent Model（L1）与开发态 Spec 资产（L2）为中心，通过「评价 → 建议 → 共识 → 修改」持续提升定义就绪（readiness），完全 ready 后进入测试环境。**

### 1.2 真源与中心

| 层 | 内容 | Builder 中的角色 |
| --- | --- | --- |
| **L1** | `agent.model.yaml`（可选索引） | **A 总览**摘要展示；无 L1 时由 L2 parse/validate 推导 |
| **L2** | `versions/<ver>/` 下 Markdown/YAML/fixtures/**VERSION**、`.harness/`（证据子集） | **B 资产**只读浏览；**唯一 Spec 写入**经 Builder 工具 |
| **L3** | materialize 后的 profile、`workspace/` | Builder **不**直接编辑；handoff 后由 Lab 消费 |

原则（与 [Agent定义模型 §0](./Agent定义模型.md#0-与现有规范的关系) 一致）：

1. **L2 为合格与否的最终依据**。
2. **L1 是索引，不是第二真源**（BD-0）。
3. **L3 不回写契约**。

### 1.3 核心闭环

```mermaid
flowchart LR
  V[查看 / 选中资产] --> E[@ Builder 评价]
  E --> S[修改建议]
  S --> C{用户共识}
  C -->|接受| W[lab_version_save]
  C -->|继续讨论| E
  W --> R[readiness 刷新]
  R -->|ready| H[部署测试 handoff]
  R -->|未 ready| V
```

| 阶段 | 谁做 | 说明 |
| --- | --- | --- |
| **查看** | 用户（右栏 B） | 只读；选中项定义 @ 评价 scope |
| **评价** | Builder Bot | 整体或局部；机检 + 人话解读 |
| **建议** | Builder Bot | 可含 diff 摘要；**不在右栏落表单** |
| **共识** | 用户 ↔ Builder（群聊） | 用户口头确认后 Builder 才可 save |
| **修改** | Builder（工具） | **唯一**日常 Spec 写入路径 |
| **就绪** | 平台 validate | `phase=spec-ready` **ready=true** |
| **测试** | handoff → Lab | B-Def 门禁；非 Builder 内完成测评 |

**侧栏 IA（v1.2.9 · 方案 A）**：handoff 仍 materialize 到 **per-slug Lab `thread_id`** 并打开该群会话；skstudio 侧栏将各业务 Lab 群 **聚合为一行 `Agent Tester (username)`**，右栏 **Agent 下拉** 切换 slug（`localStorage` 记上次；无 slug 时 Hub 空态；切换 **stop-only** 停旧 gateway）。**不**改变 Hermes `lab-<slug>` gateway 或 `GET …/lab-evaluation` 按 thread 聚合的 API。

### 1.4 范围边界

**Builder（开发环境）负责**：

- Aspect 1～7 的 **共定与写入 Git**（对话共识 + **`lab_version_save`**）
- B-Def / **定义就绪**（`phase=spec-ready`）
- **部署到测试环境**（handoff → Lab materialize）
- 右栏 **总览 + 资产只读**、初始化 / 重置

**Builder 不负责**（归 Lab / 发布）：

- SCENARIOS 对话测评、`.harness/` 写入（[九期 §5.4](./hermes与skstudio集成(九期).md#54-测评工作台labevaluationpanel--完整档--v930)）
- 研发 Done 人检 **HD-1～HD-9**、publish-preflight（[规范 §6.1–6.2](./专业智能体规范.md#61-研发-done人工核对项--hd-1hd-9)）

---

## 2. 需求（产品规则）

### 2.1 右栏结构（normative）

右栏 **仅两块**，对应 [Agent定义模型](./Agent定义模型.md) 的 L1 摘要 + L2 树：

| 区块 | 名称 | 能力 | 模式 |
| --- | --- | --- | --- |
| **A** | **总览** | Agent / @ver 选择、**整体就绪**一行、部署测试、@ 整体评价、初始化/重置、Gateway（折叠） | UI + 只读机检 |
| **B** | **资产** | L2 文件树；选中 → **只读查看**；选中路径作为 @ Builder 的 **评价 scope** | **只读** |

**禁止**在右栏增加第三块「评价面板」、Contract / Trace / Fixtures **独立 Tab**、Playbook 步骤条作为主 UX（见 §2.6）。

**Lab 对称（v9.5.2 · 单 @ver）**：Lab 右栏 **总览 · 测评 · Production Tool · 资产**；**测试 @ver = 预发布 @ver**（pin 后同号）。Builder handoff 前 **`spec-ready` 含 BD-12b**（同 @ver 已含 Lab + Production overlay）；Kanban REG-K01 **宜 handoff 前**写入 SCENARIOS（[规范 §3.4.0](./专业智能体规范.md#340-版本目录资产单文件-vs-双文件-vs-运行时派生normative--v170) · [九期 §5.5.10](./hermes与skstudio集成(九期).md#5510-release_pin-与-kanban-脚手架v952)）。

### 2.2 A — 总览

**必须展示**：

| 字段 | 说明 |
| --- | --- |
| `target_slug` / `version` | 横向一行：Agent 下拉 + 版本下拉 |
| **整体就绪** | 单行 **定义就绪 / 未就绪**（**严格就绪**，见 §2.4 纪律 #5）；**不**展开六维、阻塞列表 |
| Gateway | 折叠：进程 / WSS / 启停 |

**操作**：

| 操作 | 条件 | API / 行为 |
| --- | --- | --- |
| **部署测试** | **严格就绪** | 始终可见；enabled 当且仅当严格就绪；`POST …/handoff-to-lab` |
| **@ Builder 整体评价** | 任意 | `beginBuilderAssess` |
| **初始化 / 重置** | 未发布 → 重置；已发布 → 新建 major | `POST …/profile/init-or-reset` |

**Gateway（①）**：可保留于 A 内折叠区，**不**单独占历史「①②③…」编号区块。

**辅导目标（②）**：并入 A 顶栏（slug + @ver 选择），**不**单独成块。

### 2.3 B — 资产（只读）

**布局（normative · 简单）**：

- **B 右栏**：仅 **文件树**（扁平或一级折叠即可；**不做**复杂 Explorer、分栏预览、Tab 切换）
- **查看**：点击文件 → **弹窗（Modal）** 只读展示内容；关闭弹窗回到树
- **无**右栏内嵌预览区、**无** Monaco/富编辑器、**无** diff 面板

**树内容**（当前 @ver 工作区，与 Git 一致）：

- 必显：`CHARTER.md`、`SCENARIOS.md`、`SOUL.md`、`AGENTS.md`、`VERSION.md`
- 按需：`config/`、`fixtures/`、`.harness/`、`agent.model.yaml`（若存在）
- slug 级 `manifest.yaml`（若在 describe 中可达）

**弹窗内**：

- **只读渲染**（Markdown / YAML / 纯文本；超长可滚动）
- 二进制 fixtures P1：弹窗内仅 metadata + 下载链接
- **无**编辑、**无**保存、**无** apply / fork
- 标题栏显示相对 `path` + @ver

**选中 scope**（供 @ Builder，§3.2）：

- 打开弹窗或树节点高亮时，UI 记录 `selected_path`
- 关闭弹窗 **可保留** 最近选中 path（便于连续 @ 评价同一文件）

**评价入口**（v1.2.1 · 已实现）：

- **A 总览**：「@ Builder 整体评价」— 一键 @ Bot 并发送整体 readiness 评价请求（`selected_path` 清空为整体 scope）
- **B 弹窗**：「@ Builder 评价此文件」— 等价于带 `selected_path` 的 @ 评价
- **行为**：WebSocket 已连接时 **立即发送**；未连接时 **仅预填** 输入框 + 现有「未连接实时通道」提示
- **纪律**：评价 **只发消息**；Git 写入仍仅经用户确认后的 `lab_version_save`（§2.4）

### 2.4 群聊与 @ Builder

**Builder Bot** 是 **共改与评价** 的唯一对话入口（[八期 §5.4.6](./hermes与skstudio集成(八期).md#546-与对话的分工)）。

| 用户意图 | 典型 @ 话术 | Builder 行为 |
| --- | --- | --- |
| 整体评价 | 「整体 readiness 还差什么？」 | assess 全量 → 人话 + 优先修改项 |
| 局部评价 | （选中 CHARTER 后）「评价契约部分」 | assess aspect=3 或 path=CHARTER.md |
| 要建议 | 「CHARTER 的 INTAKE 怎么改？」 | 建议 + diff 摘要；**不写 Git** |
| 定版 | 「按刚才方案保存」 | 用户 **明确确认** 后 `lab_version_save` |

**共识纪律**（normative）：

1. 草稿与讨论 **只在对话**；Git 变更 **仅** `lab_version_save`（总是新 @ver，[八期 §6.10](./hermes与skstudio集成(八期).md#610-v810-保存为新版本)）。
2. Builder **不得**在用户未口头确认时调用 `lab_version_save`。
3. 评价与建议 **默认基于 Git 当前 @ver**（与用户右栏所见一致；**无** UI 未保存草稿）。
4. 切换辅导 **slug** 时 **自动** `@Builder Bot /new` 清 Hermes session，避免上一 agent 的对话记忆影响新 agent 定义（切换 @ver **不**自动清 session）。
5. **严格就绪**（v1.2.4）：侧栏「定义就绪」与「部署到测试环境」、后端 `handoff-to-lab` **同一标准** — `validate.ready` 且无任何 `ok=false`（**含 BD-12b · 同 @ver production overlay**）。**BD-10**：Builder IM 发起 `lab_version_save` 即 `human_confirmed`；已保存版本 describe 将 BD-10 记为已确认，**不**单独挡部署。
6. **定版纪律**（v1.2.4）：用户确认后 **先** `lab_version_save(dry_run=true)`，根据返回 `validate.checks` 修稿，再正式 save；**勿**用 `lab_spec_validate(base_ver)` 预判能否保存。SCENARIOS 落盘格式为 **hr 表格体**（见 profile `gold-standard-format.md`）。
7. **版本语义**（v1.2.5 · v1.2.8 增补）：`VERSION.md` 的 `version:` 字段 = Git **@ver**。保存时 `ensure_impl_bundle` 写入 overlay/lock 注释 `# agent_spec_version: <@ver>`。**BD-16**（warn-only）：Lab profile `VERSION.md` 与 **materialize 时的 editing @ver** 一致（[规范 v1.7.0 单 @ver pin](./专业智能体规范.md#621-skstudio-测评工作台-ui-门禁v1020--normative)）。

### 2.5 Builder 工具（MCP / Plugin）

日常 Spec **唯一写入**：**`lab_version_save`**。只读与评价工具如下（命名可与现网 alias 对齐，语义须一致）：

| 工具 | 用途 | 状态 |
| --- | --- | --- |
| **`lab_versions_describe`** | slug / @ver / checks / coaching 元数据 | ✅ 现网 |
| **`lab_spec_validate`** / **`lab_report_bdef`** | 机检与 B-Def 报告 | ✅ 现网 |
| **`lab_version_save`** | 共识后 fork → 写 `files_json` → validate → commit | ✅ 现网 |
| **`lab_tool_overlay_patch`** | 仅改 tool 勾选/provider（Git @ver · 与侧栏 PATCH 同路径） | ✅ 现网 |
| **`lab_asset_read`** | 读单文件或目录 listing（@ver 工作区） | **待实现 / 可复用 HTTP** |
| **`lab_spec_assess`** | 整体或 aspect/path 评价 + 人话摘要 + 建议方向 | **待实现**（内部 compose validate + parse） |

**禁止** Builder 使用：`write_file` 直写 Git、`cp -r` 旁路、右栏 HTTP apply/fork（410）。

Profile 真源：`hermes-profiles/agent-builder/`（SOUL · AGENTS · BUILDER-ASSESS · `skills/devops/skstudio-agent-lab/`）。

### 2.6 明确不做（out of scope · normative）

以下 **永久排除** 于 Builder 产品面（除非另开 ADR 修订本文）：

| 项 | 说明 |
| --- | --- |
| **用户在右栏编辑 L2 资产** | **不做**；无编辑器、无保存、不放开 410 |
| **右栏 fork / apply / sync-bdef 写 Spec** | 保持 410（[save_policy](./专业智能体规范.md)） |
| **Contract / Trace / Fixtures 独立 Tab** | 并入 B 树 + @ 评价；不另开 Tab |
| **Playbook P0–P6 作为主 UX** | 可内化为 A 阻塞摘要；不展示步骤条为主导航 |
| **save 前 impl 预览独立面板** | 由 Builder 对话说明；不单独右栏模块 |
| **Builder 内跑 SCENARIOS / 写 harness** | 归 Lab（九期） |

---

## 3. 交互规格

### 3.1 @ Builder 上下文包（normative）

用户 @ Builder 时，skstudio / Hermes **应注入**（在 [一期 §2.6](./Hermes与skstudio集成(一期).md) 上下文窗口基础上扩展）；**字段与挂载**见 **§7.4.2–7.4.3**。

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `coach_thread_id` | 是 | Builder 群 |
| `target_slug` | 是 | 辅导目标 |
| `version` | 是 | 当前 @ver |
| `selected_path` | 否 | B 当前选中相对路径；无则表示 **整体** scope |
| `builder_studio_mode` | 是 | 固定 `assess-and-save`（本文产品模式标识） |

**UI 快捷入口**（v1.2.1）：A「@ Builder 整体评价」、B 弹窗「@ Builder 评价此文件」调用 `beginBuilderAssess`；整体评价时 **`selected_path` 显式为 null**（不传 uplink 字段），局部评价时传当前文件 path。

**不注入** UI 草稿（因用户不编辑）。

### 3.2 评价 scope 规则

| 条件 | assess scope |
| --- | --- |
| 未选中 B 中文件 | **整体** readiness + 八方面摘要 |
| 选中 `CHARTER.md` | Aspect 3 Contract + 文件级 checks |
| 选中 `SCENARIOS.md` | Aspect 4 Verification |
| 选中 `fixtures/…` | Aspect 7 Fixtures |
| 选中 `SOUL.md` / `AGENTS.md` | Aspect 5 Behavior |
| 选中 `agent.model.yaml` | BD-0 + L1 摘要 |

机检 id（BD-*）**仅**在 Builder 回复或 A/B 摘要中按需引用；**不**以 check 列表为主界面。

### 3.3 就绪与测试门禁

| 门禁 | 条件 | UI |
| --- | --- | --- |
| **定义就绪** | `validate.ready=true` 且无 `ok=false`（BD-10 由 IM save / describe 归一化） | A 单行就绪；阻塞见 @ Builder |
| **部署测试** | 上项通过 | A「部署测试」enabled |
| **handoff 成功** | materialize Lab @ver | Toast + 打开 **Agent Tester**（对应 slug Lab 群；侧栏见 Hub 入口） |
| **测评 / Done** | Lab REG / harness / HD-* | **Lab 右栏**；非本文范围 |

---

## 4. 技术实现

### 4.1 实现锚点（现网 · 2026-05）

| 层 | 路径 |
| --- | --- |
| 右栏 UI | `frontend/src/pages/chat/BuilderStudioPanel.tsx` |
| 选中态（跨群记忆） | `frontend/src/pages/chat/BuilderStudioSelectionContext.tsx` · 面板 remount 时从 Context 恢复 slug/@ver |
| Agent Tester 右栏 | [九期 §5.4](./hermes与skstudio集成(九期).md#54-测评工作台labevaluationpanel--完整档--v930) · `LabEvaluationOverviewSection.tsx` + `LabEvaluationPanel.tsx` |
| @ 上下文 / handoff | `frontend/src/pages/chat/builderStudioHandoff.ts` · `ChatApp.tsx` |
| Builder API | `backend/app/api/routes_agent_lab.py` · `services/agent_lab/builder_studio.py` |
| 写入门禁 | `services/agent_lab/save_policy.py` · `reject_direct_spec_write` → **410** |
| Hermes 执行 | `hermes-agent/plugins/skstudio-agent-lab/` · `kanban/dashboard/skstudio_agent_lab_api.py` |
| 教练 Profile | `hermes-profiles/agent-builder/` |

**教练群与 Tool Builder（v0.3.0 · 已实现）**：**登录/注册** 时 `provision_agent_studio_for_user` 为 **所有人类用户** 幂等创建 **`Agent Builder ({username})`** 与 per-user **`Tool Builder ({username})` 私坊**（`thread_kind=tool_builder` · **`tool-builder` profile GW** · TB-ISO）；legacy 共享群 title=`Tool Builder` 仅评审员可见，迁移见 **`scripts/migrate_tool_builder_private.py`**。**不** 等待 dev 申请获批。dev 获批创建的是 **业务 Lab 测评群**。存量回填：**`scripts/backfill_agent_studio.py`**。**Tool Builder 真源**：[Tool-Builder v0.3.1](./Tool-Builder产品设计.md)（L2 通过后手动提交发布申请）。

### 4.2 HTTP API（Builder 群）

> **现网 thread_kind（normative · 勿改）**  
> Builder 教练群在实现上为 **`thread_kind=agent_lab`** 且 **`agent_slug=agent-builder`**（[八期 §5.2](./hermes与skstudio集成(八期).md)）。  
> 规范远期分型 `agent_builder_studio`（[路线图 W3-7](./Agent-Builder构建路线图.md)）**不在本迭代改库**；本文 API 路由与 `thread_kind` 判定以现网为准。

**沿用**（[八期 §5.4.5](./hermes与skstudio集成(八期).md)）：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `…/builder-studio` | 摘要（coaching target、gateway） |
| GET | `…/builder-studio/versions/describe` | **A 总览**主数据 |
| GET | `…/builder-studio/profile/init-check` | 初始化前检查 |
| POST | `…/builder-studio/profile/init-or-reset` | 初始化 / 重置 |
| POST | `…/builder-studio/handoff-to-lab` | 部署测试 |
| POST | `…/builder-studio/gateway/{action}` | Gateway 启停（可选） |
| GET/PATCH | `…/builder-studio/.../runtime/tools?platform=skstudio\|cli` | Tool 读 Git @ver / 写 overlay（[一期 §2.8.3](./能力与过程(一期).md#283-tool-独立区块--列表--选择--配置) · v1.8.0 Radio） |
| POST | `…/builder-studio/git/commit?target_slug=` | 提交 `agents/<slug>/` 下全部 Git 脏路径（[一期 §2.8.3](./能力与过程(一期).md#283-tool-独立区块--列表--选择--配置) · v1.6.2） |

**新增（本文）**：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `…/builder-studio/assets` | B 文件树（相对 path、类型、size）；**实现**见 §7.4.4 |
| GET | `…/builder-studio/assets/{path}` | B 只读文件内容；内部可代理 Hermes `GET …/versions/{ver}/file` |

**保留只读、不写 Spec**：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `…/builder-studio/contract` | parse 缓存；**可**供 B 渲染 CHARTER 结构化视图，**非**独立 Tab |

**保持 410（禁止右栏写 Spec）**：

`versions/fork`、`spec/apply`、`spec/sync-bdef`、业务 slug `PUT …/files/…`

**窄域写例外（410 白名单 · normative）** — 右栏 / 测评群可调用，**非** `spec/apply` 全量：

| 方法 | 路径 | 场景 | 规格 |
| --- | --- | --- | --- |
| POST | `…/builder-studio/fixtures` | Builder · 单文件 fixtures | [路线图 B.2.4](./Agent-Builder构建路线图.md) |
| PATCH | Hermes `…/agent-lab/agents/{slug}/tool-overlay` | Builder Lab Tool · 测评群 Production Tool | [能力与过程(一期) §2.4](./能力与过程(一期).md#24-api) · `context=builder \| lab_evaluation` |
| — | Hermes Plugin **`lab_tool_overlay_patch`** | Builder 聊天改 tool（与侧栏 PATCH 同路径 · `context=builder`） | [一期 §2.8.3](./能力与过程(一期).md#283-tool-独立区块--列表--选择--配置) |

**Normative**：白名单外任何右栏写 Git Spec → 仍 **410**；Tool overlay PATCH **不得**写 SOUL/CHARTER/`files_json`。Builder **不做** profile sync-runtime / set-editing-version（v1.6.0 废止）。

### 4.3 前端改造要点（相对现网 ①–⑥）

布局缺省：**上 A 下 B**（§7.4.7）。

| 现网区块 | 收敛为 |
| --- | --- |
| ① Gateway | A 折叠 |
| ② 辅导目标 | A 顶栏 |
| ③ 版本状态 | A 总览字段 |
| ④ 初始化/重置 | A 操作 |
| ⑤ scorecard + Playbook | A 就绪摘要（**去掉** Playbook 步骤条为主 UX） |
| ⑥ handoff | A 操作 |
| （无）Contract Tab | **删除**独立 Tab；内容进 B + @ |
| （新增） | **B 资产树 + 弹窗只读查看**（无内嵌预览） |

### 4.4 Hermes / Plugin

| 任务 | 说明 |
| --- | --- |
| **`lab_asset_read`** | 封装 `GET …/assets/{path}` 或直读 agent-lab-git 工作区 |
| **`lab_spec_assess`** | 输入 `scope=overall\|aspect\|path`；输出 summary、blocking、next_actions、suggested_paths |
| **Profile 更新** | SOUL / BUILDER-ASSESS 对齐本文闭环；强调 **只读右栏 + @ 评价 + save** |
| **`lab_version_save`** | 行为不变；`files_json` 整包替换陷阱见 SKILL.md |

### 4.5 与 Authoring Matrix 的关系

[Agent定义模型 §5](./Agent定义模型.md#5-authoring-matrix--对话--ui--平台) 中 **ui_form / ui_upload / ui_table** 对 Builder 右栏 **不适用**（用户不编辑）。Builder 右栏对应：

| Aspect | Builder UI | 写入 |
| --- | --- | --- |
| 1–7 | B 只读 + @ 对话 | **`lab_version_save`** |
| 8a State | A 总览 | validate 落盘 |
| 8b Evidence | — | Lab |

---

## 5. 迁移与对照

### 5.1 现网能力复用

| 能力 | 本文中的位置 |
| --- | --- |
| `lab_version_save` + ensure_impl_bundle | §2.5 唯一写入 |
| describe + scorecard 聚合 | A 总览 |
| init-or-reset | A 操作 |
| handoff-to-lab + Lab banner | A → Lab |
| contract parse API | B 可选结构化渲染；**非** Tab |
| BD-10 ack | A 阻塞 + @ Builder 确认流程 |
| validate 附录 B 对齐 | assess 内核 |

### 5.2 路线图条目处置

| 原路线图方向 | 处置 |
| --- | --- |
| W2 Contract / Trace / Fixtures **Tab** | **合并** → B + @ |
| W2 impl-preview 面板 | **不做**独立面板 |
| W3 八方面 scorecard | **纳入** A 摘要（可分期） |
| Playbook / 动态 CTA 为主 UX | **降级** → A 阻塞摘要 |
| 用户 UI 编辑 | **不做**（§2.6） |

---

## 6. 验收

### 6.1 产品验收

| # | 场景 | 通过标准 |
| --- | --- | --- |
| B-01 | 打开 Builder 群右栏 | 仅 **A 总览 + B 资产**；无 Playbook 主步骤条、无 Contract Tab |
| B-02 | B 点击 CHARTER | 弹窗只读内容；**无**编辑/保存；关闭回到树 |
| B-03 | @ Builder「评价 CHARTER」 | 回复含契约评价；**未**未经确认 save |
| B-03a | A「@ Builder 整体评价」 | 输入框预填/发送含整体评价话术 + @ Bot；uplink 无 `selected_path`（mock WS 未连时断言预填） |
| B-03b | B 弹窗「@ Builder 评价此文件」 | 弹窗关闭；输入框含 path + @ Bot |
| B-04 | 用户确认后 save | 新 @ver；A refresh；B 树指向新 ver |
| B-05 | ready 前 handoff | 409 + 人话原因 |
| B-06 | ready 后 handoff | Lab materialize；续接提示 |
| B-07 | 右栏 apply/fork | **410** |
| B-08 | 初始化 / 重置 | A 操作可用；符合八期脚手架纪律 |

### 6.2 技术验收

| # | 项 |
| --- | --- |
| T-01 | `GET …/builder-studio/assets` + `…/assets/{path}` 单测 |
| T-02 | `lab_spec_assess` / `lab_asset_read` Plugin 单测或集成测 |
| T-03 | @ 上下文含 `selected_path` E2E（mock） |
| T-04 | 既有 `test_builder_studio_init_reset` · handoff · describe **仍绿** |

---

## 7. 实施路线图（PR 切分 · normative）

本文 **取代** [Agent-Builder构建路线图](./Agent-Builder构建路线图.md) 的 **新产品迭代**；历史 W1/M3a 代码（Playbook 主 UX、Contract Tab 等）在收敛 PR 中 **删除或合并**，见 §7.2。

### 7.1 PR 列表与依赖

```text
PR-1  Backend · assets API          ──┐
                                      ├──→ PR-2  Frontend · B 资产树 + 弹窗
PR-5  Hermes · assess 工具 + Profile  │         PR-3  Frontend · A 总览收敛
         （可与 PR-1 并行）            │              PR-4  @ 上下文注入
                                      └────────（PR-3/4 可同仓分批，视 diff 大小）
```

| PR | 标题 | 范围 | 依赖 | 验收 |
| --- | --- | --- | --- | --- |
| **PR-1** | Backend · assets API | `GET …/builder-studio/assets`、`GET …/assets/{path}`；优先复用 `agent_lab_http.get_bundle` + `read_version_file`（§7.4.4） | — | T-01 |
| **PR-2** | Frontend · B 资产 | 右栏文件树；点击 → **弹窗**只读（§2.3）；`selected_path` 状态 | PR-1 | B-02 |
| **PR-3** | Frontend · A 收敛 | ①–⑥ 合并为 **A 总览**；去掉 Playbook 主条、Contract Tab、复杂 CTA | —（与 PR-2 同文件时可合并提交） | B-01、B-05～B-08 |
| **PR-4** | @ 上下文注入 | `BotMentionPackageUplink.builder_studio` + 前端选中态上行（§7.4.2–7.4.3） | PR-2（需选中态） | T-03、B-03 |
| **PR-5** | Hermes · assess 工具 | `lab_asset_read`、`lab_spec_assess`（**机读聚合**，§7.4.5）；Profile 对齐 §2.4 | —（可与 PR-1 并行） | T-02、B-03、B-04 |

**整轮完成**：§6.1 B-01～B-08 + §6.2 T-01～T-04 全绿。

**建议落地顺序**：PR-1 → PR-2 → PR-3 → PR-4；PR-5 与 PR-1 并行启动。

**不在本路线图内**：`gateway restart: timed out`（handoff 基础设施）— 单独 bug PR。

### 7.2 现网收敛（实施时注意）

| 现网（W1 / M3a 未收敛部分） | 处置 |
| --- | --- |
| Playbook P0–P6 步骤条 | **删除**主 UX；阻塞信息收入 A 摘要 |
| Scorecard / Contract **双 Tab** | **删除** Contract Tab；scorecard 收成 A 就绪摘要 |
| 动态 CTA / scroll_to_contract | **删除**或收成 A 内 handoff / 重新检查 |
| `GET …/contract` API | **保留**（可选供弹窗或 Builder parse）；**无**独立 Tab |
| handoff banner / toast | **保留**（§2.2 部署测试） |

### 7.3 接口约定（实现缺省 · normative）

#### `GET …/builder-studio/assets`

Query：`slug`（可选，默认 coaching target）、`version`（可选，默认工作 @ver）。

Response：

```json
{
  "slug": "hr-policy",
  "version": "v0.2.0",
  "entries": [
    { "path": "CHARTER.md", "kind": "file", "size": 4096 },
    { "path": "fixtures", "kind": "dir" }
  ]
}
```

#### `GET …/builder-studio/assets/{path}`

`path` 为相对 `versions/<ver>/` 的路径（URL 编码）。Response：

```json
{
  "slug": "hr-policy",
  "version": "v0.2.0",
  "path": "CHARTER.md",
  "content": "# …",
  "content_type": "text/markdown",
  "binary": false
}
```

二进制文件 P1：`binary: true`，`content` 省略，可选 `download_url` 或 `size` only。

#### @ 上行 `builder_studio`（PR-4 · 字段名固定）

附加于 **`BotMentionPackageUplink`**（`backend/app/hermes/schemas_ws.py`），与 Lab 的 `evaluation_panel` **并列**；挂载与注入见 **§7.4.2–7.4.3**。

```json
{
  "coach_thread_id": 42,
  "target_slug": "hr-policy",
  "version": "v0.2.0",
  "selected_path": "CHARTER.md",
  "builder_studio_mode": "assess-and-save"
}
```

`selected_path` 省略或 `null` 表示 **整体** scope（§3.2）。

#### `lab_spec_assess`（PR-5 · Plugin）

**职责**：**机读聚合**（§7.4.5）；**不**调用 LLM。人话解读由 Builder Bot 根据出参生成。

**入参**：`slug`, `version`, `scope`（`overall` | `aspect` | `path`）, `aspect?`（1–8）, `path?`

**出参**：

```json
{
  "scope": "path",
  "path": "CHARTER.md",
  "aspect": 3,
  "ready": false,
  "summary": "3 blocking · Contract INTAKE incomplete",
  "blocking": [{ "message": "…", "check_id": "BD-3" }],
  "next_actions": ["补充 INTAKE 表 …"],
  "related_paths": ["CHARTER.md", "fixtures/intake.json"]
}
```

`summary` 为 **结构化短句**（非 LLM）；`check_id` 供 Builder 回复引用；**右栏 A 默认不暴露** id 列表（§2.2）。

---

### 7.4 工程缺省（normative · 可直接编码）

下列约定补齐 §7.3 与 PR 描述之间的空隙；**冲突时服从 §2 产品规则**。

#### 7.4.1 A 阻塞摘要算法（PR-3）

输入：`GET …/versions/describe` → `validate.checks[]`、`dimensions[]`、`ready`。

输出：`blocking_summary: string[]`（**最多 3 条**），规则：

1. 若 `ready === true`：单条 `"定义就绪（B-Def 已通过）"`（**含** BD-10 `human_required` pending，v1.2.4 不单独挡）。
2. 否则从 `checks` 取 **`ok === false`** 的项。
3. 排序：`severity` 降序（若有）→ check `id` 字典序。
4. 每条文案：优先 `check.message`；空则用 `check.title`；仍空则用 `"<dimension 标签> 未通过"`。
5. **截断为 3 条**；余下失败项 **不**在 A 展开（用户 @ Builder 或 assess 看全量）。

**不在 A 展示**：check id 列表、Playbook 步骤条、Contract 表格。

**实现位置**：优先 **前端** 从现有 describe 聚合；**不强制** 改 describe API。

#### 7.4.2 `builder_studio` 上行挂载（PR-4）

| 层 | 约定 |
| --- | --- |
| **Schema** | `BotMentionPackageUplink` 增 **`builder_studio: dict \| null`**（Pydantic 字段名固定） |
| **何时填充** | Builder 教练群（`thread_kind=agent_lab` 且 `agent_slug=agent-builder`）且用户 **@ Builder Bot** |
| **谁组装** | `backend/app/hermes/bridge.py` 在构造 `BotMentionPackageUplink` 时填入 |
| **数据来源** | 请求级 meta（见 §7.4.3），**非** DB 持久化 |
| **Hermes 消费** | Profile：`builder_studio` present → 优先 `lab_spec_assess`（scope 见 §7.4.6）再回复；**无**则按通用 Builder 流程 |

`builder_studio` 对象字段（与 §7.3 JSON 一致）：

| 字段 | 必填 |
| --- | --- |
| `coach_thread_id` | 是 |
| `target_slug` | 是 |
| `version` | 是 |
| `builder_studio_mode` | 是，固定 `"assess-and-save"` |
| `selected_path` | 否 |

#### 7.4.3 `selected_path` 前端 → bridge（PR-2 + PR-4）

| 步骤 | 约定 |
| --- | --- |
| 1 | 前端 **`BuilderStudioSelectionContext`**：`{ targetSlug, version, selectedPath, coachThreadId }`；**切换 sidebar 群后再回 Builder 教练群时恢复** slug/@ver（v1.2.7） |
| 2 | **B** 树点击 / 弹窗打开：更新 `selectedPath`；关闭弹窗 **可保留** path（§2.3） |
| 3 | **A** 切换 slug：清空 `selectedPath`；**自动** `@Builder Bot /new` 清 Hermes session（避免上一 agent 对话记忆影响新 slug）；切换 @ver **不**自动 `/new` |
| 4 | 用户发消息且 **@ Builder** 时：`POST …/messages`（或 WS 发消息路径）携带可选 **`builder_studio_context`**，结构与 §7.4.2 相同 |
| 5 | `message_service` / `bridge`：落库 **不必**存 `builder_studio_context`；在触发 uplink 前写入 **ContextVar**（仿 Lab `set_evaluation_uplink_meta`） |
| 6 | uplink 发送后 **reset** ContextVar，避免泄漏到下一条消息 |
| 7 | **快捷按钮**（v1.2.1）：`beginBuilderAssess({ scope: "overall" \| "path", path? })` → 设置 `selectedPath`、@ Bot、预填模板话术；`wsLive` 时 `sendChatWith` 立即发送并携带 `builder_studio_context` |

**E2E**：mock 断言 uplink JSON 含 `builder_studio.selected_path`（T-03）。

#### 7.4.4 assets 列表与树构建（PR-1 + PR-2）

**Backend（PR-1）**：

1. 调 Hermes **`GET /agent-lab/agents/{slug}/versions/{ver}/bundle`**（skstudio 已有 `agent_lab_http.get_bundle`）。
2. 对 `files[]`（相对路径 flat list）生成 `entries[]`（§7.3）；`size` P1 可省略。
3. **必显文件**（§2.3）：若 Git 中不存在，仍返回 `entries` 项且可选 `"missing": true`（前端灰显）。
4. **`GET …/assets/{path}`**：代理 `read_version_file`；文本返回 `content` + `content_type`；**二进制** v1 返回 `binary: true`、HTTP 200、**无** `content`（弹窗提示「不支持预览」）。

**Frontend 树（PR-2）**：

1. 将 flat `entries` 按 **第一段** `/` 分组：`config/foo.md` → 目录 `config/` + 文件；**不**递归多级 Explorer。
2. 根目录文件直接列出；目录节点 **仅展开一层**（§2.3）。
3. 排序：必显五文件置顶（CHARTER → SCENARIOS → SOUL → AGENTS → VERSION），其余字母序。

#### 7.4.5 `lab_spec_assess` 职责边界（PR-5）

| 做 | 不做 |
| --- | --- |
| 调 `lab_spec_validate`（`phase=spec-ready`） | 调用 LLM |
| 按 scope **过滤** checks（§7.4.6） | 写 Git |
| 可选调 `spec/parse`（charter/scenarios）补结构化摘要 | 替代 Builder 对话 |
| 输出 `blocking` / `next_actions` / `related_paths` | 生成长文 diff |

**`next_actions`**：来自失败 check 的 `next_action` / `hint` 字段；无则空数组。

**Builder Bot**：读到 assess JSON 后 **组织人话**（BUILDER-ASSESS 格式）；用户确认后再 `lab_version_save`。

#### 7.4.6 path / aspect → assess scope

| 触发条件 | `scope` | 参数 | 过滤 checks |
| --- | --- | --- | --- |
| 无 `selected_path` | `overall` | — | 全部失败项 |
| `CHARTER.md` | `path` | `path=CHARTER.md` | BD-3、BD-4、BD-5 + charter parse 消息 |
| `SCENARIOS.md` | `path` | `path=SCENARIOS.md` | BD-5～BD-8 相关 |
| `SOUL.md` / `AGENTS.md` | `path` | 对应 path | BD-9～BD-15 / dimension soul·agents |
| `fixtures/…` | `path` | path 前缀 | BD-7b 等 |
| `agent.model.yaml` | `path` | — | BD-0 |
| `VERSION.md` | `path` | — | BD-1、版本相关 |
| `config/…` | `aspect` | `aspect=6` | Platform / config 桶 |

显式 @「评价 aspect N」时：`scope=aspect`，`aspect=N`（与 §3.2 一致）。

#### 7.4.7 UI 与 v1 渲染缺省

| 项 | v1 缺省 |
| --- | --- |
| 右栏布局 | **上 A 下 B** 纵向；Gateway 在 A 内 `<details>` 折叠 |
| 弹窗内容 | **`<pre>` 纯文本** + 滚动；Markdown 渲染 **P1** |
| describe API | **不改**；A 阻塞摘要前端聚合（§7.4.1） |
| E2E mock | 扩展 `stubBuilderStudioRoutes`：`/assets`、`/assets/{path}` fixture |
| Profile 安装 | PR-5 合并后跑 `install_agent_builder_profile.py` + Gateway restart |

---

## 8. 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1.0.0 | 2026-05-31 | 初版：A/B 右栏、@ 评价闭环、用户编辑 **不做**、取代路线图产品叙事 |
| v1.0.1 | 2026-05-31 | §2.3：资产查看 **弹窗**；B 仅树，不做复杂 Explorer |
| v1.1.0 | 2026-05-31 | **§7** 实施路线图 PR-1～5、现网收敛表、接口 JSON 约定 |
| v1.2.0 | 2026-05-31 | **§7.4** 工程缺省：阻塞摘要、builder_studio 上行、selected_path、assets 树、assess 边界、thread_kind 脚注 |
| v1.2.1 | 2026-05-31 | §2.3/§3.1：A/B @ Builder 评价快捷入口；§6.1 B-03a/b；§7.4.3 `beginBuilderAssess` |
| v1.2.2 | 2026-05-31 | §2.4/§7.4.3：切换辅导 slug 自动 `@Builder /new` 清 session |
| v1.2.3 | 2026-05-31 | §2.2 A 总览 UI 收敛；严格就绪 + handoff 对齐；移除侧栏 BD-10 / 六维 / 重新检查 |
| v1.2.4 | 2026-06-01 | 定版共识：hr SCENARIOS 真源、save 先 dry_run、`lab_version_save` 失败返回完整 validate、BD-10=IM 保存即人确、profile/skill 对齐 |
| v1.2.5 | 2026-06-01 | 双轨 version 语义、`agent_spec_version` 注释、save 忽略 overlay/lock 透传、`pinned_commit` 与 spec commit 对齐、BD-16 materialize 告警 |
| v1.2.6 | 2026-06-01 | 文档对齐：[专业智能体规范 v1.5.5](./专业智能体规范.md) 附录 B **BD-16**；BUILDER-ASSESS / bdef-checklist / 八期 §6.10；安装脚本同步 skills 树 |
| v1.2.8 | 2026-06-04 | **单 @ver 策略 A**：§2.1 Lab 对称 · handoff 含 BD-12b · 链 [规范 v1.7.0 §3.4.0](./专业智能体规范.md#340-版本目录资产单文件-vs-双文件-vs-运行时派生normative--v170) |
| v1.2.7 | 2026-06-01 | **BuilderStudioSelectionContext** 跨群恢复 slug/@ver；链 [九期 v9.4.1](./hermes与skstudio集成(九期).md) Lab 总览 UI 收敛 |
