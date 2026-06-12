# last7days-rent-skill

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Local](https://img.shields.io/badge/local--first-contact%20ready-0f766e)
![Status](https://img.shields.io/badge/status-live%20P0%20search-0f766e)

`last7days-rent-skill` 是一个面向 Codex、Claude Code 等 Agent runtime 的租房 Agent Skill。当前 V1 目标是根据用户的办公点、预算、通勤和偏好，默认先稳定产出可打开、可筛选、可行动的 L0 待核验房源线索；有 Exa/Tavily extract key 或用户授权内容时，再增强为 L1+ 结构化短名单、联系路径和下一步核验动作。

默认搜索会先根据 profile 生成渠道查询，再按 provider 可用性选择 Brave / Exa / Tavily / DDGS。没有详情增强 key 时，系统不会默认抓详情页，而是直接返回排序后的 `actionable_leads`。公开来源如果返回 403、429、验证码或登录墙，报告会保留 source、URL、HTTP 状态和 warning，不会伪造房源。

## 快速开始

安装本地 skill：

```bash
npx skills add /path/to/last7days-rent-skill -g
```

未来 GitHub 安装：

```bash
npx skills add YOUR_GITHUB_USERNAME/last7days-rent-skill -g
```

`YOUR_GITHUB_USERNAME` 是发布占位符，公开发布前请替换为实际 GitHub user 或 org。

查看命令：

```bash
python skills/last7days-rent/scripts/last7days_rent.py --help
```

创建本地租房画像：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile init \
  --office-anchor "上海五角场" \
  --city 上海 \
  --budget-max 5200 \
  --commute-minutes 35
```

按办公点和预算搜索 L0 待核验房源线索：

```bash
python skills/last7days-rent/scripts/last7days_rent.py search \
  --office-anchor "上海五角场" \
  --city 上海 \
  --budget-max 5200 \
  --days 7 \
  --limit 10
```

可显式指定 provider；如果指定 search provider 缺 key，会记录 warning 并自动 fallback。只有配置了 Exa/Tavily extract key，或显式指定 `--provider-extract basic_http` 做公开页面 smoke 时，才会尝试详情增强：

```bash
python skills/last7days-rent/scripts/last7days_rent.py search \
  --office-anchor "北京亦庄办公点" \
  --city 北京 \
  --budget-max 5200 \
  --provider-search brave \
  --provider-extract exa
```

查看最近一次报告：

```bash
python skills/last7days-rent/scripts/last7days_rent.py report --latest
```

记录反馈并影响下一轮排序：

```bash
python skills/last7days-rent/scripts/last7days_rent.py feedback \
  --listing-id <listing-id> \
  --event-type real_viewable \
  --notes "已联系，确认可看房，费用待核验"
```

本地测试模式：

```bash
python skills/last7days-rent/scripts/last7days_rent.py search --fixture
```

`--fixture` 只用于验证安装、报告格式、联系方式展示和排序逻辑；它不是默认产品路径，也不代表真实房源获取能力已经完成。

## 输出内容

每次搜索会输出：

- 聊天主结果：最多 5 条 `actionable_leads`，包含价格、面积、户型、区域命中、更新时间、URL 和下一步核验动作。
- Markdown report。
- JSON evidence package。
- `verified_shortlist`：详情增强或用户授权内容成功结构化后的 L1+ 短名单。
- `blocked_sources`：验证码、登录墙、302、超时等详情增强失败证据。
- `diagnostics`：provider diagnostics、search queries 和 acquisition candidates，默认放在报告或 JSON 附录。
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
```

## 当前支持来源

| 来源 | 当前能力 | 联系路径 |
| --- | --- | --- |
| 贝壳 / 链家 / Ke | 生成公开列表 URL，解析公开卡片；遇到验证码或登录墙时输出 warning | 平台详情页入口 |
| 房天下 | 生成上海五角场等公开列表 URL，解析卡片、价格、面积、户型、位置和详情页 | 平台详情页入口，页面公开电话时保留 |
| Wellcee | 支持解析用户提供的详情页 HTML / JSON-LD | 平台入口、原帖说明、公开电话、微信、邮箱 |
| 官方核验入口 | 只记录核验证据 | 不作为高召回房源来源 |

## Provider 配置

V1 search provider：

- `brave`：需要 `BRAVE_SEARCH_API_KEY`。
- `exa`：需要 `EXA_API_KEY`。
- `tavily`：需要 `TAVILY_API_KEY`。
- `ddgs`：无 key fallback。

V1 extract provider：

- `exa`：需要 `EXA_API_KEY`。
- `tavily`：需要 `TAVILY_API_KEY`。
- `basic_http`：只用于显式 public source smoke 或明确指定的公开页面抓取，不作为默认详情增强路径。

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

不要把本地 `config.json`、API key、cookie、token 或登录态凭证提交到仓库。

自动选择顺序：

- search：`brave -> exa -> tavily -> ddgs`
- extract：`exa -> tavily`；无 key 时默认跳过详情增强并保留 L0 leads。

## 渠道 Roadmap

- P0：贝壳 / 链家 / Ke、Wellcee、房天下、官方核验入口。默认自动采集，可进入结构化链路。
- P1：自如、我爱我家、豆瓣公开小组、公众号公开文章、安居客、58。有条件采集，需要更强 provider 或用户确认。
- P2：小红书、微博、微信群、朋友圈、公司群、校友群。默认只支持用户授权导入或人工辅助。

可查看 registry：

```bash
python skills/last7days-rent/scripts/last7days_rent.py sources list
```

## 联系方式与安全边界

这个 skill 默认 local-first，目标是帮用户真正联系房源：

- 公开房源页面或用户授权导入里的电话、微信、邮箱、平台入口、原帖联系说明属于核心房源信息，应保留并展示。
- 没有联系方式且没有可打开联系入口的房源，默认不进入 L1+ 核心短名单；L0 线索必须至少提供可打开平台 URL。
- 不上传用户画像、报告或反馈。
- 不要求 cookie、token 或平台账号。
- 不绕验证码、登录墙或反机器人机制。
- 不自动抓取微信群、朋友圈、公司群、校友群等私域内容。
- 不保存 cookie、token、secret 或登录态凭证。
- 不用模型补全未知价格、地址、押金、入住时间或联系方式。
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
- [Provider 架构说明](docs/provider-architecture.md)
- [排障说明](docs/troubleshooting.md)

## License

MIT License. See [LICENSE](LICENSE).
