# skstudio：Thread 内 Bot — 需求、技术实现与测评验收

本文档合并 **产品需求**、**技术实现要点** 与 **测评验收**，适用于 skstudio 一期 **「每群（thread）一个固定 Bot」** 能力；**不包含** Hermes、skstudio-hermes、适配器协议等（见文末「后续阶段」）。

> **与「数字员工」的边界（2026-08-05）**：本文 **Thread Bot**（`users.is_bot` · IM @ / 下行路由）**不是**权限系统中的 **数字员工授权主体**。后者真源：[数字员工与Actor身份共识.md](./数字员工与Actor身份共识.md)。二者不得混用 ACL `subject_id`。

**关联文档**：

- [`用户需求.md`](用户需求.md)（群 / thread、成员、侧栏）  
- [`技术设计.md`](技术设计.md)（数据模型、API、WS）  
- [`数字员工与Actor身份共识.md`](数字员工与Actor身份共识.md)（人类 / 数字员工 Actor · 代行 vs 履职）  
- [`Hermes与skstudio集成(一期).md`](Hermes与skstudio集成(一期).md)（Hermes / skstudio-hermes；**@ Bot 触发** 见该文档 **§2.6**）

---

## 1. 需求（产品规则）

### 1.1 定义

- **Thread 内 Bot**（以下简称 **Bot**）：每个 **thread（群）** **内置默认**的 **特殊 `users` 行**；用于侧栏、成员列表、消息发送者等处的统一展示。  
  **不是**可登录账号，**不提供**密码登录与 JWT。  
- **thread** 与 **Bot** 分属不同实体：**`threads.id`**（thread 主键）与 **该 Bot 的 `users.id`** **不得相等**  
  （实现须保证，见第 **1.4**、**2.1** 节）。  
- 产品侧 **「群」** 与 **thread** 同义，见 [`用户需求.md`](用户需求.md) 第 5 节说明。

### 1.2 存在性与唯一性

- **每个 thread 有且仅有一个 Bot**（**1:1**）。  
- **创建群（thread）成功时**，必须 **同时** 完成 Bot 绑定（同一事务或等价原子流程）；不得出现「有 thread、无 Bot」的可见状态。

### 1.3 归属范围（仅本群）

- Bot **仅**隶属于该 thread 对应的 **conversation**（与 [`技术设计.md`](技术设计.md) 第 6.3 节「群与会话」一致）。  
- Bot **必须**出现在该群的成员语义中（见第 2 节实现），且 **不得**出现在 **其他** thread / conversation 的成员关系中。  
- 用户在任何 **其他** 群的成员列表、侧栏、消息流中 **不得**看到本群的 Bot。

### 1.4 对外标识与主键（thread ≠ Bot 用户）

- **thread** 的主键为 **`threads.id`**。Bot 作为 **`users` 表一行**，主键为 **`users.id`**。  
  **二者不得相等**：**`users.id`（Bot 行）≠ `threads.id`（所属 thread）**；  
  实现插入后须校验该不变量（若与自增策略冲突，须调整插入顺序、显式分配 id 或等价手段直至满足）。  
- **产品上**用 **`thread_id`**（= 所属 `threads.id`）回答「哪一个 thread 的 Bot」——指 **协作单元**，**不是** Bot 用户行的主键。  
  API / 事件载荷中 **用 `thread_id` + `is_bot` + `user_id`（Bot 的 `users.id`）** 表达即可；  
  **不推荐**再引入与 `thread_id` 同值的 **`bot_id`** 别名以免混淆。  
- **展示名**：Bot 展示名与 **`threads.title`** 一致（见第 1.5 节）；**不**要求 `username` 与群名一致  
  （`username` 仍为系统名，如 `__bot_thread_{id}`）。

#### 1.4.1 与「名字一致」的区分

- **一致**的是 **对外展示名**（侧栏 / 成员列表 / 消息气泡标题）与 **群名**（`threads.title`），**不是**数据库里 `users.username` 与 `threads.title` 逐字相同（后者仍可为机器名）。

