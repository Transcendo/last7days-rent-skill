# 北京京东总部租房 POC 设计方案

日期：2026-06-13

状态：POC 方案草案

## 目标

本 POC 只做一条清晰闭环：

> 用户在 Codex / Claude Code / OpenClaw / Hermes Agent 等 Agent runtime 中，通过问答式 profile wizard 明确租房偏好；Agent runtime 使用自带 web search / browser 能力完成公开渠道房源发现；工具将结果整理为本地可更新、可筛选、模板化 HTML 房源列表。

首个 POC 的启动输入示例：

```text
北京京东总部，一居室，5000 RMB 以内。
```

这不是让用户一次性写完整 profile，也不是让用户填写长段表单。它只是一个 `goal seed`，用于让 Agent runtime 启动 profile wizard，并从中预填一部分字段：

| goal seed 片段 | 预填字段 | 后续确认方式 |
| --- | --- | --- |
| 北京京东总部 | `office_anchor` | 选择题确认办公锚点和通勤圈 |
| 一居室 | `housing_constraints.min_bedrooms` | 选择题确认是否接受开间/loft/合租 |
| 5000 RMB 以内 | `housing_constraints.budget_max` | 选择题确认预算策略 |

真正的 profile 仍然通过 6 道以内的问答题逐项确认；用户只需要选择或确认，不需要手写结构化参数。

这个 POC 的重点不是“工具自己联网搜索”，而是验证：

- 用户 profile 能否通过原生问答体验高质量收集。
- Agent runtime 能否负责全渠道公开房源发现。
- 工具能否把零散 evidence 变成本地 HTML 房源工作台。

## 非目标

POC 阶段明确不做：

- 不保留 Brave / Exa / Tavily / DDGS 等 provider-first 搜索路径。
- 不要求用户配置任何搜索 provider API key。
- 不内置面向贝壳、58、安居客、豆瓣等站点的批量自动抓取器。
- 不内置验证码对抗、账号登录自动化、cookie 复用或登录态保存。
- 不处理签约、付款、法律审查、线下看房排程自动化。
- 不把搜索片段写成已验真房源。
- 不保存或公开原发帖人真实身份。

这里的边界不是因为 MIT 开源协议不允许，也不是说“公开网页永远不能被读取”。MIT 只授权本项目代码的复制、修改和分发，不能替第三方平台授权其页面内容、接口、账号体系、反爬机制或用户个人信息的使用。

POC 允许做的是：

- Agent runtime 通过 web search 找到公开结果页、公开详情页和公开帖子。
- Agent runtime 打开页面并读取用户当前可见的信息。
- 用户主动提供链接、截图、复制文本或浏览器可见内容时，工具将其转成 evidence。
- 工具只保存房源摘要、来源链接、抓取时间、置信度、风险标记和联系路径，不保存 cookie、登录态或平台内部接口响应。

POC 暂不内置的是：

- 面向具体平台的长期批量 crawler。
- 绕过访问控制、验证码、风控、签名接口或反自动化机制。
- 要求用户交出账号、cookie、token 或长期登录态。
- 大规模复制、镜像、转载第三方平台内容。

如果后续要做无人值守 monitor、纯 CLI 场景或平台级数据接入，可以单独设计 `connector` / `crawler adapter` 插件。该插件需要独立约束：遵守目标站点规则、限制频率、保留来源、避免登录墙和验证码对抗、最小化个人信息，并让用户明确知道当前运行的采集方式。

## 总体架构

```text
用户自然语言目标
  -> Agent-native profile wizard
  -> 本地 RentProfile draft
  -> 北京京东总部 Anchor Pack
  -> Search Brief
  -> Agent runtime web search / browser
  -> Agent Search Evidence
  -> Ingest + 去重 + 打分 + 风险标记
  -> Local Listing Pool JSON
  -> HTML Report / HTML 工作台
```

三层职责：

| 层 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| Agent runtime | 问答交互、web search、打开网页、判断可见信息 | 不持久化业务状态 |
| last7days-rent tool | profile 状态机、evidence schema、去重、排序、HTML 生成 | 不自建搜索引擎 |
| 用户 | 选择偏好、确认联系状态、线下看房反馈 | 不需要手写复杂参数 |

## 0. 现有代码清理功能

POC 需要先单列一个 `cleanup` 功能，用来把当前代码从 provider-first 方向清理回 agent-native 主线。这个功能不是面向租房用户的产品能力，而是面向本 repo 的迁移能力：先删掉或隔离错误方向，避免后续 profile wizard、runtime evidence、HTML render 继续挂在脏架构上。

清理目标：

- 默认路径不再依赖 Brave / Exa / Tavily / DDGS。
- 默认路径不再暴露 `--provider-search` / `--provider-extract`。
- 默认报告不再输出 Markdown 作为人类最终产物。
- 默认 live flow 不再由 `run_acquisition()` 自行联网找房源。
- 保留可复用的 schema、隐私、去重、评分、HTML/JSON 产物能力。
- 删除已经失效、未追踪或只会制造误解的生成物和历史文档。

### 当前代码需要清理的面

