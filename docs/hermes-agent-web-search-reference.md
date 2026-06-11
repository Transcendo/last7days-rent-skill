# Hermes Agent Web Search 调研与 last7days-rent-skill 接入指南

调研日期：2026-06-10

调研对象：

- 参考仓库：`/Users/annacheng/Documents/github/hermes-agent`
- 当前仓库：`/Users/annacheng/Documents/open-rent/last7days-rent-skill`

本文件只沉淀调研和指导，不包含本次实现改动。

## 结论摘要

Hermes Agent 之所以能在普通对话里直接完成 web search，不是因为它把“搜索某类业务信息”写进了某个 skill，而是因为它把 `web_search` 做成了模型每轮都能看到的工具 schema。用户在对话里提出检索需求时，模型可以直接调用 `web_search(query, limit)`，底层再由 provider registry 选择 Firecrawl、Tavily、Exa、Brave、SearXNG、DuckDuckGo 等后端。

`last7days-rent-skill` 当前已经有一条业务内置的搜索链路：`profile/CLI 参数 -> SearchPlan -> provider_queries -> SearchLead -> promotion gate -> ListingItem -> report`。这条链路的问题不在 promotion 和报告，而在入口太像独立 CLI：它没有利用 agent runtime 已经配置好的对话式 `web_search` 工具，也没有一个“把外部 web_search 结果导入 SearchLead”的稳定接口。

建议下一步先补最小桥接层：允许 skill 在对话中优先使用 runtime 原生 `web_search` 获取 `{title, url, description, position}`，再把结果转换为 `SearchLead`，继续复用当前 P0 allowlist、rental semantics、contactability-first 和 evidence package。不要先做大规模爬虫，也不要把搜索摘要直接当成真实房源事实。

## Hermes Agent 的实现方式

### 1. `web_search` 是模型工具，不是业务脚本

Hermes 的 `toolsets.py` 把 `web_search` 和 `web_extract` 放进核心工具列表，并提供 `web` 与 `search` 两个工具集：

- `_HERMES_CORE_TOOLS` 包含 `web_search`, `web_extract`。
- `TOOLSETS["web"]` 暴露搜索和抽取。
- `TOOLSETS["search"]` 只暴露搜索。
- ACP/API Server 等完整工具集也包含 `web_search`。

关键路径：

- `toolsets.py:31`
- `toolsets.py:93`
- `toolsets.py:99`
- `toolsets.py:350`

这意味着只要当前平台启用了对应工具集，模型在普通对话轮次中就能看到 `web_search` 的函数 schema，并自行决定是否调用。

### 2. 工具 schema 和 handler 在 `tools/web_tools.py`

Hermes 的 `WEB_SEARCH_SCHEMA` 定义了模型可调用参数：

- `query: string`
- `limit: integer`

描述中明确说 query 会直接传给配置的后端，并允许 `site:domain`、`filetype:`、精确短语等搜索操作符。随后通过 `registry.register(name="web_search", toolset="web", ...)` 注册到工具系统。

关键路径：

- `tools/web_tools.py:1317`
- `tools/web_tools.py:1356`

注册时有两个重要设计：

- `handler` 指向 `web_search_tool(...)`。
- `check_fn=check_web_api_key`，没有可用 provider 时工具不会无条件出现在模型工具表里。

这就是“对话式搜索能工作”的核心：用户不是调用 CLI，模型是在对话中调用工具。

schema 注册后还会继续走标准模型工具装配链路：

```text
tools/web_tools.py registry.register(...)
-> toolsets.py 选择 web/search toolset
-> model_tools.get_tool_definitions()
-> tools.registry.get_definitions()
-> check_web_api_key() 过滤可用性
-> agent 初始化写入 agent.tools
-> transport 请求模型时携带 tools/function schema
```

这层链路说明：Hermes 的搜索入口是模型协议层的一等工具，和用户是否知道底层 provider 无关。用户只要在对话里提出“帮我搜近 7 天五角场租房”，模型就可以自然发起 `web_search` function call。

### 3. `web_search_tool` 只是调度器

`web_search_tool(query, limit)` 自己不关心具体 provider 的 API shape。它的流程是：

1. 规整 `limit`。
2. 检查中断。
3. 调 `_ensure_web_plugins_loaded()`，确保 bundled web provider plugin 已注册。
4. 读取 `web.search_backend` / fallback backend。
5. 从 `agent.web_search_registry` 找 active search provider。
6. 调 `provider.search(query, limit)`。
7. 返回统一 JSON 字符串。