### 1.5 展示名（与群名一致）

- Bot 的 **展示名** 与 **`threads.title`**（侧栏与面包屑所用群标题）**始终一致**。  
- **仅群创建者**可改群名（用户需求 F10）；`PATCH` 群 / thread 标题成功后，Bot 展示名 **同步更新**，无需单独「改 Bot 名」入口。

### 1.6 头像（企微机器人风格）

- Bot 头像采用与 **企业微信（企微）机器人默认头像** **视觉一致**的 **静态资源**（前端打包或 CDN URL 二选一定稿）。  
- **版权**：若无法取得企微官方素材授权，则使用 **自研替代图**，在评审中对照企微参考图通过 **视觉验收**；文档与仓库 **注明资源来源与许可**。  
- 一期 **不**做用户可配置 Bot 头像。

### 1.7 本文范围外（见关联文档）

- **Hermes、`skstudio-hermes`、网关插件、Bot 消息经 Hermes 下行落库**：见 [`Hermes与skstudio集成(一期).md`](Hermes与skstudio集成(一期).md)；本文 **不** 定义帧字段与适配器代码结构。  
- **@Bot 触发 Hermes、上下文包窗口**：见完整方案 **§2.6** 与 [`技术设计.md`](技术设计.md) **§5.3**；本文 **1.4** 只约束 Bot **主键与展示名** 及与人类成员并列展示。  
- Bot **单独**被邀请 / 踢出（Bot 生命周期 **从属于** thread / conversation 的创建与删除）。

---

## 2. 技术实现

### 2.1 数据模型（推荐）：`users` 扩展 **Bot 专用列**

- Bot 是 **`users` 表中的特殊行**（与人类账号同一表），便于 **`group_members`**、**`messages.sender_id`** 直接复用现有模型。  
- **`users` 表扩展**（列名可微调，语义如下）：  
  - **`is_bot`**：`BOOLEAN`，**默认 `false`**。  
  - **`bot_thread_id`**：`INTEGER`，**可空**，外键 **`REFERENCES threads(id)`**；**仅当** `is_bot = true` 时 **必须非空**，  
    且在该列上 **全局唯一**（每个 thread 至多一行 Bot 用户）。  
- **不变量**：对该 Bot 行，**`users.id` ≠ `threads.id`**（其中 **`threads.id` = `bot_thread_id`**）。迁移与建群事务中 **必须**校验；测试用例须覆盖。
- **表级约束（逻辑）**：`is_bot = false` ⇒ `bot_thread_id IS NULL`；`is_bot = true` ⇒ `bot_thread_id IS NOT NULL`。  
  SQLite 可用 **CHECK** 或应用层 + 单测兜底。  
- **展示名**：**不冗余**存「Bot 专用昵称列」；**一律**用 **`threads.title`**（与第 1.5 节一致）；API 返回成员时联结 thread 或由调用方已知 `thread_id` 后取标题。  
- **`threads.bot_user_id`**：**不推荐**与 `users.bot_thread_id` 双写；若仅为查询加速保留冗余列，须约定 **单一写源** 与迁移策略。  
- **不可登录**：`is_bot = true` 的行 **禁止** 密码登录；`username` 仍用系统保留前缀（如 `__bot_thread_{thread_id}`）或 UUID，**注册校验**排除 Bot 名冲突。

#### 2.1.1 SQLite 与迁移（实现备忘）

- **唯一性**：对 **`bot_thread_id`** 建 **部分唯一索引**（`WHERE is_bot = 1`），保证每 thread 至多一个 Bot 用户。  
  SQLite 示例：`CREATE UNIQUE INDEX ix_users_bot_thread ON users(bot_thread_id) WHERE is_bot = 1`。  
- **CHECK**：`(is_bot = 0 AND bot_thread_id IS NULL) OR (is_bot = 1 AND bot_thread_id IS NOT NULL)`  
  （以方言与 ORM 迁移脚本为准）。  