| 当前内容 | 现状问题 | POC 处理 |
| --- | --- | --- |
| `skills/last7days-rent/scripts/lib/providers/` | 自建 Brave/Exa/Tavily/DDGS provider 层，偏离 agent-native 主线 | 删除；如确需保留历史参考，移到 `_legacy/providers/` 且不进默认 import |
| `skills/last7days-rent/scripts/lib/acquisition/service.py` | live 主路径仍解析 provider config 并自行搜索 | 删除 provider 执行逻辑；保留可复用的 URL 分类、候选归一化能力到 `agent_evidence.py` |
| `--provider-search` / `--provider-extract` | CLI 默认路径仍暗示用户要配置 API key | 从默认 CLI 删除；不作为 POC 参数 |
| `docs/provider-architecture.md` | 继续传播 provider-first 架构 | 删除或改名为 `docs/legacy-provider-architecture.md`，并明确不属于 POC |
| `README.md` / `SKILL.md` provider 描述 | 触发路径和用户心智都还是 provider-first | 改为 runtime-first：profile wizard -> plan -> runtime search -> ingest -> render |
| `pyproject.toml` 中 `ddgs` dependency / `provider` keyword | POC 不再需要 provider fallback 依赖 | 删除 `ddgs` 依赖和 provider keyword |
| `tests/test_provider_acquisition.py` | 测试锁死 provider 架构 | 删除或拆成 `tests/legacy/`；新增 `test_agent_evidence.py` |
| `tests/test_cli.py::test_fixture_search_accepts_provider_flags` | 验证 provider flags 可用，与 POC 目标相反 | 删除，改测 `plan/ingest/render` |
| `render.py` / `pipeline.py` Markdown 输出 | 当前 `SearchResult`、`report --latest` 仍围绕 `.md` | 改成人类产物 HTML + 机器 evidence JSON |
| `sources smoke` live 命令 | 容易被误解成内置抓站能力 | 从默认 README/SKILL 移除；如保留，仅作为开发诊断，不作为用户路径 |
| `profile init/refine` 参数式入口 | 不符合已确认的选择题交互 | 降级为底层/legacy；默认入口改成 `profile wizard` |
| `__pycache__` / `.pyc` / stale `search_providers` cache | 生成物残留，污染 repo 认知 | 删除本地生成物；确认 `.gitignore` 已覆盖 |

### 保留和复用的面

不是所有旧代码都要删。以下能力仍有价值：

- `schema.py`：保留核心 dataclass，但要去掉 provider-only 字段或迁移到 legacy。
- `privacy.py` / `secret_guard.py` / `contact.py`：保留，继续负责隐私和 contact path 边界。
- `normalize.py` / `dedupe.py` / `scoring.py` / `rerank.py`：保留，但输入从 provider result 改成 agent evidence / listing pool。
- `feedback.py`：保留，用于后续 HTML 状态和用户反馈。
- `sources/*` 中的纯解析能力：可保留为“用户提供页面文本/公开可见内容”的解析器；不要作为默认自动抓取器。
- `tests/fixtures/*`：保留必要 fixture，但北京京东总部 POC 应新增自己的 profile/evidence fixture。

### 清理后的默认命令面

清理完成后，默认 CLI 应收敛为：

```bash
profile wizard start/next/answer/inspect/commit
plan
ingest
render
feedback
report --latest
```

默认不再出现：

```bash
search --provider-search ...
search --provider-extract ...
sources smoke ...
```

`search` 如果保留，只能作为兼容 alias，内部应提示用户改用 `plan -> runtime search -> ingest -> render`，不能再自行执行 provider 搜索。

### 清理验收标准

清理功能完成后必须满足：

1. `rg "BRAVE_SEARCH_API_KEY|EXA_API_KEY|TAVILY_API_KEY|ddgs|--provider-search|--provider-extract"` 不应在默认 README、SKILL、CLI help、POC 主路径测试中出现。
2. `pyproject.toml` 不再依赖 `ddgs`。
3. `python skills/last7days-rent/scripts/last7days_rent.py --help` 展示 runtime-first 命令。
4. `report --latest` 默认返回 `.html`。
5. Provider 相关测试不再属于默认 test suite。
6. 旧的 provider 文档不存在，或明确标记为 legacy 且不从 README 主路径链接。
7. 本地生成物、`__pycache__`、stale `search_providers` cache 不进入工作树。

## 1. Profile 设计与问答流程

### 设计原则

Profile 获取不能再以 CLI 参数为主：

```bash
profile init --office-anchor ... --budget-max ...
```

这种形式适合测试，不适合真实用户。真实使用应是 Agent runtime 原生问答：

- 一次只问 1-3 个问题。
- 每题都是决策题，优先提供 2-4 个选项。
- 默认选项排第一，并在 label 中标注推荐。
- 允许用户选择 `Other` 或补充自由文本。
- 每个问题都写入结构化 profile 字段。
- 支持中断后继续。

### 用户可见交互规则

本 POC 采用“低暴露、选择题式”的 profile 交互。用户认可的体验是：用户只做选择和纠偏，Agent 负责把答案收敛成结构化 profile。真实运行时默认不向用户连续展示 JSON、schema、search brief 或内部字段。

默认用户可见内容：

- 当前正在确认什么。
- 为什么这个问题会影响后续搜索。
- 2-4 个选项，推荐项排第一。
- 用户回答后的简短确认。
- 必要时提示“已记录，会影响某某搜索范围”。

默认隐藏内容：

- profile JSON 草稿。
- `writes_to` 字段映射。
- anchor pack 展开细节。
- search brief JSON。
- evidence schema。
- 评分、去重、风险规则的完整内部实现。

用户可以显式要求查看这些内容。触发方式可以是自然语言，也可以是命令：

```text
查看当前 profile
展示 JSON
查看 search brief
为什么这么搜
```

