---
name: last7days-rent
version: "0.1.0"
description: "帮助用户 7 天完成租房。基于本地 private profile，从 P0 可信公开来源聚合近 7 天候选房源，脱敏、去重、风险初筛、排序并输出报告。"
argument-hint: "last7days-rent profile init | last7days-rent search --fixture"
allowed-tools: Bash, Read, Write, AskUserQuestion
user-invocable: true
---

# last7days-rent

last7days = 帮助用户 7 天完成租房

这是一个 Agent Skill + 本地 CLI engine，不是普通爬虫。默认根据用户本地 private profile，从 P0 可信/robot-friendly 房源信源获取近 7 天候选房源，完成结构化、脱敏、去重、风险初筛、匹配排序，并输出 Markdown 短名单和 JSON evidence package。

## 触发条件

当用户表达以下需求时使用本技能：

- 想 7 天完成租房。
- 想找近 7 天房源。
- 想基于公司、办公点、园区、预算、通勤圈找房。
- 想导入房源线索并脱敏。
- 想获得候选短名单、风险标签、下一步核验问题和 7 天行动计划。

## 使用原则

1. 首次 profile 建档必须先问公司、办公点或园区，而不是先问城市。
2. profile 默认只保存在 `~/.nesthub-rent/`，不要写入 repo。
3. 缺失价格、地址、押金、入住时间和联系方式时保持 `unknown` 或 `None`，不得补全。
4. L1 是单源结构化，不能写成“已验真”。
5. L3 只能来自用户联系确认或明确反馈。
6. 输出公开报告前必须脱敏手机号、微信号、群名、真实姓名、头像或截图来源身份线索。

## MVP 来源边界

MVP 只做 P0：

- 贝壳 / 链家 / Ke 列表。
- Wellcee JSON-LD。
- 房天下。
- 官方核验入口。

MVP 不做 P1/P2：

- 自如、我爱我家。
- 58 / 安居客。
- 豆瓣、小红书、微博、公众号。
- 微信群、朋友圈、公司群、校友群、私域内容。
- WebSearch discovery。
- 用户授权导入。

不要绕验证码，不要登录，不要要求 cookie，不要暴露私人联系方式。

## CLI

```bash
python skills/last7days-rent/scripts/last7days_rent.py --help
python skills/last7days-rent/scripts/last7days_rent.py profile init --office-anchor "上海五角场"
python skills/last7days-rent/scripts/last7days_rent.py profile show --redacted
python skills/last7days-rent/scripts/last7days_rent.py search --fixture
python skills/last7days-rent/scripts/last7days_rent.py feedback --listing-id demo --event-type real_viewable
```

## 输出

每次 search 应输出：

- profile 脱敏摘要。
- P0 source coverage。
- 候选房源短名单。
- L0-L3 可信等级。
- 匹配理由。
- 风险标签。
- 字段 provenance。
- 下一步核验问题。
- 7 天租房行动计划。
- Markdown report path。
- JSON evidence package path。
