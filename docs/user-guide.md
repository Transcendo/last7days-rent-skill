# 用户指南

`last7days-rent-skill` 适合在 Codex、Claude Code 等 Agent runtime 中使用。它优先让宿主 Agent 用自身 web search 能力发现 SearchLead，再把标准 JSON 导入 CLI；Brave/Tavily/Exa API 只作为 fallback。CLI 会把通过 P0 promotion gate 的线索整理成短名单、联系方式、证据包和核验动作。

## 安装

本地安装：

```bash
npx skills add /path/to/last7days-rent-skill -g
```

安装本地 CLI 依赖：

```bash
cd /path/to/last7days-rent-skill
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

未来 GitHub 安装：

```bash
npx skills add <org>/last7days-rent-skill -g
```

## Agent 触发方式

可以直接对 Agent 说：

```text
帮我用 last7days-rent-skill 找上海五角场附近、预算 5200 以内、通勤 35 分钟内的近 7 天候选房源，并告诉我每套房怎么联系。
```

Agent 应读取 `skills/last7days-rent/SKILL.md`，先使用宿主 web search 获取真实搜索结果，再调用 CLI 导入 JSON，不手工编造房源。

## 创建本地画像

首次建档必须从公司、办公点或园区开始：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile init \
  --office-anchor "上海五角场" \
  --city 上海 \
  --budget-min 3500 \
  --budget-max 5200 \
  --commute-minutes 35 \
  --rental-mode either
```

查看本地画像：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile show
```

## 搜索候选房源

推荐路径是 runtime web search JSON import。Agent 先用 Codex / Claude Code / Hermes 的 web search 能力搜索 P0 域名，例如：

```text
site:wellcee.com/rent-apartment 上海 五角场 租房 5200以内 近7天
site:fang.com 上海 五角场 出租 5200以内 近7天
site:ke.com 上海 五角场 租房 5200以内 近7天
```

然后把结果保存为 JSON：

```json
{
  "provider": "claude_code_web_search",
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

导入并生成报告：

```bash
python skills/last7days-rent/scripts/last7days_rent.py search \
  --office-anchor "上海五角场" \
  --city 上海 \
  --budget-max 5200 \
  --days 7 \
  --runtime-websearch-json /tmp/last7days-websearch.json \
  --limit 10
```

如果 JSON 是 `{ "success": true, "data": { "web": [...] } }` 这种简化格式，必须同时传 `--runtime-query "上海 五角场 租房 5200以内 近7天"`。如果 runtime 搜索没有产生 promoted listing，CLI 默认自动回退到 API provider；加 `--no-provider-fallback` 可禁用兜底。

## API provider fallback

Brave/Tavily/Exa 是 fallback。只使用 API provider 时，需要至少一个 search provider API key：

```bash
export BRAVE_SEARCH_API_KEY=...
export TAVILY_API_KEY=...
export EXA_API_KEY=...
```

Brave 也兼容 `BRAVE_API_KEY`。默认 `--providers auto` 会按 `brave,tavily,exa` 顺序只运行有 key 的 provider。

使用本地画像：

```bash
python skills/last7days-rent/scripts/last7days_rent.py search --days 7 --limit 10 --providers auto
```

不预先建档，直接传入一次性参数：

```bash
python skills/last7days-rent/scripts/last7days_rent.py search \
  --office-anchor "上海五角场" \
  --city 上海 \
  --budget-max 5200 \
  --days 7 \
  --providers brave,tavily,exa \
  --sources wellcee,fang,beike_lianjia \
  --limit 10
```

`--providers` 表示 Brave/Tavily/Exa 这类搜索 API；`--sources` 表示目标房源平台或域名过滤，例如 `wellcee,fang,beike_lianjia`。

如果 runtime web search 已产生 promoted listing，CLI 默认不再调用这些 API provider。如果 provider 缺少 API key、限流、鉴权失败或返回非法请求，命令会输出 provider warning，并继续尝试其他 provider，而不是伪造房源。SearchLead/snippet 不能直接证明价格、发布时间、联系方式或仍在租；未通过 promotion gate 的线索只进入报告的“搜索发现线索”。

## 查看报告

```bash
python skills/last7days-rent/scripts/last7days_rent.py report --latest
```

报告默认写入：

```text
~/.last7days-rent/reports/
~/.last7days-rent/reports/last7days-rent-live.html
~/.last7days-rent/reports/last7days-rent-fixture.html
```

每份 HTML 报告应包含候选短名单、联系方式或平台联系入口、search provider coverage、source coverage、SearchLead、warnings、字段 provenance、风险标签、下一步核验问题和 7 天行动计划。JSON evidence package 会与 HTML 同目录保留，供机器读取和复核。

## 反馈结果

```bash
python skills/last7days-rent/scripts/last7days_rent.py feedback \
  --listing-id <listing-id> \
  --event-type real_viewable \
  --notes "已联系，确认可看房"
```

常用反馈：

| 类型 | 含义 |
| --- | --- |
| `real_viewable` | 已确认真实可看 |
| `track` | 继续关注 |
| `rented` | 已出租 |
| `expired` | 已失效 |
| `too_far` | 通勤过远 |
| `too_expensive` | 超预算 |
| `lead_gen_suspected` | 疑似引流 |
| `reject_agent` | 拒绝该中介或来源 |
| `untrusted_source` | 来源不可信 |
| `contact_failed` | 联系不上 |
| `wrong_contact` | 联系方式错误 |

只有用户明确反馈或联系确认后，候选房源才能进入 L3。

## 本地测试模式

```bash
python skills/last7days-rent/scripts/last7days_rent.py search --fixture
```

`--fixture` 使用 provider JSON fixture 或内置 provider fixture 验证本地链路，不请求网络，也不代表真实房源获取能力。
