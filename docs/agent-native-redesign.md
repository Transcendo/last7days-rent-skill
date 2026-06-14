# Agent-Native 租房工具改造方向

日期：2026-06-13

## 背景判断

`last7days-rent-skill` 当前走到了一个不经济的方向：它把租房工具的主干能力放在自建 search/extract provider 上，默认围绕 Brave、Exa、Tavily、DDGS 做搜索发现和详情增强。这对独立 CLI 或无人值守任务有一定意义，但对 Codex、Claude Code 这类 agent runtime 来说，方向偏重了。

原因很直接：这些 runtime 本身已经有 web search、网页打开、浏览器检查、人工判断和来源引用能力。租房任务真正困难的部分，不是“再造一个搜索引擎 provider 层”，而是把 agent 搜到的公开线索变成可行动、可追踪、可复用、隐私边界清晰的租房计划。

因此，本项目应从“自带搜索 provider 的租房爬取工具”改造为“Agent-native 租房规划与 evidence 处理工具”。

## 新定位

这个工具的核心定位是：

> 帮助 agent 把公开搜索结果、用户授权文本和用户反馈，结构化为可筛选的租房候选列表、可信等级、下一步核验动作和最终报告。

它不应默认承担搜索引擎职责。默认搜索发现应交给 agent runtime 自带的 web search 或浏览器能力完成。

工具应专注做这些事情：

- 维护用户租房 profile：办公点、预算、户型、通勤、偏好、排除项。
- 生成高质量 web search 查询计划，指导 agent 搜什么、按什么顺序搜。
- 接收 agent 搜索后的 evidence 输入，包括 URL、标题、摘要、可见字段、来源时间和截图/摘录备注。
- 对房源线索做去重、排序、预算匹配、通勤匹配、户型匹配和风险标记。
- 明确 L0-L3 可信等级，避免把搜索片段写成“已验真房源”。
- 处理隐私和联系方式边界：不暴露原发帖人身份，不保存 cookie/token，但保留公开房源允许展示的联系路径。
- 输出 Markdown、HTML、JSON evidence package，方便用户看房、复盘和继续追加。
- 接收用户反馈，把“已联系、可看房、已出租、假房源、费用不透明”等信息沉淀回排序逻辑。

## 明确不做什么

默认产品路径不再做这些事情：

- 不默认要求 `BRAVE_SEARCH_API_KEY`、`EXA_API_KEY` 或 `TAVILY_API_KEY`。
- 不把 Exa/Tavily/Brave/DDGS 作为用户成功使用工具的前置条件。
- 不把贝壳、58、安居客、豆瓣等动态网页做成稳定爬虫承诺。
- 不绕验证码、不登录、不要求 cookie、不保存登录态。
- 不用模型补全未知租金、地址、面积、押金、入住时间或联系方式。
- 不把 web search snippet 直接升级成正式 `ListingItem` 或“已确认房源”。

## 推荐工作流

新的默认工作流应是：

```text
用户提出租房目标
  -> 工具生成 profile 和 search brief
  -> agent 使用自带 web search / 浏览器搜索公开来源
  -> agent 把搜索结果整理成 evidence input
  -> 工具 ingest evidence
  -> 工具去重、打分、风险标记、生成 L0/L1 列表
  -> 工具 render Markdown / HTML / JSON
  -> 用户联系或看房后记录 feedback
  -> 工具根据反馈升级 L2/L3 或降权排除
```

示例：

```text
用户：北京京东总部，一居室，5000 元以内。

工具：
1. 识别办公锚点和通勤圈。
2. 生成搜索 brief：经海路、次渠南、次渠嘉园、次渠锦园、锋创科技园、东惠家园等关键词。
3. 要求 agent 用 web search 查 58、安居客、豆瓣、贝壳、自如等公开结果。
4. ingest 搜索结果。
5. 输出可筛选 HTML 候选列表和看房核验清单。
```

## 新命令设计

建议把 CLI 改造成四类命令。

### `profile`