- **ON DELETE**：推荐 **`users.bot_thread_id` → `threads(id)`** 带 **`ON DELETE CASCADE`**，删 thread 时顺带删 Bot 用户行；  
  **仍须**与 **`group_members`** 删除顺序一并设计，避免 FK 违反。  
- **`username`**：建议在 **已拿到 `threads.id` 后** 再插入 Bot 行，便于写入 `__bot_thread_{id}` 以利日志与排错。

#### 2.1.2 登录与鉴权

- **密码登录接口**（如 `POST /auth/login`）：若该 `users` 行 **`is_bot = true`**，须 **拒绝颁发 JWT**（返回 **401**；错误文案与「普通登录失败」是否区分由安全策略定稿，避免信息泄露）。

### 2.2 建群路径（与当前后端对齐）

当前 [`backend/app/api/routes_groups.py`](../backend/app/api/routes_groups.py) 在 `POST /groups` 中创建  
`Conversation`、`GroupMember`（owner）、`Thread`。扩展要求（**顺序须满足 FK**）：

1. 保持现有：创建 **Conversation**、**owner** 的 **`group_members`**、**`Thread`**。  
2. 插入 **Bot 的 `users` 行**：`is_bot = true`，**`bot_thread_id` = 刚创建的 `threads.id`**，密码字段无效或占位；**登录拒绝**（见第 **2.1.2** 节）。  
3. 向 **`group_members`** 再插入一行：`conversation_id` 为本群，`user_id` = 该 Bot 的 **`users.id`**，  
   `role` 建议 **`member`**（**非** `owner`）。  

**邀请 / 踢人**：服务端须拒绝将 **`is_bot=true`** 的 **`user_id`** 作为邀请对象、踢出对象等人类成员操作的目标（或在 API 层过滤 Bot）。

### 2.3 改名与删除

- **改名**：`PATCH /threads/{thread_id}` 已同步 `threads.title` 与 `conversations.title`（见现有实现）；  
  Bot 展示名取自 **thread 标题**，**无需**写回 `users`。前端依赖侧栏刷新或现有 **`sidebar_threads_changed`** 类事件。  
- **删群**：删除 `thread` / `conversation` 时，**先**清理 **`group_members`**（含 Bot）、**再**删 **Bot 的 `users` 行**  
  （`is_bot` 且 `bot_thread_id` 指向本 thread）、**再**删 **thread**（或依赖 **`users.bot_thread_id` ON DELETE CASCADE** 等  
  具体 DDL 一次定稿）。  
  须满足 FK 与「删群即销毁协作单元」。

### 2.4 侧栏与成员列表 API

- **`GET /sidebar`** 与成员列表相关响应中，对每个可见 thread 附带 **Bot 摘要**：至少  
  **`thread_id`**（所属 **`threads.id`**，**不是** Bot 的 **`users.id`**）、**`user_id`**（Bot 行的 **`users.id`**）、  
  **`display_name`**（= thread 标题）、**`avatar_url` 或内置资源键**（一期固定）。  
- 人类成员列表与 Bot **合并展示**时，建议字段 **`is_bot`: true**，便于前端渲染企微风格头像与标签  
  （可选「机器人」文案，产品定稿）。

#### 2.4.1 `GET /sidebar` / 成员列表（一期最小字段契约）

- **人类**成员：沿用既有字段（如 **`user_id`**、**`username`**）。  
- **Bot** 行：**`is_bot`: true**；**`thread_id`**（= **`users.bot_thread_id`**，与 **`threads.id`** 一致）；  
  **`user_id`**（= Bot 的 **`users.id`**，**须**满足 **`user_id` ≠ `thread_id`**）；  
  **`display_name`**（= 该 thread 的 **`title`**）；**`avatar_url`** 或 **`avatar_key`**（固定机器人静态资源，见第 1.6 节）。

