# last7days-rent-skill

**last7days = 帮助用户 7 天完成租房**

last7days-rent-skill 是一个 Agent Skill + 本地 CLI engine。它根据用户本地 private profile，从 P0 可信/robot-friendly 房源信源获取近 7 天候选房源，完成结构化、脱敏、去重、风险初筛、匹配排序，并输出 Markdown 短名单和 JSON evidence package。

## 快速开始

本地安装：

```bash
npx skills add /path/to/last7days-rent-skill -g
```

未来 GitHub 安装：

```bash
npx skills add <org>/last7days-rent-skill -g
```

本地 CLI smoke：

```bash
python skills/last7days-rent/scripts/last7days_rent.py --help
python skills/last7days-rent/scripts/last7days_rent.py profile init --office-anchor "上海五角场" --budget-max 5200
python skills/last7days-rent/scripts/last7days_rent.py profile show --redacted
python skills/last7days-rent/scripts/last7days_rent.py search --fixture
```

## MVP 边界

MVP 只接入 P0 来源：贝壳/链家/Ke 列表、Wellcee JSON-LD、房天下、官方核验入口。

MVP 不接入 P1/P2：自如、我爱我家、58/安居客、豆瓣、小红书、微博、公众号、微信群、朋友圈、公司群、校友群、私域内容、WebSearch discovery、用户授权导入。

MVP 不绕验证码、不登录、不要求 cookie，不承诺每套房仍在租，不替代线下看房、付款、签约和合同审查。

## 输出路径

默认本地 private profile 与报告目录：

- `~/.nesthub-rent/profile.json`
- `~/.nesthub-rent/profile.md`
- `~/.nesthub-rent/feedback.jsonl`
- `~/.nesthub-rent/reports/`

## L0-L3

| 等级 | 含义 |
| --- | --- |
| L0 | 原始线索，未结构化或来源不足 |
| L1 | 单源结构化，有原始 URL 或平台证据，不能写成已验真 |
| L2 | 多源佐证或重复出现，关键字段基本一致 |
| L3 | 用户联系确认或明确反馈仍在租、可看房 |

## 可复制 Prompts

### 自动接入/安装

```text
请安装并使用 last7days-rent-skill。安装后先读取 SKILL.md，确认它是 Agent Skill + 本地 private profile，不是普通爬虫。不要绕验证码，不要要求 cookie，不要抓私域。
```

### 首次创建 Profile

```text
请用 last7days-rent-skill 帮我创建本地租房 profile。第一步必须问我的公司、办公点或园区，再由办公点推导城市和通勤圈；不要先从城市泛搜开始。
```

### 按 Profile 搜近 7 天房源

```text
请基于我的本地 private profile，用 last7days-rent-skill 搜近 7 天候选房源。只使用 P0 来源：贝壳/链家/Ke、Wellcee JSON-LD、房天下、官方核验入口。输出 Markdown report 和 JSON evidence package。
```

### 反馈并更新 Profile

```text
这套房已经失效/太远/太贵/疑似引流/真实可看。请把反馈写入 last7days-rent-skill 的本地 feedback.jsonl，并解释下一轮排序会如何变化。
```

### Goal / Multi-Agent 执行

```text
/goal 请读取 task/mvp-core/ 并完成 last7days-rent-skill MVP。按编号执行。multi-agent 只在准确、高效且写入范围互不冲突时使用；如果任务小、上下文强耦合或拆分会增加集成风险，由 main agent 串行完成。每个 subagent 必须汇报 changed files、tests run、warnings、remaining risks，最终由 main agent 复核并运行 validator、CLI smoke、pytest 和 git status。
```

### P0-only MVP 执行

```text
请只实现 last7days-rent-skill 的 P0 MVP：贝壳/链家/Ke、Wellcee JSON-LD、房天下、官方核验入口。不要创建 websearch_discovery.py、user_import.py，也不要创建 58/安居客/豆瓣/小红书/微博/公众号 adapter。
```

完整 prompt 模板见 `docs/prompts.md`。排障见 `docs/troubleshooting.md`。
