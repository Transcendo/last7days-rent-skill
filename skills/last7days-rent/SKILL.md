---
name: last7days-rent
description: "帮助用户 7 天完成租房。默认基于本地 private profile 或一次性参数，用 search provider 获取近 7 天 L0 待核验房源线索；有 extract key 或用户授权内容时再增强为 L1+ 短名单。"
---

# last7days-rent

last7days = 帮助用户 7 天完成租房

这是一个 Agent Skill + 本地 CLI engine，不是普通爬虫。默认根据用户本地 private profile 或一次性参数，通过 search provider 获取可打开、可筛选、可行动的 L0 待核验房源线索，并输出聊天摘要、Markdown report 和 JSON evidence package。有 Exa/Tavily extract key 或用户授权内容时，才尝试详情增强、结构化联系方式、去重、风险初筛和 L1+ 短名单。

## 触发条件

当用户表达以下需求时使用本技能：

- 想 7 天完成租房。
- 想找近 7 天房源。
- 想基于公司、办公点、园区、预算、通勤圈找房。
- 提供房源 URL 或文本，要求结构化、提取联系方式、核验。
- 想获得可溯源房源线索、联系方式、风险标签、下一步核验问题和 7 天行动计划。

## 使用原则

1. 首次 profile 建档必须先问公司、办公点或园区，而不是先问城市。
2. profile 默认只保存在 `~/.last7days-rent/`，不要写入 repo。
3. 缺失价格、地址、押金、入住时间和联系方式时保持 `unknown` 或 `None`，不得补全。
4. L0 是待打开平台页核验的搜索线索，必须明确“待核验”，不能写成已验真或已确认仍在租。
5. L1 是单源结构化，不能写成“已验真”。
6. L3 只能来自用户联系确认或明确反馈。
7. 公开房源页面或用户授权导入里的电话、微信、邮箱、平台入口、原帖联系说明必须保留为 `contact_methods`；cookie、token、secret、session、authorization 等凭证不能进入报告或 cache。
8. 不绕验证码、不要求 cookie、不自动抓私域、不保存登录态凭证。
9. 每套 L1+ 核心短名单房源必须有可行动联系路径；L0 线索至少要有可打开平台 URL 和下一步核验动作。

## 渠道边界

V1 默认自动采集 P0：

- 贝壳 / 链家 / Ke 列表。
- Wellcee JSON-LD。
- 房天下。
- 官方核验入口。

P1 有条件采集，需要更强 provider 或用户确认：

- 自如、我爱我家。
- 安居客、58。
- 豆瓣公开小组、公众号公开文章。

P2 默认只支持用户授权导入或人工辅助：

- 小红书、微博。
- 微信群、朋友圈、公司群、校友群、私域内容。
- WebSearch discovery 可以进入 L0 待核验线索，但不能直接升级为 L1+ 正式房源。

不要绕验证码，不要登录，不要要求 cookie，不要暴露私人联系方式。

## CLI

```bash
python skills/last7days-rent/scripts/last7days_rent.py --help
python skills/last7days-rent/scripts/last7days_rent.py profile init --office-anchor "上海五角场" --city 上海 --budget-max 5200
python skills/last7days-rent/scripts/last7days_rent.py profile show --redacted
python skills/last7days-rent/scripts/last7days_rent.py search --office-anchor "上海五角场" --city 上海 --budget-max 5200 --days 7 --limit 10
python skills/last7days-rent/scripts/last7days_rent.py sources list
python skills/last7days-rent/scripts/last7days_rent.py search --fixture
python skills/last7days-rent/scripts/last7days_rent.py feedback --listing-id demo --event-type real_viewable
```

可选参数只在用户明确表达对应约束时传入：

- 用户要求一居室/两居室以上时，传 `--min-bedrooms N`。
- 用户要求或已经配置 provider key 时，才显式传 `--provider-search` / `--provider-extract`。
- 默认 search 不显式指定 provider，让 auto 根据可用 key 和 DDGS fallback 自动选择。
- 无 Exa/Tavily extract key 时，不要强行抓详情页；先返回 `actionable_leads`。

## 输出

每次 search 应输出：

- profile 脱敏摘要。
- 聊天主结果优先展示最多 5 条 `actionable_leads`：价格、面积、户型、区域命中、更新时间、URL、下一步核验动作。
- `verified_shortlist`：只有详情增强或用户授权内容成功结构化后才出现。
- `blocked_sources`：验证码、登录墙、302、超时等详情增强失败证据。
- `diagnostics`：provider diagnostics、search queries 和 acquisition candidates，放入报告或 JSON 附录，不干扰聊天主结果。
- P0 source coverage。
- L0-L3 可信等级。
- 匹配理由。
- 风险标签。
- 字段 provenance。
- 下一步核验问题。
- 7 天租房行动计划。
- Markdown report path。
- JSON evidence package path。