### 2.5 消息、已读与未读（与 [`技术设计.md`](技术设计.md) 第 6.6、6.7 节对齐）

- 一期 **Bot 不产生**用户可见的「主动发言」；若库中无 Bot 发送的消息，则消息列表仅体现人类。  
- **已读人数分母（已定案）**：**不含** thread 固定 Bot。分母 = 该 **`conversation_id`** 下 **`group_members`** 联结 **`users`** 后  
  **`is_bot = false`** 的成员数，**再减 1（发送者）**（仅当发送者亦为人类成员时；Bot 代发消息若未来启用，发送者判定另见实现）。  
- **已读记录**：**不**为 `is_bot = true` 的用户写入 **`group_message_reads`**（`mark_read` / WS 已读路径对 Bot `user_id` **跳过**）。  
- **未读角标**：**默认**——**Bot 作为发送者的消息**（`sender_id` 指向 Bot 的 `users.id`）**不计入**其他成员的未读计数与侧栏角标聚合  
  （与 [`用户需求.md`](用户需求.md) **U1** 一致）；人类互发规则不变。  
  **例外（方案 B · 2026-08-20）**：`threads.thread_kind = personal` 时 Bot 消息**计入**收件人未读（个人助理收件箱：inform / 偏差通知 / 助手回复等）；标已读取 max **含 Bot**。生产群等 kind 仍不计。已读回执路径仍跳过 Bot。  
  实现锚点：`skstudio/backend/app/services/read_service.py`（`thread_counts_bot_unread`）；迭代见 [`skstudio-PA未读角标-personal例外迭代.md`](./skstudio-PA未读角标-personal例外迭代.md)。
- 与总规 **§6.6**、**§6.7**、**§11.1** `expected_reader_count` 及 **§14** 速查表表述一致；若本文与总规冲突，  
  **以修订日期较新且显式写「已定案」者为准**。

### 2.6 前端

- 在成员列表、消息气泡（若未来有 Bot 消息）、侧栏详情等位置：当 **`is_bot`** 或 **`bot_thread_id` 与当前会话 thread 一致** 时  
  使用 **固定机器人头像组件** 与展示名（来自 **该 thread 的 `title`**）。  
- **暗色模式**：一期可与全局主题一致；头像底图若固定浅色，需在验收中目视确认对比度可接受。

### 2.7 与总技术设计的关系

- [`技术设计.md`](技术设计.md) 已在 **第 6.1、6.2、6.3、6.6、6.7 节** 与 **第 13、14 节** 增补与本文一致的 **摘要**  
  （含主键不等、已读不含 Bot、未读不含 Bot 发言）；实现细节、验收仍以 **本文** 为准，  
  避免两处长篇重复。若后续改列名或约束，**须同步**改总规摘要 + 本文修订记录。

---

## 3. 测评验收

### 3.1 共识检查清单（评审勾选）

| 序号 | 项 | 结论（勾选 / 日期） |
| ---- | -- | ------------------- |
| C1 | **已定案**：API 用 **`thread_id` + `is_bot` + `user_id`** 表达 Bot；**不**再引入 **`bot_id`** 别名 | ✓ |
| C2 | **已定案**：已读分母 **不含** Bot（仅人类 `is_bot=false` 成员；见第 2.5 节与 `技术设计` §6.6） | ✓ |
| C3 | Bot 头像资源路径与版权 / 自研替代说明已归档 | |
| C4 | `group_members` 中 Bot 的 `role` 为 `member`（或其它约定值） | |
| C5 | 邀请 / 踢人 API 与 UI 均不可针对 Bot | |
| C6 | `users`：`is_bot` 默认 false；`bot_thread_id` 唯一且与 `is_bot` 联动约束已落 DDL/迁移 | |
| C7 | 登录接口对 `is_bot=true` 的用户行 **一律拒绝**（见第 2.1.2 节） | |

### 3.2 功能验收用例（手测 / 自动化建议）