关键路径：

- `tools/web_tools.py:758`
- `tools/web_tools.py:787`
- `tools/web_tools.py:843`
- `tools/web_tools.py:853`
- `tools/web_tools.py:861`
- `tools/web_tools.py:874`

统一返回格式大致是：

```json
{
  "success": true,
  "data": {
    "web": [
      {
        "title": "string",
        "url": "string",
        "description": "string",
        "position": 1
      }
    ]
  }
}
```

失败时返回：

```json
{
  "success": false,
  "error": "..."
}
```

### 4. Provider 是插件化的窄接口

Hermes 把 provider 接口抽成 `WebSearchProvider`：

- `name`
- `display_name`
- `is_available()`
- `supports_search()`
- `supports_extract()`
- `search(query, limit)`
- `extract(urls, **kwargs)`
- `get_setup_schema()`

关键路径：

- `agent/web_search_provider.py:63`
- `agent/web_search_provider.py:90`
- `agent/web_search_provider.py:99`
- `agent/web_search_provider.py:116`
- `agent/web_search_provider.py:160`

这个接口有两个值得借鉴的约束：

- `is_available()` 必须是便宜检查，不能做网络请求。
- 每个 provider 都归一到同一个响应 shape，工具 wrapper 不需要知道 Tavily、Brave、Exa 的差异。

### 5. Provider registry 负责选择后端

Hermes 的 `agent/web_search_registry.py` 维护 provider map，并按以下顺序选择 active provider：

1. `web.search_backend` / `web.extract_backend`
2. `web.backend`
3. 只有一个可用 provider 时直接使用
4. legacy preference：`firecrawl -> parallel -> tavily -> exa -> searxng -> brave-free -> ddgs`
5. 没有可用 provider 时返回 None，由工具给出 setup 提示

关键路径：

- `agent/web_search_registry.py:48`
- `agent/web_search_registry.py:122`
- `agent/web_search_registry.py:133`
- `agent/web_search_registry.py:181`
- `agent/web_search_registry.py:222`

这里的关键不是 provider 顺序本身，而是“显式配置优先、自动发现兜底、不可用时给明确错误”。

### 6. Provider 具体实现很薄

Brave provider：

- `BRAVE_SEARCH_API_KEY`
- GET `https://api.search.brave.com/res/v1/web/search`
- 返回 `title/url/description/position`
- search-only，不支持 extract

关键路径：

- `plugins/web/brave_free/provider.py:33`
- `plugins/web/brave_free/provider.py:50`
- `plugins/web/brave_free/provider.py:60`
- `plugins/web/brave_free/provider.py:123`

Tavily provider：

- `TAVILY_API_KEY`
- 支持 search 和 extract
- `/search` 结果归一成 `data.web`
- `/extract` 结果归一成 document list

关键路径：

- `plugins/web/tavily/provider.py:128`
- `plugins/web/tavily/provider.py:139`
- `plugins/web/tavily/provider.py:149`
- `plugins/web/tavily/provider.py:174`

DuckDuckGo provider：

- 使用 `ddgs` 包
- 不需要 API key
- 依赖是否安装由 `is_available()` 判断
- search-only

关键路径：

- `plugins/web/ddgs/provider.py:23`
- `plugins/web/ddgs/provider.py:39`
- `plugins/web/ddgs/provider.py:59`
- `plugins/web/ddgs/provider.py:95`

### 7. `execute_code` 也能间接调用 `web_search`

Hermes 的代码执行沙箱会生成 `hermes_tools.py` stub，其中包含：

- `web_search(query: str, limit: int = 5)`
- `web_extract(urls: list)`

关键路径：

- `tools/code_execution_tool.py:213`
- `tools/code_execution_tool.py:1699`

这解释了另一种顺滑体验：模型可以不把每一步搜索结果都展开进主上下文，而是在代码执行环境里通过 RPC 调 web 工具，做批量 query、筛选、整理，再把最终摘要返回。

需要注意的是，`execute_code` 里的 `web_search` 不是第二套搜索实现。Hermes 会根据当前 session 真实可用工具动态重建 `execute_code` schema；stub 通过 RPC 回到主进程，最终仍然走同一个 `web_search_tool -> provider.search()` 链路。也就是说，主对话工具和沙箱工具共享同一个 provider registry、同一个权限/可用性判断、同一个返回 shape。

