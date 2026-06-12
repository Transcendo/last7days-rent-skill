# Provider 架构说明

`last7days-rent-skill` 使用自有 search/extract provider 架构。Agent runtime 只需要调用 skill 或 CLI；具体搜索和抽取能力由本项目根据配置自动选择。

## 目标

```text
用户 profile
  -> 渠道/区域查询生成
  -> SearchProvider 发现房源 URL
  -> SourceCandidate
  -> CandidateLead / actionable_leads (L0 待核验)
  -> 可选 ExtractProvider 详情增强
  -> 渠道 adapter 结构化
  -> verified_shortlist (L1+) + evidence
```

## SearchProvider

V1 支持：

- `brave`：需要 `BRAVE_SEARCH_API_KEY`，search-only。
- `exa`：需要 `EXA_API_KEY`，支持 search 和 extract。
- `tavily`：需要 `TAVILY_API_KEY`，支持 search 和 extract。
- `ddgs`：无 API key fallback，search-only。

自动选择顺序：

```text
brave -> exa -> tavily -> ddgs
```

显式配置 provider 但不可用时，不中断搜索流程；系统会记录 warning 并 fallback 到可用 provider。

## CandidateLead

`CandidateLead` 是 V1 默认主结果，来自 search result 的标题、摘要、URL 和可见字段。字段固定包括 `lead_id/source_id/url/title/summary/price_text/area_text/layout_text/freshness_text/commute_matches/budget_match/bedroom_match/provider/trust_level/status/next_action`。

- L0 线索可以展示给用户，但必须明确“待打开平台页核验”。
- ranking 必须命中办公点或通勤圈关键词，并尽量匹配预算和户型。
- `--limit` 表示最终返回 lead 数，不等于每条 query 的 search result 数。
- 搜索候选不能直接生成正式 `ListingItem`。

## ExtractProvider

V1 支持：

- `exa`：需要 `EXA_API_KEY`。
- `tavily`：需要 `TAVILY_API_KEY`。
- `basic_http`：只用于显式 public source smoke 或明确指定的公开页面抓取，不作为默认详情增强路径。

自动选择顺序：

```text
exa -> tavily
```

无 Exa/Tavily extract key 时，默认跳过详情增强并保留 L0 `actionable_leads`。详情增强返回 302、验证码、登录墙或超时时，失败信息进入 `blocked_sources`，不会让整次搜索失败。

## 配置

配置可来自环境变量，或本地私有文件 `~/.last7days-rent/config.json`：

```json
{
  "providers": {
    "search": "auto",
    "extract": "auto",
    "api_keys": {
      "brave": "...",
      "exa": "...",
      "tavily": "..."
    }
  }
}
```

环境变量优先级高于本地 config：

- `BRAVE_SEARCH_API_KEY`
- `EXA_API_KEY`
- `TAVILY_API_KEY`

不要把本地 config、API key、cookie、token 或登录态凭证提交到仓库。

## 输出边界

- Search snippet 可以生成 `CandidateLead`，作为 L0 待核验线索展示；不能直接生成正式 `ListingItem`。
- Extract content 只作为页面内容输入，不能被视为已验真。
- 正式字段优先来自渠道 adapter。
- 缺失字段保持 `unknown` 或 `None`。
- 不登录、不绕验证码、不保存 cookie/token。

## Acquisition 职责边界

`acquisition` 是房源线索获取编排层，负责生成 provider discovery query、执行 search、沉淀 `SourceCandidate`，并调用 lead builder 产出 `actionable_leads`。只有有可用 extract provider 时，才对 top leads 做详情增强，并把成功内容交给 source adapter。

- 城市和平台 URL 由 source query builder 维护。
- 通勤区域 hint 由 profile 或 commute plan 维护。
- P1/P2 只保留为 candidate/warning，默认不进入正式短名单。
- source adapter 是正式结构化入口；search snippet 或 extract text 不能直接生成正式房源。

## Roadmap

- P0：贝壳 / 链家 / Ke、Wellcee、房天下、官方核验入口。默认自动采集，可进入结构化链路。
- P1：自如、我爱我家、豆瓣公开小组、公众号公开文章、安居客、58。有条件采集，需要更强 provider 或用户确认。
- P2：小红书、微博、微信群、朋友圈、公司群、校友群。默认只支持用户授权导入或人工辅助。

V1 不实现 SearXNG、Firecrawl 或并行多 provider 聚合。