| 编号 | 场景 | 预期 | 优先级 |
| ---- | ---- | ---- | ------ |
| T1 | 新用户创建群 | 该群 `group_members` 含 owner + **1 名 Bot**；**`users.id`（Bot）≠ `threads.id`**；侧栏可见；**`thread_id`** 可标识该 Bot | P0 |
| T2 | 同用户创建第二个群 | 两个 thread 各有一个 Bot；**Bot `users.id` 不同**；**`thread_id` 各自不同** | P0 |
| T3 | 受邀用户接受邀请进入群 | 成员列表含创建者、自己、**Bot**；他群无本群 Bot | P0 |
| T4 | 创建者修改群名（PATCH thread） | Bot 展示名与侧栏群名 **一致**，刷新后仍一致 | P0 |
| T5 | 创建者删除群（无 Matter 前提） | Bot 对应 `users` 与成员行 **不可再查**；无孤儿 FK | P0 |
| T6 | 尝试将邀请目标设为 Bot 用户名（若 API 暴露） | **400/403** 或静默过滤，且不生成待处理邀请 | P1 |
| T7 | 尝试踢出 Bot（若 UI 有踢人） | **不可执行**或后端 **403** | P1 |
| T8 | 已读摘要（有人类消息时） | 分母 **不含** Bot；`expected_reader_count` 与 UI 一致；无 NaN、无分母为 0 | P1 |
| T9 | 数据库约束 | 不存在两行 **`is_bot=1` 且 `bot_thread_id` 相同**；人类行 **`is_bot=0` ⇒ `bot_thread_id` IS NULL** | P0 |
| T10 | Bot 为发送者的消息（生产群等非 personal） | 其他成员侧栏 **未读不增加**；与 **U1**、§6.7 默认规则一致 | P1 |
| T10b | personal thread Bot 消息 / inform | 收件人「我的助理」**未读增加**；mark_read 后归零；见 IF-15 | P0 |

**自动化建议**：在 [`backend/tests`](../backend/tests) 中为 `POST /groups` 增加断言：`group_members` 行数、  
存在 **`is_bot` + `bot_thread_id`** 与 thread 一致；删群后该 Bot 的 `users` 行不存在。

### 3.3 文档与交付物验收

| 编号 | 项 | 预期 |
| ---- | -- | ---- |
| D1 | 本文与 `用户需求` / `技术设计` 无矛盾 | 评审签字或纪要链接 |
| D2 | [`技术设计.md`](技术设计.md) **§6.1–6.3、§6.6–6.7、§11.1、§13–14** 已与本文对齐；列名或约束变更须同 PR 更新 | PR 或变更单可指认 |

---

## 4. 后续阶段（不在本文范围）

- Hermes 平台适配器、**skstudio-hermes** WebSocket、服务 token 等：  
  见 [`Hermes与skstudio集成(一期).md`](Hermes与skstudio集成(一期).md) 与 [`技术设计.md`](技术设计.md) 第 **5.3–5.4** 节；**Bot 基线**（本文第 **2–3** 节）宜先验收再扩展联调深度。

---

## 5. 修订记录

| 日期 | 说明 |
| ---- | ---- |
| 2026-08-20 | **§2.5 / T10b**：`thread_kind=personal` Bot 计入未读（方案 B）；链 [PA未读角标迭代](./skstudio-PA未读角标-personal例外迭代.md)。 |
| 2026-05-14 | 关联文档改为 [`Hermes与skstudio集成(一期).md`](Hermes与skstudio集成(一期).md)；**§1.7**/**§4** 与 **@ 触发 Hermes**（完整方案 **§2.6**）交叉引用；**不**再引用已合并的旧文件名。 |
| 2026-05-13 | **定稿合并**：**`users.id` ≠ `threads.id`**；**C1**；**未读不含 Bot 发言**；**内置 / 不登录**；修订记录与总规 **§6.1–6.7、§13–15** 同步（见 [`技术设计.md`](技术设计.md)）。 |
