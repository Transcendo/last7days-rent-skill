# Anchor Pack 与 POC 范围说明

日期：2026-06-13

状态：产品与架构方向草案

## 一句话结论

`last7days-rent-skill` 的差异化能力不应该是“自己再做一套搜索 provider”，而应该是：

> 面向一线/新一线城市互联网大厂租房场景，沉淀办公锚点、通勤圈、片区经验和搜索策略，再把 Codex / Claude Code 等 Agent runtime 搜到的公开房源线索，转成本地可更新、可筛选、适配用户 profile 的 HTML 房源候选池。

换句话说：

- Web search 是 agent runtime 的能力。
- Anchor Pack、evidence ingest、租房排序、隐私边界和本地 HTML 房源池，才是这个 skill 的能力。

## 为什么 Anchor Pack 是亮点

如果用户裸用 web search，通常只会搜：

```text
北京 京东总部 一居室 5000 租房
```

这类搜索能拿到一些结果，但召回和排序都不稳定。原因是租房搜索不是只知道公司名就够了，还需要知道：

- 公司真实办公锚点在哪里。
- 最近地铁站、骑行圈、公交圈是什么。
- 哪些小区/公寓是这个办公点员工常看的。
- 哪些片区是“近但贵”、哪些是“远一点但性价比高”。
- 哪些关键词能搜到房源，哪些关键词会引出大量中介广告或无关内容。
- 预算段和户型在这个办公圈是否现实。
- 哪些来源适合做 L0 线索，哪些来源需要谨慎核验。

这些知识不是 web search 工具天然知道的。它需要一个租房 domain layer。

因此，Anchor Pack 应该成为本项目的核心资产。

## Anchor Pack 的定义

Anchor Pack 是面向互联网公司办公点的租房搜索与通勤知识包。

它不是房源数据库，也不是静态小区推荐榜。它是让 agent 更会搜、更会问、更会排序的上下文。

建议最小结构：

```json
{
  "anchor_id": "beijing-jd-hq-yizhuang",
  "city": "北京",
  "company": "京东",
  "campus_name": "京东总部",
  "aliases": ["京东总部", "JD总部", "京东亦庄总部"],
  "office_anchor": {
    "address_text": "待来源核验后的办公地址",
    "nearest_metro": ["经海路"],
    "source_urls": [],
    "confidence": "medium",
    "updated_at": "2026-06-13"
  },
  "commute_zones": [
    {
      "zone_id": "walk_or_bike",
      "label": "步行/骑行优先",
      "keywords": ["经海路", "锋创科技园"],
      "tradeoff": "通勤最短，但公寓和商住属性需要重点核验"
    },
    {
      "zone_id": "value_regular_residential",
      "label": "正规住宅性价比",
      "keywords": ["次渠南", "次渠嘉园", "次渠锦园"],
      "tradeoff": "租金更稳，通勤需要骑行或地铁/公交衔接"
    }
  ],
  "query_templates": [
    "{city} {company} {campus_name} 附近 一居室 {budget_max}以内 租房",
    "{city} {metro_or_zone} 一居室 {budget_max} 租房",
    "site:douban.com/group {campus_name} 整租 一居",
    "site:58.com {zone_keyword} 一居室 租房"
  ],
  "risk_notes": [
    "低价开间可能不是完整一居",
    "步行近房源需核验商水商电和居住登记",
    "公开小组标题中的手机号不进入公开报告"
  ]
}
```

## Anchor Pack 应该覆盖什么

POC 不需要一开始覆盖全国。建议先覆盖一线/新一线中互联网公司密度高、租房需求强的城市。

优先级建议：

| 优先级 | 城市 | 目标 |
| --- | --- | --- |
| P0 | 北京、上海、深圳、杭州 | 验证核心互联网办公锚点和租房圈层 |
| P1 | 广州、成都、南京、武汉 | 扩展新一线样本 |
| P2 | 西安、苏州、长沙、重庆、合肥 | 作为后续模板化扩展 |

P0 城市每个先覆盖 3-5 个典型办公锚点即可，不要一开始追求全量。

每个锚点要先沉淀这些内容：

