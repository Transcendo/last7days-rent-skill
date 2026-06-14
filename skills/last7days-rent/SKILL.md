---
name: last7days-rent
description: "帮助用户 7 天完成租房。基于本地 private profile，通过 Agent runtime 自带 web search/browser 发现公开房源线索，并将 evidence 整理为本地可更新 HTML 房源列表。"
---

# last7days-rent

last7days = 帮助用户 7 天完成租房。

这是一个 Agent Skill + 本地 CLI engine，不是平台爬虫。默认使用 Agent runtime 原生能力完成三件事：问答式 profile 收集、公开渠道房源发现、evidence 交接；本工具只负责本地 profile 状态、search brief、evidence ingest、可信等级、去重排序和 HTML 房源列表。

## 触发条件

当用户表达以下需求时使用本技能：

- 想 7 天完成租房。
- 想基于公司、办公点、园区、预算、户型、通勤圈找房。
- 想在 Codex、Claude Code、OpenClaw、Hermes Agent 等 runtime 中完成租房规划。
- 提供房源 URL、截图、复制文本或搜索结果，要求整理成可筛选房源列表。
- 想获得可溯源房源线索、联系路径、风险标签、下一步核验问题和 7 天行动计划。

## 默认工作流

默认不要让用户填写长表单，也不要要求用户手写 JSON。

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard start --goal-seed "北京京东总部，一居室，5000 RMB 以内"
python skills/last7days-rent/scripts/last7days_rent.py profile wizard next
python skills/last7days-rent/scripts/last7days_rent.py profile wizard answer --question-id <id> --value <A|B|C|D>
python skills/last7days-rent/scripts/last7days_rent.py profile wizard commit
python skills/last7days-rent/scripts/last7days_rent.py plan --explain
python skills/last7days-rent/scripts/last7days_rent.py ingest --evidence <runtime-evidence.json> --validate
python skills/last7days-rent/scripts/last7days_rent.py ingest --evidence <runtime-evidence.json>
python skills/last7days-rent/scripts/last7days_rent.py render
python skills/last7days-rent/scripts/last7days_rent.py report --latest
```

`search` 如果存在，只能作为兼容提示，不应作为默认路径。

## Profile 问答规则

1. 一次只问一个决策题。
2. 推荐项排第一。
3. 用户回答后只给简短确认和下一题，不默认展示 JSON。
4. 用户明确说“查看当前 profile / 展示 JSON / 为什么这么搜”时，才调用 inspect 或 plan explain。
5. 预算、户型、通勤、来源偏好、风险偏好都必须写入 profile，后续 search brief 必须从 profile 派生。
6. 不要在 search brief 中硬编码用户已经改过的预算、户型或通勤策略。

## Runtime 使用原则

不要检测 runtime 品牌名。只根据能力工作：

- 有原生选择 UI：用选择 UI 呈现 profile wizard。
- 没有选择 UI：用 Markdown 单题选择。
- 有 web search/browser：按 `plan` 执行公开渠道发现和页面核验。
- 没有 web search/browser：请用户提供链接、截图或复制文本。
- 有 structured output：产出 evidence JSON。
- 没有 structured output：产出 fenced JSON，并让用户保存为本地文件后 ingest。

## Evidence 规则

Agent runtime 交给 `ingest` 的 JSON 必须包含 `items`。每个 item 至少包含：

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

推荐包含：

- `canonical_url`
- `source_domain`
- `normalized_fields`
- `field_confidence`
- `contact_path`
- `listing_status_hint`

缺字段时先运行：

```bash
python skills/last7days-rent/scripts/last7days_rent.py ingest --evidence <file> --validate
```

## 可信等级

| 等级 | 规则 |
| --- | --- |
| L0 | 搜索结果、片段、复制文本或未打开页面 |
| L1 | 已打开公开页面，且至少 3 个关键字段可见 |
| L2 | 至少两个独立来源交叉确认同一房源，且关键字段一致 |
| L3 | 用户已联系、约看、实看或明确反馈仍在租 |

同一中介跨平台重复分发不算独立来源。L3 只能来自用户反馈，不能由搜索或模型推断产生。

## 边界

- 不要求 cookie、token、secret 或登录态。
- 不绕验证码、不登录、不做反自动化对抗。
- 不保存平台内部接口响应。
- 不自动抓微信群、朋友圈、公司群、校友群等私域内容。
- 不保存或公开原发帖人的真实身份。
- 不用模型补全未知价格、地址、押金、入住时间或联系方式。
- 不承诺每套房仍在租，不替代线下看房、付款、签约和合同审查。

## 输出

默认人类交付物是 HTML 房源列表；JSON 只作为机器证据包和可更新状态。

HTML 应包含：

- profile 摘要。
- 可筛选房源卡片。
- 来源链接。
- 可信等级和风险标签。
- 下一步核验动作。
- 本地更新时间。

JSON 应包含：

- profile。
- search brief。
- runtime evidence。
- listing pool。