### 8. Web 结果按不可信内容处理

Hermes 在工具结果回填模型消息时，会把 `web_search`、`web_extract`、browser 和 MCP 这类外部可控内容视为 untrusted tool result。这个设计值得 last7days 继承到产品语义里：搜索结果可以作为线索和 provenance，但不能作为系统指令，也不能直接填充价格、联系方式、仍在租等事实字段。

关键路径：

- `agent/tool_dispatch_helpers.py:325`
- `agent/tool_dispatch_helpers.py:353`

## last7days-rent-skill 当前搜索链路

当前仓库的搜索链路已经有不少正确方向。

### 1. CLI 暴露 search 参数

`last7days_rent.py search` 支持：

- `--fixture`
- `--limit`
- `--office-anchor`
- `--city`
- `--budget-min`
- `--budget-max`
- `--days`
- `--providers`
- `--sources`

关键路径：

- `skills/last7days-rent/scripts/last7days_rent.py:51`
- `skills/last7days-rent/scripts/last7days_rent.py:134`

### 2. Profile/参数生成 SearchPlan

`build_search_plan()` 会从 profile 或一次性参数生成：

- `provider_queries`
- `source_queries`
- `commute_areas`

`_provider_queries_for_request()` 目前把选中的 listing source 转成 include domains，再生成统一 base query，例如“上海 五角场 租房 5200以内 近7天”。

关键路径：

- `skills/last7days-rent/scripts/lib/sources/query.py:33`
- `skills/last7days-rent/scripts/lib/sources/query.py:54`
- `skills/last7days-rent/scripts/lib/sources/query.py:82`
- `skills/last7days-rent/scripts/lib/sources/query.py:112`

### 3. Provider fanout 已经存在

当前实现内置了：

- Brave
- Tavily
- Exa

`fetch_search_leads(plan)` 会逐个 provider query 执行：

- 没 API key，记录 `<provider>_missing_api_key`
- 未知 provider，记录 `<provider>_unknown_provider`
- HTTP 错误，映射成稳定 warning
- 全部不可用，追加 `no_search_provider_available`

关键路径：

- `skills/last7days-rent/scripts/lib/search_providers/router.py:13`
- `skills/last7days-rent/scripts/lib/search_providers/router.py:20`
- `skills/last7days-rent/scripts/lib/search_providers/router.py:29`
- `skills/last7days-rent/scripts/lib/search_providers/router.py:74`

Provider mapper 会把各家响应转成 `SearchLead`：

- Brave：`skills/last7days-rent/scripts/lib/search_providers/brave.py:45`
- Tavily：`skills/last7days-rent/scripts/lib/search_providers/tavily.py:42`
- Exa：`skills/last7days-rent/scripts/lib/search_providers/exa.py:46`

### 4. SearchLead promotion gate 是正确的业务边界

`promote_search_leads()` 当前只允许：

- URL 域名命中 P0 allowlist：`ke.com/lianjia.com/fang.com/wellcee.com`
- URL 是可打开的 http/https
- title/snippet/highlights/text_excerpt 有租房语义

通过后才生成低置信 L1 `ListingItem`，并把原始 URL 作为 platform contact。

关键路径：

- `skills/last7days-rent/scripts/lib/search_providers/promote.py:12`
- `skills/last7days-rent/scripts/lib/search_providers/promote.py:50`
- `skills/last7days-rent/scripts/lib/search_providers/promote.py:80`
- `skills/last7days-rent/scripts/lib/search_providers/promote.py:96`

这个边界必须保留。Search API snippet 只能证明“发现了线索”，不能证明价格、发布时间、联系方式或仍在租。

### 5. Pipeline 和报告已经能保留搜索证据

`run_search()` 会把 live search 的 provider coverage、search leads、promoted/rejected leads 写入 HTML report 和 JSON evidence package。

关键路径：

- `skills/last7days-rent/scripts/lib/pipeline.py:261`
- `skills/last7days-rent/scripts/lib/pipeline.py:278`
- `skills/last7days-rent/scripts/lib/pipeline.py:299`
- `skills/last7days-rent/scripts/lib/pipeline.py:311`

报告渲染里也有：

- Search Provider Coverage
- 搜索发现线索
- Warnings
- 联系路径

关键路径：

- `skills/last7days-rent/scripts/lib/render.py:93`
- `skills/last7days-rent/scripts/lib/render.py:100`
- `skills/last7days-rent/scripts/lib/render.py:113`
- `skills/last7days-rent/scripts/lib/render.py:124`