对应 CLI 能力：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard inspect
python skills/last7days-rent/scripts/last7days_rent.py profile wizard inspect --format json
python skills/last7days-rent/scripts/last7days_rent.py plan --explain
```

交互样式示例：

```text
用户：北京京东总部，一居室，5000 RMB 以内

Agent：我先确认办公锚点。你说的“北京京东总部”，我理解为亦庄经海路附近的京东总部办公区。请选择：
A. 京东总部 / 亦庄经海路（推荐）
B. 京东亦庄其他办公点
C. 我不确定

用户：A

Agent：已确认办公锚点。下一题确认户型：你要一居室、二居室，还是独立整租即可？
```

注意：上面的 Agent 回复不展示 profile JSON。只有用户明确要求“展示 JSON / 查看当前 profile”时，Agent 才展开结构化内容。

### Runtime 能力模型

POC 不做“当前运行在 Codex 还是 Claude Code”的强判断，也不把某个平台写进核心业务逻辑。原因是本项目的目标是通用于多个 Agent runtime：Codex、Claude Code、OpenClaw、Hermes Agent，以及后续可能出现的新 runtime。

核心原则：

- 不检测平台品牌。
- 不依赖平台私有环境变量作为主路径。
- 不在 tool 内直接调用 Codex / Claude / OpenClaw / Hermes 的专有 API。
- 只声明本步骤需要哪些 runtime capability。
- 能力存在时使用原生体验；能力不存在时降级到通用文本协议。

POC 需要的 runtime capability：

| Capability | 用途 | 首选形态 | 降级形态 |
| --- | --- | --- | --- |
| `interactive_choice` | profile wizard 问答 | 原生选择 UI / 多选 UI | Markdown 单题选择 |
| `web_search` | 公开渠道发现 | runtime 自带 web search | 用户手工提供链接 |
| `browser_open` | 打开详情页核验 | runtime browser / Playwright / app browser | 用户复制页面文本或截图 |
| `local_file_write` | 写 profile、evidence、HTML | runtime 文件工具 | 用户指定输出路径后写入 |
| `structured_output` | 传递 evidence JSON | tool call / JSON block | Markdown fenced JSON |

因此，skill 的核心实现只需要输出和消费标准协议：

- `wizard next` 输出问题 JSON。
- Agent runtime 自行决定如何展示这个问题。
- `wizard answer` 接收用户答案。
- `plan` 输出 search brief。
- Agent runtime 自行决定如何搜索和浏览。
- `ingest` 接收 Agent 整理后的 evidence JSON。
- `render` 输出 HTML。

### Runtime Adapter 参考

不同 Agent runtime 只需要实现很薄的一层 adapter；没有 adapter 时也可以靠通用 Markdown 协议运行。

| Runtime | `interactive_choice` 参考实现 | `web_search` 参考实现 | 备注 |
| --- | --- | --- | --- |
| Codex | `request_user_input` 或聊天单题选择 | Codex web search / browser | 不要求 skill 检测 Codex，只由 Agent 自行选择工具 |
| Claude Code | `AskUserQuestion` 或聊天单题选择 | Claude Code 可用 web / browser 工具 | 不把 Claude schema 写进核心 CLI |
| OpenClaw | runtime 自带选择/确认工具；没有则 Markdown | OpenClaw web/search/browser 能力 | 只要能产出 evidence JSON 即可 |
| Hermes Agent | tool gateway / chat choice / Markdown | Hermes web search gateway | 只要能执行 search brief 即可 |
| Unknown runtime | Markdown 单题选择 | 用户提供链接、截图、复制文本 | 最低可用路径 |

如果确实需要记录运行环境，只作为 debug metadata：

```json
{
  "runtime_meta": {
    "runtime_name": "unknown",
    "capabilities": ["interactive_choice", "web_search", "browser_open"],
    "declared_by": "agent",
    "detected_by_tool": false
  }
}
```

这里的 `runtime_name` 不能影响业务分支；业务分支只能看 capability 是否可用。

### Runtime Adapter Contract

这里计划补的不是更多平台判断，而是一份稳定的 adapter contract。任何 runtime 只要满足 contract，就可以使用本 skill；不满足时走 Markdown 兜底。

Adapter contract 分为 5 个面：

| Contract | 目的 | 必需性 |
| --- | --- | --- |
| Capability Declaration | 由 Agent 声明当前 runtime 能做什么 | 必需 |
| Question Presentation | 把 wizard question 展示给用户 | 必需 |
| Search Brief Execution | 执行 `plan` 产出的 search brief | 有 web/search 时必需 |
| Evidence Handoff | 把搜索结果整理为 evidence JSON | 必需 |
| Fallback + Error Protocol | 能力缺失或格式错误时给出可修复提示 | 必需 |

#### 1. Capability Declaration

Adapter 不需要检测“当前是不是 Codex / Claude”。它只声明能力：

```json
{
  "runtime_meta": {
    "runtime_name": "codex",
    "adapter_version": "0.1.0",
    "capabilities": {
      "interactive_choice": true,
      "web_search": true,
      "browser_open": true,
      "local_file_write": true,
      "structured_output": true
    }
  }
}
```

如果 runtime 不想暴露名称，`runtime_name` 可以是 `unknown`。业务逻辑只看 capability。

#### 2. Question Presentation

`profile wizard next` 输出统一问题 JSON：

```json
{
  "question_id": "budget_strategy",
  "title": "确认预算策略",
  "body": "你更希望严格 5000 以内，还是允许少量超预算作为备选？",
  "type": "single_choice",
  "options": [
    {"value": "strict_5000", "label": "严格 5000 以内", "recommended": true},
    {"value": "backup_5500", "label": "目标 5000，最高可到 5500"}
  ]
}
```

Adapter 选择展示方式：

- 有 `interactive_choice`：用 runtime 原生选择 UI。
- 无 `interactive_choice`：渲染为 Markdown 单题选择。
- 用户补充自由文本时，adapter 把原文放入 `answer_note`。

#### 3. Search Brief Execution

`plan` 输出 search brief 后，adapter 负责用 runtime 自带能力执行：

- 有 `web_search`：按 `search_batches` 执行搜索。
- 有 `browser_open`：打开高价值详情页，摘录用户可见字段。
- 无 `web_search`：提示用户提供链接、截图或复制文本。
- 无 `browser_open`：仅用 search result snippet，trust level 保持 L0。

核心规则：

- adapter 不保存 cookie/token/session。
- adapter 不要求用户提供平台账号。
- adapter 不绕验证码或登录墙。
- adapter 不把搜索片段当成已验真房源。

#### 4. Evidence Handoff

Adapter 最终交给 `ingest` 的格式必须是统一 evidence JSON：

```json
{
  "runtime_meta": {
    "runtime_name": "unknown",
    "adapter_version": "0.1.0",
    "capabilities": ["web_search", "structured_output"]
  },
  "query_context": {
    "scenario": "jd_hq_beijing_poc",
    "profile_hash": "local-profile-hash",
    "generated_at": "2026-06-13T10:00:00+08:00"
  },
  "items": []
}
```

`ingest` 只相信 schema，不相信 runtime 名称。即使来自 Codex / Claude / OpenClaw / Hermes，也必须通过同一套 evidence validator。

#### 5. Fallback + Error Protocol

Adapter 或 Agent 遇到能力缺失时，不应该失败退出，而是输出下一步可操作提示：

| 缺失能力 | 降级行为 |
| --- | --- |
| 无 `interactive_choice` | 输出 Markdown 单题选择 |
| 无 `web_search` | 要求用户提供链接、截图、复制文本 |
| 无 `browser_open` | 只收 search snippet，标记 L0 |
| 无 `local_file_write` | 输出 JSON/HTML 内容，并提示用户选择保存路径 |
| evidence JSON 不合法 | 调用 `ingest --validate` 返回字段级错误 |

POC 应新增两个和 adapter contract 相关的开发产物：

```text
docs/runtime-adapter-contract.md
tests/fixtures/runtime_adapters/
```

`docs/runtime-adapter-contract.md` 放完整 contract 和示例；主 POC 文档只保留设计摘要，避免后续继续膨胀。

### Profile 数据结构

POC profile 最小字段：

```json
{
  "profile_meta": {
    "schema_version": "0.2.0-poc",
    "created_at": "2026-06-13T10:00:00+08:00",
    "updated_at": "2026-06-13T10:00:00+08:00",
    "status": "draft"
  },
  "user_goal": {
    "target_days": 7,
    "scenario": "jd_hq_beijing_poc"
  },
  "office_anchor": {
    "company": "京东",
    "campus_name": "京东总部",
    "city": "北京",
    "anchor_id": "beijing-jd-hq-yizhuang",
    "nearest_metro": ["经海路"],
    "confidence": "user_confirmed"
  },
  "housing_constraints": {
    "budget_max": 5000,
    "budget_target": 4300,
    "rental_mode": "whole",
    "min_bedrooms": 1,
    "allow_studio": false,
    "move_in_by": null
  },
  "commute_preferences": {
    "strategy": "balanced",
    "max_minutes": 35,
    "preferred_modes": ["bike", "metro", "walk"],
    "derived_zones": ["经海路", "次渠南", "次渠嘉园", "次渠锦园", "锋创科技园"]
  },
  "risk_preferences": {
    "source_strategy": "public_all_channels",
    "allow_personal_transfer": true,
    "allow_apartment": true,
    "require_contact_path": true
  },
  "wizard_state": {
    "current_step": "done",
    "answered_question_ids": [],
    "confirmed_fields": [],
    "open_questions": []
  }
}
```

关键点：

- `budget_max` 是硬上限，`budget_target` 是推荐主力预算。
- `allow_studio` 区分“一居室硬要求”和“可接受开间”。
- `source_strategy` 不等于 provider；它描述公开渠道覆盖偏好。
- `wizard_state` 用于中断恢复。

### Profile Wizard 问题序列

POC 只做 6 道核心题。问题 ID 必须和 CLI 状态机保持一致，Agent runtime 展示给用户时可以只展示自然语言标题和 A/B/C/D 选项，不展示 `writes_to`。

| 顺序 | `question_id` | 确认内容 | 推荐项 | 写入字段 |
| --- | --- | --- | --- | --- |
| Q1 | `office_anchor` | 北京京东总部是否为亦庄经海路办公区 | 京东总部 / 亦庄经海路 | `office_anchor`、`commute_preferences.derived_zones_priority` |
| Q2 | `bedroom_scope` | 户型硬约束 | 正规一居 / 一室一厅 | `housing_constraints.preferred_bedrooms`、`min_bedrooms`、`allow_shared` |
| Q3 | `budget_strategy` | 预算是否允许备选超预算 | 严格按目标预算以内 | `housing_constraints.budget_target`、`budget_max`、`over_budget_policy` |
| Q4 | `commute_strategy` | 通勤和候选数量取舍 | 均衡通勤 | `commute_preferences.strategy`、`max_minutes`、`expand_zones_if_sparse` |
| Q5 | `source_strategy` | 公开来源覆盖范围 | 平台优先，个人转租补充 | `risk_preferences.source_strategy`、`preferred_sources` |
| Q6 | `risk_filter` | 风险过滤强度 | 稳妥过滤 | `risk_preferences.risk_filter` |

实际问题 JSON 由 `profile wizard next` 输出，统一形态为：

```json
{
  "question_id": "bedroom_scope",
  "title": "确认户型硬约束",
  "body": "请确认你要看的户型范围。",
  "type": "single_choice",
  "options": [
    {
      "value": "one_bedroom",
      "label": "正规一居 / 一室一厅",
      "description": "优先整租正规一居，默认排除合租。",
      "recommended": true
    }
  ],
  "writes_to": [
    "housing_constraints.preferred_bedrooms",
    "housing_constraints.min_bedrooms",
    "housing_constraints.allow_shared"
  ]
}
```

### Wizard 命令设计

CLI 只做状态机，不负责复杂交互 UI。

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard start \
  --scenario jd_hq_beijing_poc

python skills/last7days-rent/scripts/last7days_rent.py profile wizard next

python skills/last7days-rent/scripts/last7days_rent.py profile wizard answer \
  --question-id bedroom_scope \
  --value B

python skills/last7days-rent/scripts/last7days_rent.py profile wizard inspect

python skills/last7days-rent/scripts/last7days_rent.py profile wizard commit
```