- 公司/园区名称和别名。
- 办公点地址或搜索锚点。
- 最近地铁站/公交站/常用片区。
- 推荐搜索关键词。
- 候选小区/片区关键词。
- 预算经验区间。
- 风险提示。
- 来源 URL、更新时间、置信度。

## Anchor Pack 的边界

Anchor Pack 不能变成“过期租房攻略”。

必须遵守这些边界：

- 具体地址、地铁站、小区经验必须有来源或标记为待核验。
- 任何锚点信息都需要 `updated_at` 和 `confidence`。
- 不承诺某小区一定有房。
- 不承诺某价格一定能租到。
- 不保存个人发帖人身份。
- 不保存私域群聊原文。
- 不把用户个人 profile 写入公共 anchor pack。

Anchor Pack 只提供搜索和排序上下文，不能替代当前 web search 和现场看房核验。

## POC 目标

完整愿景是帮助用户 7 天内完成租房全链路。但当前 POC 不应该覆盖签约、付款、合同审查和线下看房执行。

当前 POC 的目标是：

> 帮助用户在 Codex / Claude Code 等 Agent runtime 里，通过全渠道公开 web search 获取房源线索，并沉淀为一份本地可更新、适合自己 profile 的 HTML 房源汇总列表。

这个目标比“7 天完成租房”窄，但它验证了最关键的一段链路：

```text
用户需求
  -> profile
  -> anchor pack
  -> search brief
  -> agent web search
  -> evidence ingest
  -> ranking / risk / trust level
  -> local HTML listing pool
  -> 用户反馈更新
```

## POC 的输入与输出

### 输入

用户自然语言需求：

```text
北京京东总部，一居室，5000 RMB 以内。
```

工具应整理为 profile：

```json
{
  "city": "北京",
  "office_anchor": "北京京东总部",
  "budget_max": 5000,
  "min_bedrooms": 1,
  "preferred_commute_minutes": null,
  "hard_filters": []
}
```

### 中间产物

工具生成 search brief：

- 办公锚点。
- 推荐通勤圈。
- 推荐片区关键词。
- 推荐来源。
- 查询模板。
- 排除词。
- evidence 收集字段。
- 隐私规则。

Agent runtime 使用自己的 web search / browser 能力执行搜索。

搜索结果沉淀为 evidence input：

```json
{
  "source_url": "https://example.com/listing/1",
  "source_name": "58",
  "title": "次渠锦园北区精装一居室",
  "snippet": "1室 60平 3950元/月 次渠南地铁站附近",
  "observed_at": "2026-06-13T10:00:00+08:00",
  "visible_fields": {
    "price_text": "3950元/月",
    "area_text": "60平",
    "layout_text": "1室",
    "community": "次渠锦园北区",
    "district_hint": "次渠南"
  },
  "contact_path": {
    "type": "platform_entry",
    "entry_url": "https://example.com/listing/1"
  },
  "trust_level": "L0",
  "agent_notes": ["待核验民水民电", "待核验是否包物业取暖"]
}
```

### 输出

POC 最终输出是一份本地 HTML 房源汇总列表。

HTML 必须支持：

- 按预算筛选。
- 按片区/小区筛选。
- 按来源筛选。
- 按可信等级筛选。
- 按风险标签筛选。
- 标记联系状态。
- 记录下一步动作。
- 合并新一轮搜索结果。
- 保留来源链接和 observed time。

建议同时输出：

- Markdown report。
- JSON evidence package。
- 本地 profile 摘要。
- 搜索 brief 记录。

## “全渠道”的定义

POC 阶段的“全渠道”不是任意抓取互联网内容，而是由 agent runtime 使用公开 web search 覆盖尽可能多的公开来源。

允许的 POC 渠道：

- 58、安居客。
- 贝壳、链家。
- 自如、我爱我家。
- 豆瓣公开小组。
- Wellcee 等公开页面。
- 乐乎、泊寓、蜂客、城家、有巢等品牌公寓公开页面。
- NestHub 指南和本地 NestHub 内容只作为先验知识，不作为实时房源。
- 官方核验或地图公开信息。

需要谨慎的渠道：

- 小红书公开内容：可作为 L0 搜索线索，但不要绕登录和反爬。
- 微博公开内容：可作为 L0 搜索线索，但不要自动私信或抓个人隐私。