## 最大缺口

当前最大缺口不是“没有搜索 provider 代码”，而是缺一个 agent runtime 入口。

Hermes 的路线是：

```text
用户自然语言 -> 模型看到 web_search schema -> 调 web_search -> provider registry -> 标准 web result
```

当前 last7days 的路线是：

```text
用户/skill 指令 -> 本地 CLI search -> 内置 provider fanout -> SearchLead -> ListingItem
```

因此，当本地没有 Brave/Tavily/Exa key，或者运行环境本身已经有可用 `web_search` 工具时，last7days 不能自然复用 runtime 搜索能力。它只能报告 `*_missing_api_key` 和 `no_search_provider_available`。

更直接地说：Hermes 的搜索能力是“agent 工具能力”，last7days 当前的搜索能力是“CLI 内部 HTTP client 能力”。这两者之间缺一个 `web_search result -> SearchLead` 的导入/适配层。

## 可以参考 Hermes 的设计

### 借鉴 1：标准化 web result shape

建议接受 Hermes shape 作为外部搜索结果输入：

```json
{
  "success": true,
  "data": {
    "web": [
      {
        "title": "上海五角场租房...",
        "url": "https://www.wellcee.com/rent-apartment/...",
        "description": "五角场租房，平台联系...",
        "position": 1
      }
    ]
  }
}
```

映射到 `SearchLead`：

- `provider = "runtime_web_search"` 或真实 provider 名
- `query = agent 传入的查询词`
- `rank = position`
- `title = title`
- `url = url`
- `snippet = description`
- `domain = domain_for_url(url)`
- `raw = {"source_shape": "hermes.web_search", ...}`

这样 Hermes/Codex/Claude Code 等 runtime 只要能给出类似结构，都能接入，不必把每个 runtime 的工具系统写进业务核心。

### 借鉴 2：把 provider 可用性当成能力检查

当前 `provider_api_key()` 可以继续存在，但建议后续把 provider 抽象成统一对象：

```text
name
display_name
is_available()
supports_search()
search(query) -> SearchLead[]
```

这样内置 API provider、fixture provider、runtime web_search import provider 可以共用 registry。Hermes 的 ABC 很完整，但 last7days 不需要复制 `extract`、plugin discovery、setup UI 的全部复杂度。

### 借鉴 3：显式配置优先，自动发现兜底

建议搜索 provider 选择顺序改成：

1. 用户 CLI 显式 `--providers`
2. profile/source preferences
3. 环境中可用 API key
4. runtime web_search import 结果
5. fixture，仅限 `--fixture`

这样用户明确指定 provider 时可以得到明确错误，自动模式则尽量找到一条可用搜索腿。

### 借鉴 4：搜索和抽取分层

Hermes 把 `web_search` 和 `web_extract` 分开。last7days 也应继续分层：

- 默认：只做 `web_search` 发现 SearchLead。
- 可选核验：只对少量 promoted URL 做 extract/open URL 验证。
- 禁止默认：批量 crawl、登录态、cookie、绕验证码。

这与当前 `docs/source-policy.md` 的边界一致。

### 借鉴 5：失败是结果的一部分

Hermes provider 失败返回 `{success:false,error}`，last7days 当前也有 warnings。下一步应把 runtime web_search 的失败也纳入 `search_provider_coverage`，例如：

- `runtime_web_search_unavailable`
- `runtime_web_search_failed`
- `runtime_web_search_empty`
- `runtime_web_search_result_parse_failed`

不要把空结果翻译成“没有房源”。

## 不建议照搬的部分

不要直接复制 Hermes 的完整 plugin 系统。Hermes 是通用 agent 平台，插件发现、工具配置 UI、toolset、sandbox RPC 都是平台层能力。last7days 是一个租房 skill，本轮目标是把搜索腿接上，不需要引入整套工具注册中心。

不要直接把 Firecrawl/Tavily extract 变成默认房源采集。搜索摘要和页面抽取都可能被 prompt injection、广告页、过期索引、反爬页面污染。默认只能发现入口，正式候选仍要过 P0 allowlist、租房语义和联系路径约束。

不要用 LLM summary 填价格、地址、联系方式、发布时间。Hermes 的 `web_extract` 会为了上下文压缩做摘要，但 last7days 的事实字段必须来自可追溯 URL、结构化字段、用户授权导入或用户后续确认。