Agent runtime 调用逻辑：

```text
1. 调用 wizard next 获取题目 JSON。
2. Agent 判断当前 runtime 是否有 interactive_choice capability。
3. 如果有，用 runtime 原生选择 UI 展示。
4. 如果没有，生成 Markdown 单题选择。
5. 用户选择后调用 wizard answer。
6. 默认只向用户展示简短确认，不展示 JSON。
7. 如果用户要求查看详情，调用 wizard inspect 展示当前 profile 或解释信息。
8. 重复直到 wizard_state.current_step = done。
9. 调用 wizard commit 写入 profile.json。
```

禁止在 CLI 核心中写这类分支：

```python
if runtime == "codex":
    ...
elif runtime == "claude":
    ...
```

允许在 runtime adapter 或文档示例中写这类映射：

```python
if capability("interactive_choice"):
    render_native_choice(question)
else:
    render_markdown_choice(question)
```

## 2. Agent Runtime 全渠道房源获取

### 删除 provider-first 路线

POC 中应删除或移除默认使用：

- `BRAVE_SEARCH_API_KEY`
- `EXA_API_KEY`
- `TAVILY_API_KEY`
- DDGS fallback
- `--provider-search`
- `--provider-extract`
- provider diagnostics 作为主报告内容

建议代码层改造：

