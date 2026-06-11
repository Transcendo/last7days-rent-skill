---
name: last7days-rent
version: "0.1.0"
description: "帮助用户 7 天完成租房。优先使用宿主 Agent web search 能力发现近 7 天房源线索并导入 CLI；Brave/Tavily/Exa 仅作为 fallback，只将通过 P0 promotion gate 的线索转成低置信候选并输出报告。"
argument-hint: "python scripts/last7days_rent.py profile init | python scripts/last7days_rent.py search --runtime-websearch-json /tmp/websearch.json --office-anchor 上海五角场 --city 上海 --budget-max 5200"
allowed-tools: Bash, Read, Write, AskUserQuestion
user-invocable: true
---

# last7days-rent

last7days = 帮助用户 7 天完成租房

这是一个 Agent Skill + 本地 CLI engine，不是普通爬虫。默认根据用户本地 private profile 或一次性参数，先使用 Codex / Claude Code / Hermes 等宿主 Agent 自带 web search 能力发现近 7 天房源线索，再把搜索结果 JSON 导入 CLI；Brave/Tavily/Exa Web Search API 只作为 runtime web search 没有 promoted listing 时的 fallback。SearchLead 默认不能进入核心短名单，只有命中 P0 房源域名且通过 promotion gate 后，才可生成低置信 L1 ListingItem，并输出 HTML 短名单和 JSON evidence package。

## 触发条件

当用户表达以下需求时使用本技能：

- 想 7 天完成租房。
- 想找近 7 天房源。
- 想基于公司、办公点、园区、预算、通勤圈找房。
- 提供房源 URL 或文本，要求结构化、提取联系方式、核验。
- 想获得可溯源候选短名单、联系方式、风险标签、下一步核验问题和 7 天行动计划。

## 使用原则

1. 首次 profile 建档必须先问公司、办公点或园区，而不是先问城市。
2. profile 默认只保存在 `~/.last7days-rent/`，不要写入 repo。
3. 缺失价格、地址、押金、入住时间和联系方式时保持 `unknown` 或 `None`，不得补全。
4. L1 是单源结构化，不能写成“已验真”。
5. L3 只能来自用户联系确认或明确反馈。
6. SearchLead/snippet 不能直接证明价格、发布时间、联系方式或仍在租。
7. 公开房源页面或用户授权导入里的电话、微信、邮箱、平台入口、原帖联系说明必须保留为 `contact_methods`；cookie、token、secret、session、authorization 等凭证不能进入报告或 cache。
8. 不绕验证码、不要求 cookie、不自动抓私域、不保存登录态凭证。
9. 默认不启用 Tavily extract、Exa full text 或任何 crawl。
10. 每套核心短名单房源必须有可行动联系路径。

## MVP 来源边界

MVP Search Provider：

- Runtime web search JSON import：Codex / Claude Code / Hermes 等宿主 Agent 搜索结果导入，默认优先级最高，不需要 API key。
- Brave Search API：`BRAVE_SEARCH_API_KEY`，兼容 `BRAVE_API_KEY`。
- Tavily API：`TAVILY_API_KEY`。
- Exa API：`EXA_API_KEY`。

MVP Listing Source 只做 P0 promotion：

- 贝壳 / 链家 / Ke URL 域名。
- Wellcee URL 域名。
- 房天下 URL 域名。
- 官方核验入口。

MVP 不做 P1/P2：

- 自如、我爱我家。
- 58 / 安居客。
- 豆瓣、小红书、微博、公众号。
- 微信群、朋友圈、公司群、校友群、私域内容。
- Web Search discovery 不能直接升级为正式房源；必须通过 P0 domain + 租房语义 promotion gate。

不要绕验证码，不要登录，不要要求 cookie，不要暴露私人联系方式。

## CLI

Agent runtime 安装后，下面的相对路径都以本 `SKILL.md` 所在目录为准。先进入 skill 目录，或用等价的绝对路径调用 `scripts/last7days_rent.py`。

本地 CLI 依赖由项目 `pyproject.toml` 声明。开发或直接运行源码时，建议在仓库根目录创建 venv 后执行 `python -m pip install -e .`，确保 Jinja2 HTML renderer 可用。

```bash
python scripts/last7days_rent.py --help
python scripts/last7days_rent.py profile init --office-anchor "上海五角场" --city 上海 --budget-max 5200
python scripts/last7days_rent.py profile show --redacted
python scripts/last7days_rent.py search --office-anchor "上海五角场" --city 上海 --budget-max 5200 --runtime-websearch-json /tmp/last7days-websearch.json --limit 10
python scripts/last7days_rent.py search --office-anchor "上海五角场" --city 上海 --budget-max 5200 --days 7 --providers auto --sources wellcee,fang,beike_lianjia --limit 10
python scripts/last7days_rent.py sources list
python scripts/last7days_rent.py search --fixture
python scripts/last7days_rent.py feedback --listing-id demo --event-type real_viewable
```

## Agent runtime web search 工作流

当宿主 Agent 支持 web search 时，优先走这条路径：

1. Agent 用自身 web search 能力搜索 P0 域名，例如 `site:wellcee.com/rent-apartment 上海 五角场 租房 5200以内 近7天`、`site:fang.com 上海 五角场 出租 近7天`。
2. Agent 将搜索结果保存成 JSON 文件，格式为 `{ "provider": "codex_web_search", "query": "...", "results": { "success": true, "data": { "web": [...] } } }`。
3. Agent 调用 CLI：`python scripts/last7days_rent.py search --runtime-websearch-json /tmp/last7days-websearch.json --office-anchor "上海五角场" --city 上海 --budget-max 5200`。
4. 如果 runtime web search 已产生通过 P0 promotion gate 的候选，CLI 默认不再调用 Brave/Tavily/Exa；如果没有 promoted listing，CLI 才回退到 `--providers` 指定的 API provider。

可加 `--no-provider-fallback` 禁用兜底，便于调试和复现。简化 JSON 如果没有内含 `query`，必须同时传 `--runtime-query`。

## 输出

每次 search 应输出：

- profile 脱敏摘要。
- search provider coverage。
- SearchLead / promoted_leads / rejected_leads。
- P0 source coverage。
- 候选房源短名单。
- L0-L3 可信等级。
- 匹配理由。
- 风险标签。
- 字段 provenance。
- 下一步核验问题。
- 7 天租房行动计划。
- HTML report path。
- JSON evidence package path。
