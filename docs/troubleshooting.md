# 排障说明

## 搜索没有结果

先确认输入是否足够具体：

```bash
python skills/last7days-rent/scripts/last7days_rent.py search \
  --office-anchor "上海五角场" \
  --city 上海 \
  --budget-max 5200 \
  --days 7 \
  --providers auto \
  --limit 10
```

如果报告只有 warnings，说明 search provider 不可用、没有 SearchLead，或 SearchLead 没有通过 promotion gate。不要把空报告当成“没有房源”，应查看 search provider coverage、SearchLead 和 warning。

优先路径是宿主 Agent runtime web search。先让 Codex / Claude Code 用自身 web search 搜索 P0 域名并保存 JSON，再导入 CLI：

```bash
python skills/last7days-rent/scripts/last7days_rent.py search \
  --office-anchor "上海五角场" \
  --city 上海 \
  --budget-max 5200 \
  --runtime-websearch-json /tmp/last7days-websearch.json \
  --limit 10
```

只有 runtime web search 没有 promoted listing 时，CLI 才默认回退到 Brave/Tavily/Exa。

## Provider 缺少 key、限流或鉴权失败

这是预期边界。Brave/Tavily/Exa API 是 fallback；没有 API key 时不会触网，会记录 `*_missing_api_key`。401/403、402、422、429、5xx 等错误会映射成稳定 provider warning。

可尝试：

- 配置 `BRAVE_SEARCH_API_KEY`、`TAVILY_API_KEY` 或 `EXA_API_KEY`。
- 换一个 provider，例如 `--providers tavily,exa`。
- 缩小城市/区域关键词。
- 使用 `--sources wellcee,fang,beike_lianjia` 缩小目标 P0 域名。
- 优先使用 `--runtime-websearch-json` 导入宿主 Agent 的 web search 结果。

## Runtime web search JSON 导入失败

如果 CLI 报 `runtime websearch JSON is invalid`，先确认文件是合法 JSON。推荐格式：

```json
{
  "provider": "codex_web_search",
  "query": "site:wellcee.com/rent-apartment 上海 五角场 租房 5200以内 近7天",
  "results": {
    "success": true,
    "data": {
      "web": [
        {
          "title": "房源标题",
          "url": "https://www.wellcee.com/rent-apartment/...",
          "description": "搜索摘要",
          "position": 1
        }
      ]
    }
  }
}
```

如果 JSON 是简化格式 `{ "success": true, "data": { "web": [...] } }`，必须加 `--runtime-query "上海 五角场 租房"`。单条结果缺少 URL 会被跳过并记录 `runtime_web_search_missing_url`。

## 报告只有 warnings

这通常表示 runtime web search/API provider 都失败、无 key、无结果，或发现的 SearchLead 都没有通过 P0 promotion gate。报告仍然有价值，因为它记录了失败来源和下一步动作。

需要检查：

- `sources list` 里 search provider 的 `has_api_key`。
- `search_provider_coverage` 的 status、HTTP、warning。
- `search_leads` 是否存在。
- `rejected_leads` 的 rejection_reason 是否为 `non_p0_domain`、`no_rental_semantics` 或 `invalid_url`。

## 房源没有联系方式

没有联系方式且没有可打开平台入口的房源，对用户来说不可行动。核心短名单不应推荐这类候选。

需要检查：

- adapter 是否提取了页面里的电话、微信、邮箱或原帖联系说明。
- 平台是否只允许站内联系；如果是，报告应展示 source URL 和联系动作。
- 该来源是否只适合作为 L0 线索，而不是正式 listing。

## SearchLead 没有进入短名单

SearchLead 默认不能直接进入短名单。必须同时满足：

- URL 域名匹配 P0 allowlist，例如 `ke.com`、`lianjia.com`、`fang.com`、`wellcee.com`。
- title/snippet/highlights 至少有租房语义。
- URL 可打开。

SearchLead/snippet 不能直接证明价格、发布时间、联系方式或仍在租。Search API freshness 只能说明搜索索引或页面日期信号，不能等同于房源发布时间。

## 平台只允许站内联系

这是可接受的联系路径。报告应展示：

- 原始房源 URL。
- 联系动作，例如“打开平台页面后点击联系/预约看房”。
- 该联系路径的 provenance 和采集时间。

如果平台入口需要登录或验证码，不要绕过，应记录 warning。

## 联系方式疑似引流

如果房源只给微信/电话、拒绝看房、催定金、要求看房费或资料费，应保留联系方式事实，同时打上风险标签。不要因为有联系方式就把房源写成可信。

## L1、L2、L3 被误解

L1 不是已验真，只表示单源结构化且有来源证据和可行动联系路径。

L2 表示多源佐证或重复字段一致，但仍不保证仍在租。

L3 只能来自用户联系确认或明确反馈，例如“已联系，确认可看房”。平台编号、核验码或多源重复都不能自动变成 L3。

## 本地测试模式

```bash
python skills/last7days-rent/scripts/last7days_rent.py search --fixture
```

该模式只验证 provider fixture、promotion gate、本地链路和报告格式，不请求网络，也不代表真实房源获取成功。