| 当前内容 | POC 处理 |
| --- | --- |
| `providers/` | 删除或移到 `_legacy/providers/` |
| `provider-architecture.md` | 标记 deprecated 或删除 |
| provider config | 删除默认路径 |
| provider tests | 删除或改为 legacy tests |
| acquisition provider fallback | 改成 runtime evidence only |

保留的核心入口：

- `plan`：生成 Agent search brief。
- `ingest`：读取 Agent 搜索 evidence。
- `render`：输出 HTML。
- `feedback`：更新房源状态。

### 北京京东总部 Anchor Pack

POC 内置一个 Anchor Pack：

```json
{
  "anchor_id": "beijing-jd-hq-yizhuang",
  "city": "北京",
  "company": "京东",
  "campus_name": "京东总部",
  "aliases": ["京东总部", "北京京东总部", "京东亦庄总部"],
  "office_keywords": ["科创十一街", "经海路", "亦庄"],
  "commute_zones": [
    {
      "zone_id": "near_office",
      "label": "近公司",
      "keywords": ["经海路", "锋创科技园", "通泰国际公馆"],
      "priority": "A",
      "risk_notes": ["公寓/商住属性较多", "需核验水电和居住登记"]
    },
    {
      "zone_id": "value_residential",
      "label": "住宅性价比",
      "keywords": ["次渠南", "次渠嘉园", "次渠锦园", "次渠南里"],
      "priority": "A",
      "risk_notes": ["需确认到京东总部实际骑行/公交时间"]
    },
    {
      "zone_id": "budget_backup",
      "label": "预算备选",
      "keywords": ["东惠家园", "玉江佳园", "次渠北里", "泰禾1号街区"],
      "priority": "B",
      "risk_notes": ["可能是开间/公寓/合租变体，需严格核验"]
    }
  ]
}
```

### Search Brief 输出

`plan` 命令应输出 Agent 可执行的搜索 brief。

POC 阶段允许先为北京京东总部场景内置一份硬编码 search brief fixture，便于快速打通 `plan -> runtime search -> ingest -> render` 链路。但这只能作为测试夹具和样例，不应成为真实使用路径。

真实使用时，`plan` 必须从 profile + anchor pack 派生 search brief：

| Search Brief 字段 | 来源 |
| --- | --- |
| 户型关键词 | `housing_constraints.preferred_bedrooms` / `min_bedrooms` / `allow_studio` / `allow_shared` |
| 预算关键词 | `housing_constraints.budget_target` / `budget_max` / `over_budget_policy` |
| 通勤圈 | `commute_preferences.strategy` + anchor pack `commute_zones` |
| 来源渠道 | `risk_preferences.source_strategy` / `preferred_sources` |
| 扩圈策略 | `commute_preferences.expand_zones_if_sparse` |
| 风险过滤 | `risk_preferences.risk_filter` |