继续保留。负责本地私有画像。

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile init \
  --office-anchor "北京京东总部" \
  --city 北京 \
  --budget-max 5000 \
  --min-bedrooms 1
```

### `plan`

新增默认入口之一。生成 agent 可执行的搜索计划，而不是直接调用 provider。

```bash
python skills/last7days-rent/scripts/last7days_rent.py plan \
  --office-anchor "北京京东总部" \
  --city 北京 \
  --budget-max 5000 \
  --min-bedrooms 1
```

输出内容：

- 搜索目标摘要。
- 通勤锚点和候选片区。
- 推荐查询词列表。
- 推荐来源顺序。
- 排除查询词。
- evidence 收集字段要求。
- 隐私和联系方式处理规则。

### `ingest`

新增核心入口。读取 agent 整理出的 evidence 文件。

```bash
python skills/last7days-rent/scripts/last7days_rent.py ingest \
  --input evidence.json \
  --output-dir ~/.last7days-rent/reports
```

`ingest` 负责：

- 校验 evidence schema。
- 规范化 URL 和来源。
- 提取租金、面积、户型、片区、更新时间等可见字段。
- 识别公开联系路径和平台入口。
- 去重。
- 打分和风险标记。
- 生成 `CandidateLead` 或 `ListingItem`。

### `render`

新增核心入口。把当前候选池输出成报告。

```bash
python skills/last7days-rent/scripts/last7days_rent.py render \
  --format html \
  --latest
