# Provider 架构说明

`last7days-rent-skill` 使用自有 search/extract provider 架构。Agent runtime 只需要调用 skill 或 CLI；具体搜索和抽取能力由本项目根据配置自动选择。

## 目标

```text
用户 profile
  -> 渠道/区域查询生成
  -> SearchProvider 发现房源 URL
  -> ExtractProvider 获取公开页面内容
  -> 渠道 adapter 结构化
  -> acquisition evidence + 房源输出
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

## ExtractProvider

V1 支持：

- `exa`：需要 `EXA_API_KEY`。
- `tavily`：需要 `TAVILY_API_KEY`。
- `basic_http`：无 API key fallback，只请求公开 HTML，不登录、不绕验证码。

自动选择顺序：

```text
exa -> tavily -> basic_http
```

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

- Search snippet 只能作为 `SourceCandidate`，不能直接生成正式 `ListingItem`。
- Extract content 只作为页面内容输入，不能被视为已验真。
- 正式字段优先来自渠道 adapter。
- 缺失字段保持 `unknown` 或 `None`。
- 不登录、不绕验证码、不保存 cookie/token。

## Roadmap

- P0：贝壳 / 链家 / Ke、Wellcee、房天下、官方核验入口。默认自动采集，可进入结构化链路。
- P1：自如、我爱我家、豆瓣公开小组、公众号公开文章、安居客、58。有条件采集，需要更强 provider 或用户确认。
- P2：小红书、微博、微信群、朋友圈、公司群、校友群。默认只支持用户授权导入或人工辅助。

V1 不实现 SearXNG、Firecrawl 或并行多 provider 聚合。