因此，下面 JSON 是 POC 样例。正式实现中不能写死“一居室 / 5000”，必须用 profile 渲染模板。比如用户在 wizard 中改成“二居室、最高 5500”，search brief 和 HTML 标题都必须同步变成“二居室 / 5500 以内”。

```json
{
  "profile_id": "local-current",
  "scenario": "jd_hq_beijing_poc",
  "search_batches": [
    {
      "id": "structured_platforms",
      "goal": "获取平台型一居/整租线索",
      "queries": [
        "北京 京东总部 一居室 5000以内 租房 亦庄",
        "北京 经海路 一居室 5000 租房",
        "北京 次渠南 一居室 5000 租房",
        "北京 次渠嘉园 一居室 租房 京东总部",
        "北京 次渠锦园 一居室 租房 京东总部"
      ],
      "preferred_sources": ["58", "安居客", "贝壳", "链家", "自如", "我爱我家"]
    },
    {
      "id": "community_posts",
      "goal": "获取个人转租/房东直租线索",
      "queries": [
        "site:douban.com/group 亦庄租房 京东总部 一居室",
        "site:douban.com/group 经海路 整租一室 免中介费",
        "site:douban.com/group 锋创科技园 整租 一室"
      ],
      "preferred_sources": ["豆瓣公开小组", "公开文章"]
    },
    {
      "id": "anchor_validation",
      "goal": "核验办公锚点和通勤圈",
      "queries": [
        "北京 京东总部 地址 经海路 科创十一街",
        "京东总部 经海路 地铁 步行"
      ],
      "preferred_sources": ["官方地图", "公开地图", "公司公开信息"]
    }
  ],
  "run_budget": {
    "target_accepted_listings": 10,
    "max_search_batches": 4,
    "max_queries_per_batch": 6,
    "max_results_per_query": 8,
    "max_detail_pages_total": 20,
    "max_detail_pages_per_source": 5,
    "expand_if_accepted_below": 6
  },
  "collection_rules": {
    "must_capture": ["source_url", "title", "snippet", "observed_at", "source_name"],
    "capture_when_visible": ["price_text", "area_text", "layout_text", "community", "district_hint", "contact_path"],
    "privacy": [
      "不公开原发帖人身份",
      "不保存 cookie/token/session",
      "公开联系方式只作为 contact_path，报告中优先展示平台入口"
    ]
  }
}
```

### Evidence 输入格式

Agent runtime 搜到房源后，整理成统一 JSON：

```json
{
  "runtime_meta": {
    "runtime_name": "unknown",
    "adapter_version": "0.1.0",
    "capabilities": ["web_search", "browser_open", "structured_output"]
  },
  "query_context": {
    "scenario": "jd_hq_beijing_poc",
    "city": "北京",
    "office_anchor": "北京京东总部",
    "budget_target": 5000,
    "budget_max": 5500,
    "preferred_bedrooms": 2,
    "profile_hash": "local-profile-hash",
    "generated_at": "2026-06-13T10:00:00+08:00"
  },
  "items": [
    {
      "evidence_id": "ev-001",
      "batch_id": "structured_platforms",
      "query_id": "structured_platforms-q03",
      "query": "北京 次渠锦园 二居室 5500 租房 京东总部",
      "collected_via": "web_search_result",
      "source_url": "https://example.com/listing/1",
      "canonical_url": "https://example.com/listing/1",
      "source_domain": "example.com",
      "source_name": "58",
      "source_type": "platform_listing",
      "page_opened": false,
      "title": "次渠锦园北区精装二居室",
      "snippet": "2室 60平 5300元/月 次渠南地铁站附近",
      "raw_excerpt": "搜索结果页可见摘要，未打开详情页",
      "observed_at": "2026-06-13T10:00:00+08:00",
      "visible_fields": {
        "price_text": "5300元/月",
        "area_text": "60平",
        "layout_text": "2室",
        "community": "次渠锦园北区",
        "district_hint": "次渠南"
      },
      "normalized_fields": {
        "price_monthly": 5300,
        "area_sqm": 60,
        "bedrooms": 2
      },
      "field_confidence": {
        "price_monthly": "medium",
        "area_sqm": "medium",
        "bedrooms": "medium",
        "community": "medium"
      },
      "contact_path": {
        "type": "platform_entry",
        "entry_url": "https://example.com/listing/1"
      },
      "listing_status_hint": "unknown",
      "agent_notes": [
        "待核验是否民水民电",
        "待核验是否包物业取暖"
      ]
    }
  ]
}
```

POC 的 evidence schema 不需要一次性做成最终版，但最小可稳定 ingest 字段应包括：

| 字段 | 是否必需 | 用途 |
| --- | --- | --- |
| `evidence_id` | 必需 | 追溯 observation |
| `batch_id` / `query_id` | 必需 | 追溯 search brief 来源 |
| `source_url` | 必需 | 进入主列表和去重 |
| `canonical_url` | 可由 ingest 补齐 | URL 去重 |
| `source_domain` | 可由 ingest 补齐 | 来源统计和风控 |
| `collected_via` | 必需 | 区分 search snippet / opened page / user supplied |
| `page_opened` | 必需 | 判断最高可信等级 |
| `raw_excerpt` | 必需 | 字段追溯，不保存整页 |
| `visible_fields` | 必需 | 用户可见字段 |
| `normalized_fields` | 可由 ingest 补齐 | 排序、筛选、预算/户型判断 |
| `field_confidence` | 推荐 | 告诉用户哪些字段仍待核验 |
| `contact_path` | 推荐 | 没有时进入观察池，不进首看列表 |
| `listing_status_hint` | 推荐 | `unknown/active/expired/leased` |