```

输出内容：

- Markdown report。
- HTML 候选列表。
- JSON evidence package。
- 看房优先级。
- 核验清单。
- blocked/unknown 字段说明。

### `search`

保留但降级。

`search --provider-*` 不应再是 README 和 SKILL 的默认路径。它应标记为 legacy 或 experimental，仅用于以下场景：

- 无 agent web search 能力的纯 CLI 环境。
- 定时任务或无人值守 monitor。
- 本地 smoke test。
- 用户明确要求使用 Exa/Tavily/Brave provider。

## Evidence 输入格式

建议新增 `agent_search_evidence` schema。

最小字段：

```json
{
  "query_context": {
    "city": "北京",
    "office_anchor": "北京京东总部",
    "budget_max": 5000,
    "min_bedrooms": 1,
    "generated_at": "2026-06-13T10:00:00+08:00"
  },
  "items": [
    {
      "source_url": "https://example.com/listing/1",
      "source_name": "58",
      "source_tier": "public_web",
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
      "agent_notes": [
        "待核验是否民水民电",
        "待核验是否包物业取暖"
      ]
    }
  ]
}
```

设计原则：

- `source_url` 必须存在。
- `observed_at` 必须存在，用于处理房源时效。
- 搜索片段里的字段只能进入 `visible_fields`，不能标记为已验真。
- 私人手机号、微信号等如果来自公开房源页面且属于房源联系路径，可进入 `contact_path`；如果是发帖人身份或私域来源，不进入公开报告。
- cookie、token、session、authorization 等字段必须拒绝写入。

## 可信等级保留并强化

可信等级是这个项目最值得保留的抽象。

| 等级 | 含义 | 来源 |
| --- | --- | --- |
| L0 | 搜索发现线索，未打开或未结构化核验 | agent web search、搜索结果、平台列表 |
| L1 | 单源结构化，有 URL 和可行动联系路径 | agent 打开页面后摘录、用户授权文本、公开页面字段 |
| L2 | 多源佐证或同房源重复出现，关键字段基本一致 | 多平台重复、同 URL 多次观测、来源交叉验证 |
| L3 | 用户明确联系确认仍在租、可看房或已实看 | 用户反馈 |

约束：

- L0 可以展示，但必须写“待核验”。
- L1 不能写成“已验真”。
- L2 可以进入优先短名单，但仍需看房和合同核验。
- L3 只能来自用户反馈，不能由搜索、provider 或模型推断产生。

## 隐私与联系方式边界

租房工具必须同时满足两个目标：保护来源隐私，以及让用户真的能联系房源。

保留：

- 平台详情页入口。
- 公开房源页明确展示的联系按钮或联系说明。
- 用户授权导入文本中的联系方式。
- 用户自己记录的联系反馈。

不保留到公开报告：

- 原发帖人的真实身份。
- 与房源联系无关的个人主页、昵称、头像、社交身份。
- 私域群聊上下文。
- cookie、token、session、authorization、登录态。
- 从非授权私域内容中抽取的私人联系方式。

报告中应优先展示“联系路径”，而不是展示个人身份。

## 模块改造建议

建议保留：

- `profile_schema.py`
- `profile_store.py`
- `commute_plan.py`
- `scoring.py`
- `dedupe.py`
- `risk.py`
- `contact.py`
- `privacy.py`
- `render.py`
- `feedback.py`
- `schema.py` 中的 `CandidateLead`、`ListingItem`、`SourceCandidate`、可信等级相关结构

建议新增：

- `agent_evidence.py`：读取和校验 agent 搜索 evidence。
- `search_brief.py`：生成 agent web search brief。
- `ingest.py`：把 evidence 转为候选和短名单。
- `html_render.py` 或强化现有 render：输出可筛选 HTML。

建议降级：

- `providers/`
- `acquisition/service.py`
- `docs/provider-architecture.md`
- CLI 中的 `search --provider-search` 和 `--provider-extract`

降级不是删除。它们可以保留为 legacy provider path，避免一次性破坏现有测试和后续无人值守场景。

## 文档改造建议

优先修改这些文档：

1. `README.md`
   - 开头改成 agent-native 定位。
   - 默认 quickstart 改成 `plan -> agent web search -> ingest -> render`。
   - provider 配置移到 legacy/advanced。

2. `skills/last7days-rent/SKILL.md`
   - 描述从“用 search provider 获取线索”改为“指导 agent 搜索，并处理 evidence”。
   - 使用原则加入：优先使用 runtime web search，不默认调用 provider。
   - CLI 示例更新为 `plan`、`ingest`、`render`。

3. `docs/provider-architecture.md`
   - 改名或补充说明为 legacy provider path。
   - 明确它不是默认 agent skill 路径。

4. 新增 `docs/evidence-schema.md`
   - 固化 `agent_search_evidence` 输入格式。

5. 新增或更新 `docs/user-guide.md`
   - 写一个完整例子：北京京东总部，一居室，5000 元以内。

## 代码迁移顺序

建议分 4 个小 PR 做。

### PR 1：文档和定位

- 新增本文档。
- 更新 README 和 SKILL 文案。
- 将 provider path 标记为 advanced/legacy。
- 不改行为，降低风险。

### PR 2：新增 plan 和 evidence schema

- 新增 `plan` 命令。
- 新增 `agent_search_evidence` schema。
- 新增 schema 单测。
- fixture 覆盖北京京东总部案例。

### PR 3：新增 ingest 和 render

- 新增 `ingest` 命令。
- ingest evidence 到 `CandidateLead` / `ListingItem`。
- 输出 Markdown / HTML / JSON。
- 保留隐私和联系方式测试。

### PR 4：降级 provider search

- README 默认路径移除 `search --provider-*`。
- `search` 标记为 legacy/experimental。
- provider 测试保留但从核心用户路径中移出。
- 清理 provider diagnostics 在主报告中的权重。

## 完成标准

改造完成后，用户应能这样使用：

1. 用户说：“北京京东总部，一居室，5000 以内。”
2. Agent 根据工具生成的 search brief 使用 runtime web search 找公开线索。
3. Agent 把搜索结果保存为 evidence。
4. 工具 ingest evidence 并输出 HTML 房源列表。
5. HTML 中每条房源都有价格、片区、来源、可信等级、风险和下一步核验动作。
6. 报告不暴露原发帖人身份，不保存 secret，不伪造未知字段。
7. 用户反馈后，工具能把房源升级为 L3 或降权排除。

这才是本项目应该交付的核心价值：不是“我也能搜”，而是“我能把 agent 搜到的东西变成一个真正可执行的租房工作流”。
