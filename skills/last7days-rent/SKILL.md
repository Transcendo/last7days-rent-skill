---
name: last7days-rent
description: "面向一线/新一线城市互联网大厂同学的 7 天快速租房助手：本地化收集租房需求生成 profile，基于 profile 全渠道聚合公开房源和用户授权输入，生成个人租房 HTML，并可按最新 profile 持续 refresh。"
---

# last7days-rent

last7days = 帮助一线/新一线城市互联网大厂同学 7 天快速租房。

这是一个面向互联网大厂员工租房场景的 Agent Skill + 本地 CLI engine。核心目标是：根据用户自己的租房需求，全渠道聚合公开可用和用户授权输入的房源信息，帮助用户在 7 天内快速完成租房决策。

仓库职责固定为四件事：

1. 本地化收集用户租房需求，生成专属租房 profile。
2. 基于 profile 进行全渠道搜索适配和房源信息聚合。
3. 生成专属个人租房 HTML 候选池。
4. 基于本地最新 profile 持续更新全渠道房源信息。

默认使用 Agent runtime 原生能力完成公开 web search/browser 和用户授权内容整理；本工具负责本地 profile 状态、全渠道 search brief、evidence ingest、可信等级、去重排序、持续 refresh 和 HTML 房源列表。

当前仓库内置的完整可执行 Anchor 样例是北京京东总部 / 亦庄经海路；字节、腾讯、阿里、美团、百度、网易、小米等办公点属于后续 Anchor Pack 扩展方向，未内置前不要承诺已有同等先验数据。

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
1. 本地化收集你的租房需求，生成专属租房 profile。
2. 根据 profile 生成全渠道搜索 brief，覆盖公开平台、品牌公寓、公开转租社区和你授权导入的材料。
3. 用公开 web search/browser，或你给的链接、截图、复制文本，整理房源 evidence。
4. 给候选房源做去重、可信等级、风险标签和联系路径整理。
5. 输出本地可更新的个人租房 HTML，后续按最新 profile 继续 refresh。

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

我会先用短问答补齐 profile，再执行全渠道 refresh，收集公开 evidence，最后给你一个本地可更新的个人 HTML 候选池。

你先告诉我：你在哪个城市、哪个公司/办公点上班？
```

## 工作原则

- 先确认用户的租房 profile，再生成搜索计划。
- 只把公开可见线索或用户授权输入写入 evidence。
- 默认交付 HTML 房源列表；JSON 只作为机器证据包和可更新状态。
- “全渠道”只包括合规公开渠道和用户授权输入，不包括自动抓取私域群聊、登录后内容或绕验证码。
- 默认示例必须体现互联网办公点锚点，例如“北京京东总部 / 亦庄经海路”；可以说明这是内置样例 Anchor，不要把内部 POC、测试 fixture、本机路径或个人隐私暴露给用户。
- 不要把 skill 当作通用网页抓取器或平台 crawler。

## 默认工作流

默认不要让用户填写长表单，也不要要求用户手写 JSON。

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard start --goal-seed "北京京东总部亦庄经海路，一居室，预算 6000 RMB 以内，通勤 45 分钟内"
python skills/last7days-rent/scripts/last7days_rent.py profile wizard next
python skills/last7days-rent/scripts/last7days_rent.py profile wizard answer --question-id <id> --value <A|B|C|D>
python skills/last7days-rent/scripts/last7days_rent.py profile wizard commit
python skills/last7days-rent/scripts/last7days_rent.py refresh --prepare
python skills/last7days-rent/scripts/last7days_rent.py refresh --evidence <runtime-evidence.json>
python skills/last7days-rent/scripts/last7days_rent.py report --latest
```

`plan`、`ingest`、`render` 是底层调试命令。`search` 如果存在，只能作为兼容提示，不应作为默认路径。

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
- 有 web search/browser：按 `refresh --prepare` 生成的 brief 执行公开渠道发现和页面核验。
- 没有 web search/browser：请用户提供链接、截图或复制文本。
- 有 structured output：产出 evidence JSON。
- 没有 structured output：产出 fenced JSON，并让用户保存为本地文件后 ingest。

## Runtime source audit 契约

`refresh --prepare` 生成的 search brief 是后续 evidence 的上下文，runtime 执行时必须把它带回：

- 优先在 evidence 中写入 `query_context.brief_path`；如果不能保证本地路径可读，就内联完整 `search_brief`。
- 按 search brief 的 6 个 batch 顺序执行，不能只跑豆瓣或只跑已熟悉渠道。
- 每个 source 都要记录执行状态：`attempted`、`blocked`、`zero_yield`、`not_attempted`。
- evidence 推荐包含 `source_attempts` 和 `attempted_queries`；缺失时 CLI 会先 warning 并继续入库，但 HTML 会标记“计划未完整审计”。
- 页面阻断也要记录：登录墙、验证码、安全页、App 下载墙、字段不可见都写入 `url_class` / `reject_reasons`，不要静默丢弃。
- “全渠道”采用保守合规口径：公开租房平台、品牌公寓公开页、豆瓣/Wellcee 等公开社区可自动发现；小红书、公众号、微博、微信群、公司群、朋友圈只作为 `roadmap_not_enabled`、`user_authorized_only` 或 `policy_disabled`，不自动抓取。
- 实际执行少于计划时，要说明是未执行、零结果、页面阻断，还是政策禁用。

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

正常用户路径应直接运行：

```bash
python skills/last7days-rent/scripts/last7days_rent.py refresh --evidence <file>
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
- 顶部通用 `避坑指南` CTA，固定链接到 `https://nest-hub.eggcampus.com/`，文案不能绑定具体公司。
- 4 个 tab：`房源`、`下一步策略`、`来源覆盖`、`风险指南`。
- 可筛选房源卡片，卡片内不重复塞“下一步”，只保留比较信息、可信等级和风险标签。
- 明显的蓝色来源按钮，例如“打开豆瓣来源”“打开安居客来源”。
- 可信等级和风险标签。
- 独立的下一步策略：今天先做、按房源行动、7 天计划。
- 来源覆盖：计划、尝试、入池、详情页、阻断、未执行、政策禁用或需用户授权。
- 本地更新时间。

JSON 应包含：

- profile。
- search brief。
- runtime evidence。
- listing pool。