Ingest 规则：

- 搜索结果 snippet 只产生 L0。
- Agent 打开页面并摘录可见字段后，最多 L1。
- 多来源重复不能自动提升到 L2；L2 必须是独立来源交叉确认。
- 用户反馈确认后才是 L3。
- 无 `source_url` 的线索不进入 HTML 主列表。
- 无可行动联系路径的线索可以进入观察池，但不进首看列表。

Trust level 规则：

| 等级 | 条件 | 说明 |
| --- | --- | --- |
| L0 | 只有搜索结果、snippet、用户复制的单段文本，或未打开详情页 | 候选线索，不视为可联系房源 |
| L1 | Agent 打开公开详情页，摘录到价格/户型/小区/面积/联系入口中的至少 3 项 | 待核验房源，可进入主列表 |
| L2 | 至少两个独立来源交叉确认，且价格、小区/片区、户型、面积、联系入口或平台入口基本一致 | 可优先联系，但仍不是已验真 |
| L3 | 用户已联系、已约看、已看房，或用户明确反馈仍在租/已出租/真实可约 | 只能来自用户反馈 |

L2 独立来源要求：

- 同一中介在多个平台分发，不算独立来源。
- 同一平台不同 URL 但标题/联系方式高度一致，不算独立来源。
- 平台房源 + 个人帖子可以算独立来源，但必须有小区/价格/户型/面积中至少 3 项一致。
- 官方地图或公司地址只能作为锚点 evidence，不提升房源 trust level。

Merge 规则：

- 优先用 `canonical_url` 去重。
- 无稳定 URL 时，用 `community + price_monthly + bedrooms + area_sqm` 弱匹配。
- 弱匹配只合并为 observation，不直接提升 trust level。
- 用户状态字段，例如 `shortlisted/contacted/rejected`，merge 时必须保留。

执行预算和停止条件：

| 项目 | POC 默认值 | 说明 |
| --- | --- | --- |
| 首轮目标主列表候选 | 10 条 | 少于 10 条也可以交付，但要显示 coverage gap |
| 每个 search batch 最多 query | 6 条 | 避免 runtime 无边界搜索 |
| 每条 query 最多采纳结果 | 8 条 | 只取可见字段较完整的结果 |
| 每轮最多打开详情页 | 20 页 | 优先打开平台房源和字段完整候选 |
| 单一来源最多详情页 | 5 页 | 避免被单一平台污染候选池 |
| 首轮扩圈触发 | 主列表候选少于 6 条 | 从近通勤圈扩到 profile 中的 backup zones |
| 停止条件 | 已有 10 条主列表候选，或所有 batch 执行完成，或连续 2 个 batch 无新增主列表候选 | 停止后生成 HTML，而不是继续搜索 |

扩圈顺序：

1. 先搜 `derived_zones_priority` 中的近通勤圈。
2. 若主列表少于 6 条，启用 `expand_zones_if_sparse`。
3. 若仍少于 6 条，保留 coverage gap，不自动放宽预算/户型硬约束。
4. 放宽预算或户型必须回到 profile wizard 让用户确认。

### 全渠道来源优先级

| 渠道 | POC 角色 | 可信等级默认值 | 说明 |
| --- | --- | --- | --- |
| 58 / 安居客 | 主力 L0/L1 候选池 | L0-L1 | 房源多，但要警惕引流 |
| 贝壳 / 链家 | 平台对照 | L0-L1 | 可能验证码/登录墙，保留公开链接即可 |
| 自如 / 我爱我家 | 品牌/平台对照 | L0-L1 | 适合做稳定性参照 |
| 豆瓣公开小组 | 个人转租补充 | L0 | 不公开发帖人身份，严格标待核验 |
| Wellcee / 公开文章 | 补充来源 | L0-L1 | 有结构化字段则进入候选 |
| 地图/官方信息 | 锚点核验 | evidence | 不作为房源来源 |

## 3. HTML 模板化展示

### 输出原则

最终交付给用户的是本地 HTML，而不是 Markdown。

HTML 是人类工作台；JSON 是机器状态。

```text
~/.last7days-rent/
  profiles/
    jd-hq-beijing.profile.json
  pools/
    jd-hq-beijing.listing-pool.json
  reports/
    jd-hq-beijing-rentals.html
    jd-hq-beijing-evidence.json
```

HTML 可以是单文件，便于打开和分享；但更新状态应回写 JSON pool。

### Listing Pool 数据结构