## 推荐接入路线

### Phase 1：补 runtime web_search 导入桥

新增一个只处理标准 search result 的桥接能力，建议命名为：

```text
search --websearch-json <path>
```

或：

```text
search import-web-results --provider runtime_web_search --query "..." --input <path>
```

输入兼容 Hermes `web_search` shape。输出进入当前 pipeline：

```text
Hermes web_search result
-> RuntimeSearchResult parser
-> SearchLead[]
-> promote_search_leads()
-> normalize/dedupe/score/rerank
-> HTML/JSON report
```

最小实现不需要联网，也不需要知道 Hermes 内部 provider。只要 agent 在对话里能拿到 web_search JSON，就能喂给 last7days。

### Phase 2：更新 skill 使用流程

`skills/last7days-rent/SKILL.md` 后续可以加入运行时策略：

1. 如果当前 agent runtime 有原生 `web_search` 工具，先用 `web_search` 做 discovery。
2. 每个目标来源至少一条 query，不要只用一个宽泛 query。
3. 将结果保存为临时 JSON，再调用 CLI 导入。
4. CLI 继续负责 promotion、去重、风险、联系路径和报告。
5. 如果 runtime 无 `web_search`，再回退到 CLI 内置 Brave/Tavily/Exa provider。

推荐 query 模板：

```text
site:wellcee.com/rent-apartment 上海 五角场 租房 5200以内 近7天
site:zu.fang.com/chuzu 上海 五角场 出租 5200以内
site:ke.com/zufang 上海 五角场 租房 5200以内
site:lianjia.com/zufang 上海 五角场 租房 5200以内
```

注意：不同搜索后端对 `site:` 和 freshness 支持不一致，所以结果必须带 provider/query/rank provenance。

### Phase 3：收敛 provider 抽象

把当前 `PROVIDER_CALLS` 字典演进成轻量 registry：

```text
SearchProvider:
  name
  is_available()
  build_queries(request/profile)
  search(query) -> list[SearchLead]
```

Provider 类型至少包括：

- `brave`
- `tavily`
- `exa`
- `runtime_web_search_import`
- `fixture`

这能把“有 API key 的本地搜索”和“agent 已经搜索过的结果导入”放到同一套 coverage/report 模型里。

### Phase 4：少量 URL 核验，不做默认 crawl

当 SearchLead promoted 后，可以增加显式开关：

```text
--verify-promoted-urls
```

只对 top N promoted URL 做轻量核验，并遵守：

- 不使用 cookie。
- 不绕验证码。
- 不保存 secret。
- 请求失败只写 warning。
- 抽取内容不能把 L1 自动提升为 L3。

## 下一步验收清单

搜索腿接上至少要满足：

- 无 Brave/Tavily/Exa key 但 runtime 已有 `web_search` 结果时，可以生成 `SearchLead` 和报告。
- `SearchLead` 导入结果仍经过 P0 allowlist 和 rental semantics gate。
- 未通过 gate 的结果出现在 rejected/search leads，不进入核心短名单。
- 每个 promoted listing 至少有 source URL 作为 platform contact。
- 报告展示 query、provider、rank、promotion/rejection reason。
- provider/runtime 失败进入 warnings，不伪造候选。
- fixture 覆盖 Hermes shape，测试不触网。

建议新增测试：

- `test_runtime_web_search_shape_maps_to_search_leads`
- `test_runtime_web_search_import_uses_promotion_gate`
- `test_runtime_web_search_import_records_rejections`
- `test_no_api_key_but_imported_web_results_can_produce_report`
- `test_runtime_web_search_failure_becomes_warning`

## 对当前实现的具体建议

短期不要删当前 Brave/Tavily/Exa 实现。它们已经能作为本地 fallback，并且已有 tests/fixtures 覆盖。优先补外部结果导入，能最快验证“对话搜索 -> 房源短名单”的闭环。

中期再考虑把 provider 代码从函数式 fanout 收敛成轻量 provider registry。这个重构应服务于 runtime import、fixture、本地 API provider 的统一 coverage，而不是为了仿 Hermes 做插件系统。

长期如果要把 last7days 放进 Hermes 生态，可以再考虑 Hermes-native skill flow：让 skill 指令明确要求 agent 先调用 `web_search`，再调用 last7days CLI 做业务筛选。这样 Hermes 负责通用搜索能力，last7days 负责租房领域判断和报告交付。