不在 POC 默认范围：

- 微信群。
- 朋友圈。
- 公司群。
- 校友群。
- 中介私聊记录。
- 需要登录、cookie、token 或验证码绕过的内容。

这些内容只能通过用户授权导入进入工具，而且报告中仍要做隐私处理。

## HTML 房源池的本地更新模型

POC 不能只生成一次性报告。它应该生成一个可持续维护的本地房源池。

建议状态模型：

| 状态 | 含义 |
| --- | --- |
| `new` | 新发现，还没看 |
| `shortlisted` | 用户感兴趣 |
| `contacted` | 已联系 |
| `scheduled` | 已约看 |
| `viewed` | 已看房 |
| `rejected` | 用户排除 |
| `stale` | 长时间未更新或疑似已下架 |
| `leased` | 用户确认已出租 |

每次新搜索后，工具应：

- 用 canonical URL 去重。
- 用小区 + 价格 + 面积 + 标题相似度做弱去重。
- 保留旧的用户反馈状态。
- 更新 `last_seen_at`。
- 新增 `observations`，而不是覆盖旧证据。
- 对疑似下架或长期未见的房源标记 `stale`。

## 信任等级在 POC 中的用法

POC 不追求“验真”，但必须避免误导。

| 等级 | POC 展示方式 |
| --- | --- |
| L0 | 搜索线索，必须展示“待核验” |
| L1 | 单源页面打开后结构化，可进入候选列表 |
| L2 | 多源重复或多次观测，可提升排序 |
| L3 | 用户联系或看房确认，可作为重点推荐 |

关键约束：

- Web search snippet 只能产生 L0。
- Agent 打开公开页面并摘录字段后，最多 L1。
- 多源重复可以 L2，但仍不是“已验真”。
- L3 只能来自用户反馈。

## POC 成功标准

以“北京京东总部，一居室，5000 元以内”为例，POC 成功标准如下：

1. 工具能基于 Anchor Pack 生成经海路、次渠南、次渠嘉园、次渠锦园、锋创科技园等搜索方向。
2. Agent 能按 search brief 使用 runtime web search 获取公开房源线索。
3. 工具能 ingest 至少 10 条公开来源 evidence。
4. 工具能生成本地 HTML 房源列表。
5. HTML 每条房源至少包含来源、价格、面积/户型可见字段、片区、可信等级、风险和下一步动作。
6. HTML 支持筛选和人工状态更新。
7. 新一轮搜索可以 merge 到同一房源池，而不是生成孤立报告。
8. 报告不暴露原发帖人身份，不保存 secret，不补全未知字段。

## 近期实现建议

建议拆成 4 个小阶段。

### 阶段 1：文档与 schema

- 新增 Anchor Pack schema。
- 新增 POC scope 文档。
- 新增 agent evidence schema。
- 明确 `search --provider-*` 是 legacy/advanced。

### 阶段 2：Search Brief

- 新增 `plan` 命令。
- 输入 profile。
- 输出 agent 可执行的搜索 brief。
- 内置 1-2 个样例 Anchor Pack，例如北京京东总部。

### 阶段 3：Evidence Ingest

- 新增 `ingest` 命令。
- 读取 agent 搜索整理出的 JSON。
- 生成候选房源池。
- 保留 trust level、risk、source provenance。

### 阶段 4：Local HTML Pool

- 新增或强化 HTML render。
- 支持筛选、排序、状态标记。
- 支持增量 merge。
- 支持导出 Markdown / JSON。

## 与 7 天全链路目标的关系

“7 天内完成租房”仍然是长期产品目标。

但 POC 阶段先交付这个关键闭环：

```text
找得到 -> 看得懂 -> 排得出优先级 -> 能持续更新 -> 能指导下一步联系和看房
```

签约、付款、合同审查、看房排程自动化，可以后续再做。当前最重要的是证明：

- Anchor Pack 能显著提升搜索质量。
- Agent runtime 的 web search 能覆盖公开渠道。
- 工具能把零散搜索结果变成可执行的本地租房工作台。

这才是 `last7days-rent-skill` 在 Codex / Claude Code 生态中的合理位置。