```json
{
  "pool_meta": {
    "pool_id": "jd-hq-beijing",
    "scenario": "jd_hq_beijing_poc",
    "created_at": "2026-06-13T10:00:00+08:00",
    "updated_at": "2026-06-13T10:00:00+08:00"
  },
  "profile_summary": {},
  "listings": [
    {
      "listing_id": "listing-abc123",
      "status": "new",
      "priority": "A",
      "trust_level": "L0",
      "title": "次渠锦园北区精装一居室",
      "community": "次渠锦园北区",
      "district_hint": "次渠南",
      "price_monthly": 3950,
      "price_text": "3950元/月",
      "area_text": "60平",
      "layout_text": "1室",
      "commute_tags": ["次渠南", "京东总部通勤圈"],
      "source_names": ["58"],
      "source_urls": ["https://example.com/listing/1"],
      "contact_path": {
        "type": "platform_entry",
        "entry_url": "https://example.com/listing/1"
      },
      "risk_flags": ["needs_fee_verification"],
      "next_actions": ["确认民水民电", "确认是否包物业取暖", "确认仍在租"],
      "first_seen_at": "2026-06-13T10:00:00+08:00",
      "last_seen_at": "2026-06-13T10:00:00+08:00",
      "observations": ["ev-001"]
    }
  ]
}
```

### HTML 页面结构

模板结构：

```text
Header
  - 标题：北京京东总部 5000 内一居室候选池
  - Profile 摘要：预算、户型、通勤策略、更新时间

Controls
  - 搜索框
  - 预算筛选
  - 片区筛选
  - 来源筛选
  - 可信等级筛选
  - 风险筛选
  - 状态筛选

Summary
  - 候选总数
  - A/B/C 优先级数量
  - 主力价格区间
  - 待核验风险数量

Listing Cards / Table
  - 小区/标题
  - 租金/面积/户型
  - 片区/通勤标签
  - 来源链接
  - 可信等级
  - 风险标签
  - 下一步动作
  - 当前状态

Sections
  - 首看列表
  - 备选列表
  - 低预算/过渡列表
  - 已排除/已过期列表

Footer
  - 来源说明
  - 隐私说明
  - 更新时间
```

### HTML 交互

POC 阶段只需要前端本地交互：

- 搜索。
- 筛选。
- 排序。
- 展开/折叠详情。
- 点击来源链接。
- 标记状态可先不回写，状态更新通过 CLI 或下一轮 ingest 完成。

后续增强：

- HTML 内编辑状态并导出 JSON patch。
- 本地小型静态 app。
- 看房日程和联系记录。

### CSS / UI 要求

- 单文件 HTML，内联 CSS/JS。
- 信息密度高，适合反复查看。
- 不做营销式 landing page。
- 卡片或表格都可以，但必须能快速比较。
- 移动端可读。
- 风险标签明显。
- 不展示原发帖人身份。
- 不把 unknown 字段留空，要显示“待核验”。

## 更新与合并逻辑

每次新一轮搜索后：

1. 读取现有 listing pool。
2. 规范化 URL。
3. 用 canonical URL 去重。
4. 对没有稳定 URL 的线索，用标题 + 小区 + 价格 + 面积弱匹配。
5. 保留用户状态，例如 `shortlisted`、`contacted`、`rejected`。
6. 更新 `last_seen_at`。
7. 追加 observations。
8. 长时间未出现的标记为 `stale`。
9. 重新生成 HTML。

状态枚举：

| 状态 | 含义 |
| --- | --- |
| `new` | 新发现 |
| `shortlisted` | 用户感兴趣 |
| `contacted` | 已联系 |
| `scheduled` | 已约看 |
| `viewed` | 已看房 |
| `rejected` | 用户排除 |
| `stale` | 疑似过期 |
| `leased` | 确认已出租 |

## POC 验收标准

以用户提供一个短 `goal seed` 启动：

```text
北京京东总部，一居室，5000 RMB 以内。
```

Live POC 验收标准：

1. Agent 从 `goal seed` 预填锚点、户型、预算，并通过 6 道以内选择/确认题完成 profile。
2. Profile 写入本地 JSON，包含预算、户型、通勤策略、来源偏好。
3. `plan` 生成北京京东总部 search brief。
4. Agent runtime 使用 web search 获取至少 10 条公开房源 evidence。
5. `ingest` 生成 listing pool。
6. `render` 生成本地 HTML。
7. HTML 至少展示 10 条候选，并支持搜索/筛选。
8. 每条候选包含来源链接、价格、面积/户型可见字段、片区、可信等级、风险、下一步动作。
9. 不展示原发帖人身份，不保存 secret，不补全未知字段。
10. 第二轮搜索可以 merge 到同一 pool，并保留用户状态。

公开测试夹具只覆盖小规模 smoke flow：`tests/fixtures/evidence/jd_hq_runtime_evidence.json` 目前用于验证 schema、去重、L0/L1/L2 和 HTML render，不代表 live POC 的 10 条候选目标已经由 fixture 覆盖。

## 参考依据

- Codex best practices：Plan mode 适合复杂/模糊任务，Codex 可以先收集上下文并提问后再执行。
- Codex app server：`tool/requestUserInput` 可向用户展示 1-3 个短问题，适合作为 Codex app 的结构化选择 UI。
- Claude Code user input：`AskUserQuestion` 可用于多选澄清问题，适合 profile wizard。
- Claude Code tools schema：`AskUserQuestion` 的问题包含 header、options、multiSelect 和 answers，能直接映射本设计的问题结构。

## 后续扩展

POC 成功后再扩展：

- 北京其他大厂 Anchor Pack。
- 上海、深圳、杭州 P0 Anchor Pack。
- HTML 内状态编辑和 JSON patch 导出。
- 联系记录和看房日程。
- 用户授权导入私域线索。
- 7 天行动计划自动更新。

当前阶段先把一条链路打穿：

```text
问清楚 -> 搜得到 -> 理得顺 -> 看得懂 -> 能更新
```
