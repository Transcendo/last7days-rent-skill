# last7days-rent-skill

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Local](https://img.shields.io/badge/local--first-contact%20ready-0f766e)
![Status](https://img.shields.io/badge/status-web%20search%20provider%20discovery-0f766e)

`last7days-rent-skill` 是一个面向 Codex、Claude Code、Hermes 等 Agent runtime 的租房 Agent Skill 仓库。它不只是一个 `SKILL.md`：仓库同时包含本地 CLI、search provider / listing source 适配层、HTML 报告模板、文档和测试。目标是根据用户的办公点、预算、通勤和偏好，优先使用宿主 Agent 自带 web search 能力发现近 7 天房源线索，再把标准 JSON 导入 CLI；CLI 只把命中 P0 房源域名且通过 promotion gate 的线索降级转成 L1 候选，去重、风险初筛、匹配排序，并输出可溯源短名单、联系路径和下一步核验动作。

默认 live 搜索先走 runtime web search JSON import；Brave / Tavily / Exa provider fanout 只是 fallback。SearchLead/snippet 不能直接证明价格、发布时间、联系方式或仍在租；没有 promotion 的搜索结果只进入“搜索发现线索”，不会进入核心短名单。旧 HTML parser 仅作为 fixture/parser lab 保留。

## 仓库内容

```text
skills/last7days-rent/
├── SKILL.md                         # Agent runtime 入口说明
├── scripts/last7days_rent.py        # 本地 CLI
├── scripts/lib/search_providers/    # runtime web search / Brave / Tavily / Exa
├── scripts/lib/sources/             # beike_lianjia / fang / wellcee / official_verifier
└── templates/report.html.j2         # HTML 报告模板

docs/
├── user-guide.md
├── source-policy.md
├── troubleshooting.md
└── hermes-agent-web-search-reference.md

tests/                               # CLI、schema、provider、render、privacy 等测试
```

## 快速开始

安装本地 skill：

```bash
npx skills add /path/to/last7days-rent-skill -g
```

安装本地 CLI 依赖：

```bash
cd /path/to/last7days-rent-skill
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

要求 Python 3.11+。macOS 自带 `python3` 可能仍是 3.9；如果直接运行源码，请显式使用 `python3.11` 创建 venv，后续统一用 `.venv/bin/python` 执行 CLI 和测试。

未来 GitHub 安装：

```bash
npx skills add <org>/last7days-rent-skill -g
```

查看命令：

```bash
.venv/bin/python skills/last7days-rent/scripts/last7days_rent.py --help
```

创建本地租房画像：

```bash
.venv/bin/python skills/last7days-rent/scripts/last7days_rent.py profile init \
  --office-anchor "上海五角场" \
  --city 上海 \
  --budget-max 5200 \
  --commute-minutes 35
```

查看或微调本地画像：

```bash
.venv/bin/python skills/last7days-rent/scripts/last7days_rent.py profile show --redacted
.venv/bin/python skills/last7days-rent/scripts/last7days_rent.py profile refine --decision commute --weight 1.2
```

按办公点和预算搜索候选房源。推荐先让 Codex / Claude Code 用自身 web search 找 P0 域名线索，再导入 JSON：

```bash
.venv/bin/python skills/last7days-rent/scripts/last7days_rent.py search \
  --office-anchor "上海五角场" \
  --city 上海 \
  --budget-max 5200 \
  --days 7 \
  --runtime-websearch-json /tmp/last7days-websearch.json \
  --limit 10
```

runtime web search JSON 推荐格式：

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

如果 runtime 搜索没有产生 promoted listing，CLI 会自动回退到 Brave / Tavily / Exa。需要可复现调试时加 `--no-provider-fallback`。

只使用 API provider fallback：

```bash
.venv/bin/python skills/last7days-rent/scripts/last7days_rent.py search \
  --office-anchor "上海五角场" \
  --city 上海 \
  --budget-max 5200 \
  --days 7 \
  --providers auto \
  --limit 10
```

可用 API key：

```bash
export BRAVE_SEARCH_API_KEY=...
export TAVILY_API_KEY=...
export EXA_API_KEY=...
```

Brave 兼容 `BRAVE_API_KEY`。默认 `--providers auto` 会按 `brave,tavily,exa` 顺序只运行有 API key 的 provider；无 key 时报告会写入 `no_search_provider_available`，不会伪造空结果。

查看最近一次报告：

```bash
.venv/bin/python skills/last7days-rent/scripts/last7days_rent.py report --latest
```

记录反馈并影响下一轮排序：

```bash
.venv/bin/python skills/last7days-rent/scripts/last7days_rent.py feedback \
  --listing-id <listing-id> \
  --event-type real_viewable \
  --notes "已联系，确认可看房，费用待核验"
```

本地测试模式：

```bash
.venv/bin/python skills/last7days-rent/scripts/last7days_rent.py search --fixture
```

`--fixture` 只用于验证安装、报告格式、联系方式展示和排序逻辑；它不是默认产品路径，也不代表真实房源获取能力已经完成。

## 输出内容

每次搜索会输出：

- 聊天短名单。
- HTML report。
- JSON evidence package。
- source coverage 和 source warnings。
- 每套候选房源的来源 URL、抓取时间、字段 provenance。
- 每套核心短名单房源的联系方式或平台联系入口。
- 匹配理由、风险标签、不确定点和下一步核验问题。
- 7 天租房行动计划。

默认本地输出路径：

```text
~/.last7days-rent/profile.json
~/.last7days-rent/profile.md
~/.last7days-rent/feedback.jsonl
~/.last7days-rent/cache/
~/.last7days-rent/reports/
~/.last7days-rent/reports/last7days-rent-live.html
~/.last7days-rent/reports/last7days-rent-fixture.html
```

## 当前支持 Search Provider 和 Listing Source

| Search provider | 当前能力 |
| --- | --- |
| Runtime web search JSON import | 导入 Codex / Claude Code / Hermes 等宿主 Agent 的 web search 结果，默认优先使用，不需要 API key |
| Brave Search API | 发现网页级 SearchLead，使用 `freshness=pw`、`count<=20`、`result_filter=web` |
| Tavily API | 发现网页级 SearchLead，默认 `search_depth=basic`、`include_answer=false`、`include_raw_content=false` |
| Exa API | 发现网页级 SearchLead，使用 `includeDomains` 和发布时间窗口；不使用 summary 填事实字段 |

| Listing source | 当前处理 |
| --- | --- |
| 贝壳 / 链家 / Ke | 仅当 search URL 域名命中 `ke.com/lianjia.com` 且有租房语义时 promotion 为 L1 |
| 房天下 | 仅当 search URL 域名命中 `fang.com` 且有租房语义时 promotion 为 L1 |
| Wellcee | 仅当 search URL 域名命中 `wellcee.com` 且有租房语义时 promotion 为 L1 |
| 官方核验入口 | 只记录核验证据，不作为高召回房源来源 |

可查看 registry：

```bash
.venv/bin/python skills/last7days-rent/scripts/last7days_rent.py sources list
```

对单个 source 做 live smoke：

```bash
.venv/bin/python skills/last7days-rent/scripts/last7days_rent.py sources smoke --source fang --city 上海 --area 五角场
```

## CLI 能力总览

| 命令 | 作用 |
| --- | --- |
| `profile init` | 从办公点/园区/公司开始创建本地画像 |
| `profile show --redacted` | 查看脱敏画像摘要 |
| `profile refine` | 用取舍题结果更新权重 |
| `search` | 导入 runtime web search JSON，必要时回退到 Brave/Tavily/Exa |
| `search --fixture` | 用离线 fixture 验证本地链路和报告格式 |
| `sources list` | 查看 search provider 与 listing source registry |
| `sources smoke` | 对单个 source 做 live smoke |
| `feedback` | 记录联系结果，影响下一轮排序 |
| `report --latest` | 返回最近一次 HTML 报告路径 |

## 联系方式与安全边界

这个 skill 默认 local-first，目标是帮用户真正联系房源：

- 公开房源页面或用户授权导入里的电话、微信、邮箱、平台入口、原帖联系说明属于核心房源信息，应保留并展示。
- 没有联系方式且没有可打开联系入口的房源，默认不进入核心短名单。
- 不上传用户画像、报告或反馈。
- 不要求 cookie、token 或平台账号。
- 不绕验证码、登录墙或反机器人机制。
- 不自动抓取微信群、朋友圈、公司群、校友群等私域内容。
- 不默认启用 Tavily extract、Exa full text 或任何 crawl。
- 不保存 cookie、token、secret 或登录态凭证。
- 不用模型补全未知价格、地址、押金、入住时间或联系方式。
- 不把 Search API freshness 当成房源发布时间。
- 不承诺每套房仍在租，不替代线下看房、付款、签约和合同审查。

## 可信等级

| 等级 | 含义 | 使用方式 |
| --- | --- | --- |
| L0 | 原始线索或发现候选 | 只作为候选或被拒绝为 out of scope |
| L1 | 单源结构化，有真实 URL 或用户授权导入证据，并有联系路径 | 可低置信展示，不能写成已验真 |
| L2 | 多源佐证或重复出现，关键字段和联系路径基本一致 | 可进入短名单 |
| L3 | 用户联系确认或明确反馈仍在租、可看房 | 可重点推荐 |

L3 只能来自用户确认或明确反馈。官方核验入口、平台编号或多源重复都不能单独把房源提升为 L3。

## 更多文档

- [用户指南](docs/user-guide.md)
- [来源政策](docs/source-policy.md)
- [排障说明](docs/troubleshooting.md)
- [Hermes Agent web search 接入调研](docs/hermes-agent-web-search-reference.md)

## 开发校验

仓库当前包含 CLI、schema、provider、source、report、privacy、secret guard 等测试。提交 README 或代码改动前，建议至少跑：

```bash
.venv/bin/python -m pytest -q
```

## License

License 尚未声明。公开发布前请补充 `LICENSE` 文件。
