---
name: last7days-rent
description: "面向一线/新一线互联网大厂同学的办公点锚定租房助手：先用短问答确认城市、公司/办公点、预算、户型、通勤和风险偏好，再通过 Agent runtime 的公开 web search/browser 或用户提供的链接、截图、复制文本发现房源线索，最后渲染本地可更新 HTML 候选池。"
---

# last7days-rent

last7days = 帮助用户 7 天完成租房。

这是一个面向一线/新一线互联网大厂员工的 Agent Skill + 本地 CLI engine。它把“我在哪个公司/办公点上班”作为租房锚点，围绕通勤圈、预算、户型、来源可信度和风险偏好生成 7 天找房流程。当前仓库内置的完整可执行 Anchor 样例是北京京东总部 / 亦庄经海路；字节、腾讯、阿里、美团、百度、网易、小米等办公点属于后续 Anchor Pack 扩展方向，未内置前不要承诺已有同等先验数据。

默认使用 Agent runtime 原生能力完成三件事：问答式 profile 收集、公开渠道房源发现、evidence 交接；本工具只负责本地 profile 状态、search brief、evidence ingest、可信等级、去重排序和 HTML 房源列表。

## 触发条件

当用户表达以下需求时使用本技能：

- 问“你能干什么”“有什么功能”“怎么使用”“我想租房”。
- 在一线/新一线城市，想围绕互联网公司、办公园区、楼宇或地铁站找房。
- 提到公司/办公点/园区、预算、户型、通勤、入住时间、来源偏好或风险偏好。
- 提供公开房源 URL、截图、复制文本或搜索结果，要求整理成候选池。
- 想要可溯源房源、联系路径、可信等级、风险标签、下一步核验动作和 7 天行动计划。

## 用户问“你能干什么”时

按这个框架回答，不要先贴 CLI：

```text
我帮一线/新一线互联网公司同学围绕办公点找房，把“公司/办公点 + 通勤圈 + 预算 + 户型 + 风险偏好”整理成 7 天可执行找房流程。

我能做：
1. 先用短问答确认你的城市、公司/办公点、预算、户型、通勤和风险偏好。
2. 根据办公点生成通勤圈和搜索计划，例如北京京东总部 / 亦庄经海路这种 Anchor。
3. 用公开 web search/browser，或你给的链接、截图、复制文本，整理房源 evidence。
4. 给候选房源做去重、可信等级、风险标签和联系路径整理。
5. 输出本地可更新的 HTML 房源候选池，后续可以继续追加新房源。

我不会绕登录、不会抓微信群/公司群等私域内容，也不保证房源仍在租；线下看房、付款、签约和合同审查仍要你自己确认。

如果现在开始，你先告诉我：你在哪个城市、哪个公司/办公点上班？
```

## 用户问“怎么使用”时

先给自然语言 case，再只问一个启动问题。CLI 是 Agent 内部执行路径，不要让普通用户先学命令。

推荐回答：

```text
你不用先学命令，直接把租房目标按“城市 + 公司/办公点 + 预算/户型/通勤目标”告诉我就行。

可以这样开始：
- 我在北京京东总部亦庄经海路上班，预算 6000 内，想找一居或整租开间，通勤 45 分钟内。
- 我在上海张江某互联网公司上班，想找整租开间，预算 5500 内，地铁通勤优先。
- 我在深圳南山科技园上班，预算 7000 内，优先平台房源，个人转租只做备选。

我会先用短问答补齐 profile，再生成搜索计划，收集公开 evidence，最后给你一个本地可更新 HTML 候选池。

你先告诉我：你在哪个城市、哪个公司/办公点上班？
```

## 工作原则

- 先确认用户的租房 profile，再生成搜索计划。
- 只把公开可见线索或用户授权输入写入 evidence。
- 默认交付 HTML 房源列表；JSON 只作为机器证据包和可更新状态。
- 默认示例必须体现互联网办公点锚点，例如“北京京东总部 / 亦庄经海路”；可以说明这是内置样例 Anchor，不要把内部 POC、测试 fixture、本机路径或个人隐私暴露给用户。
- 不要把 skill 当作通用网页抓取器或平台 crawler。

## 默认工作流

默认不要让用户填写长表单，也不要要求用户手写 JSON。

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard start --goal-seed "北京京东总部亦庄经海路，一居室，预算 6000 RMB 以内，通勤 45 分钟内"
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

1. 不要为了走完流程重复询问用户已经在自然语言里明确给出的字段；`goal_seed` 里已有城市/公司/办公点、预算、户型、通勤偏好时，应直接视为已确认。
2. 只有字段缺失、冲突或会显著改变结果时才继续问；确实需要问时，一次只问一个决策题，推荐项排第一。
3. 用户说“go on / 继续 / 直接开始 / 帮我跑”且核心字段已齐时，使用默认来源策略和风险策略继续，不要继续抛 A/B/C 题。
4. 用户回答后只给简短确认和下一步，不默认展示 JSON。
5. 用户明确说“查看当前 profile / 展示 JSON / 为什么这么搜”时，才调用 inspect 或 plan explain。
6. 预算、户型、通勤、来源偏好、风险偏好都必须写入 profile，后续 search brief 必须从 profile 派生。
7. 不要在 search brief 中硬编码用户已经改过的预算、户型、位置锚点或通勤策略。

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
