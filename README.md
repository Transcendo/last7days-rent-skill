# last7days-rent-skill

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Local](https://img.shields.io/badge/local--first-runtime%20native-0f766e)
![Status](https://img.shields.io/badge/status-JD%20HQ%20POC-0f766e)

`last7days-rent-skill` 是一个面向 Codex、Claude Code、OpenClaw、Hermes Agent 等 Agent runtime 的租房 Skill。它不再自建搜索引擎或要求搜索 API key；默认路径是：

```text
profile wizard -> plan -> Agent runtime web search/browser -> ingest evidence -> render HTML
```

当前 POC 聚焦“北京京东总部租房”：通过问答式 profile wizard 确认办公锚点、预算、户型、通勤和风险偏好；由 Agent runtime 使用自身 web search/browser 能力发现公开房源线索；工具负责把 evidence JSON 去重、分级、沉淀为本地可更新的 HTML 房源列表。

## 快速开始

安装本地 skill：

```bash
npx skills add /path/to/last7days-rent-skill -g
```

查看命令：

```bash
python skills/last7days-rent/scripts/last7days_rent.py --help
```

启动北京京东总部 profile wizard：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard start \
  --goal-seed "北京京东总部，一居室，5000 RMB 以内"
```

逐题确认：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard next
python skills/last7days-rent/scripts/last7days_rent.py profile wizard answer --question-id office_anchor --value A
python skills/last7days-rent/scripts/last7days_rent.py profile wizard answer --question-id bedroom_scope --value B
python skills/last7days-rent/scripts/last7days_rent.py profile wizard answer --question-id budget_strategy --value B
python skills/last7days-rent/scripts/last7days_rent.py profile wizard answer --question-id commute_strategy --value B
python skills/last7days-rent/scripts/last7days_rent.py profile wizard answer --question-id source_strategy --value B
python skills/last7days-rent/scripts/last7days_rent.py profile wizard answer --question-id risk_filter --value B
```

默认 answer 只返回简短确认和下一题，不向用户暴露完整 JSON。用户需要时可以查看：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard inspect
python skills/last7days-rent/scripts/last7days_rent.py profile wizard inspect --format json
```

确认 profile 并生成搜索计划：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard commit
python skills/last7days-rent/scripts/last7days_rent.py plan --explain
```

`plan` 会从 profile 和北京京东总部 anchor pack 派生 search brief，包括查询批次、候选来源、执行预算和停止条件。Agent runtime 应按 brief 执行公开 web search/browser，并把结果整理成 evidence JSON。

校验并导入 runtime evidence：

```bash
python skills/last7days-rent/scripts/last7days_rent.py ingest \
  --evidence tests/fixtures/evidence/jd_hq_runtime_evidence.json \
  --validate

python skills/last7days-rent/scripts/last7days_rent.py ingest \
  --evidence tests/fixtures/evidence/jd_hq_runtime_evidence.json
```

生成 HTML 房源列表：

```bash
python skills/last7days-rent/scripts/last7days_rent.py render
python skills/last7days-rent/scripts/last7days_rent.py report --latest
```

默认本地输出路径：

```text
~/.last7days-rent/profile.json
~/.last7days-rent/profiles/
~/.last7days-rent/pools/
~/.last7days-rent/reports/
~/.last7days-rent/feedback.jsonl
```

## 输出内容

默认人类产物是单文件 HTML：

- profile 摘要：办公锚点、预算、户型、通勤策略。
- 房源卡片：标题、小区、价格、面积、户型、片区、来源链接。
- 筛选控件：关键词、可信等级、状态、风险标签。
- 可信等级：L0/L1/L2/L3。
- 风险标签：片段线索、缺少联系路径、字段待核验等。
- 下一步动作：打开来源、确认仍在租、核验费用和联系入口。

机器产物是 JSON：

- profile draft / committed profile。
- search brief。
- runtime evidence。
- listing pool。

## Runtime Evidence Contract

Agent runtime 不需要让工具判断“当前是 Codex 还是 Claude Code”。核心只看能力和协议：

- `interactive_choice`：逐题确认 profile。
- `web_search`：公开渠道发现。
- `browser_open`：打开公开页面核验可见字段。
- `local_file_write`：写入 evidence、pool、HTML。
- `structured_output`：把搜索结果交给 `ingest`。

Evidence item 至少包含：

- `evidence_id`
- `batch_id`
- `query_id`
- `query`
- `collected_via`
- `source_url`
- `source_name`
- `source_type`
- `page_opened`
- `title`
- `snippet`
- `raw_excerpt`
- `observed_at`
- `visible_fields`

推荐额外字段：

- `canonical_url`
- `source_domain`
- `normalized_fields`
- `field_confidence`
- `contact_path`
- `listing_status_hint`

详见 [Runtime Adapter Contract](docs/runtime-adapter-contract.md)。

## 可信等级

| 等级 | 含义 | 使用方式 |
| --- | --- | --- |
| L0 | 搜索结果、片段、复制文本或未打开页面 | 只能作为待核验候选 |
| L1 | 已打开公开页面，且至少 3 个关键字段可见 | 可低置信展示 |
| L2 | 至少两个独立来源交叉确认同一房源，且价格/小区/户型/面积/联系入口等关键字段一致 | 可进入短名单 |
| L3 | 用户已联系、约看、实看或明确反馈仍在租 | 可重点推荐 |

同一中介在多个平台重复分发不算独立来源。L3 只能来自用户反馈，不能由搜索、模型推断或多源重复自动升级。

## 渠道边界

POC 允许：

- Agent runtime 使用公开 web search 查找公开结果页、公开详情页和公开帖子。
- Agent runtime 打开用户当前可见的公开页面，并摘录必要字段。
- 用户主动提供链接、截图、复制文本或浏览器可见内容。
- 工具保存房源摘要、来源链接、抓取时间、可信等级、风险标记和联系路径。

POC 不做：

- 面向具体平台的长期批量 crawler。
- 验证码对抗、登录自动化、cookie 复用或登录态保存。
- 要求用户交出账号、cookie、token 或平台内部接口响应。
- 大规模复制、镜像、转载第三方平台内容。
- 把搜索片段写成已验真房源。
- 保存或公开原发帖人的真实身份。

## Profile 交互原则

- 一次只问一个决策题。
- 推荐项排第一。
- 用户只需要选择或纠偏，不需要手写结构化 JSON。
- 默认隐藏 profile JSON、search brief 和 evidence schema。
- 用户明确要求“查看 JSON / 查看当前 profile / 为什么这么搜”时再展示内部结构。

## 开发验证

```bash
python3 -m pytest
python skills/last7days-rent/scripts/last7days_rent.py --help
python skills/last7days-rent/scripts/last7days_rent.py report --latest
```

## 更多文档

- [北京京东总部 POC 方案](docs/poc-jd-hq-runtime-profile-html.md)
- [Runtime Adapter Contract](docs/runtime-adapter-contract.md)
- [Anchor Pack Scope](docs/poc-anchor-pack-scope.md)
- [来源政策](docs/source-policy.md)

## License

MIT License. See [LICENSE](LICENSE).
