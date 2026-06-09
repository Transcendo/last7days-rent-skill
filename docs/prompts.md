# Prompts

## 自动接入/安装 Prompt

```text
请安装并使用 last7days-rent-skill。安装后先读取 SKILL.md，确认它是 Agent Skill + 本地 private profile，不是普通爬虫。不要绕验证码，不要要求 cookie，不要抓私域。
```

## 首次创建 Profile Prompt

```text
请用 last7days-rent-skill 帮我创建本地租房 profile。第一步必须问我的公司、办公点或园区，再由办公点推导城市和通勤圈；不要先从城市泛搜开始。profile 默认写入 ~/.nesthub-rent/profile.json 和 ~/.nesthub-rent/profile.md。
```

## 按 Profile 搜近 7 天房源 Prompt

```text
请基于我的本地 private profile，用 last7days-rent-skill 搜近 7 天候选房源。只使用 P0 来源：贝壳/链家/Ke、Wellcee JSON-LD、房天下、官方核验入口。输出 profile 脱敏摘要、P0 source coverage、候选短名单、L0-L3、风险标签、字段 provenance、下一步核验问题、7 天行动计划、Markdown report 和 JSON evidence package。
```

## 反馈并更新 Profile Prompt

```text
这套房已经失效/太远/太贵/疑似引流/真实可看。请把反馈写入 last7days-rent-skill 的本地 feedback.jsonl，并解释下一轮排序会如何变化。不要上传 profile，不要保存私人联系方式。
```

## Goal / Multi-Agent 执行 Prompt

```text
/goal 请读取 task/mvp-core/ 并完成 last7days-rent-skill MVP。按编号执行：先做 1.product_contract_and_scope.md，再做 2.*，再根据耦合度决定 3.* 是否并行，然后做 4.*，最后由 main agent 完成 5.final_integration_and_validation.md。multi-agent 只在准确、高效且写入范围互不冲突时使用；如果任务小、上下文强耦合或拆分会增加集成风险，由 main agent 串行完成。每个 subagent 必须只处理自己的 task 文件，严格遵守写入范围，完成后汇报 changed files、tests run、warnings、remaining risks。main agent 最终复核，不把 subagent 结果直接当验收。
```

## P0-only MVP 执行 Prompt

```text
请只实现 last7days-rent-skill 的 P0 MVP：贝壳/链家/Ke、Wellcee JSON-LD、房天下、官方核验入口。不要创建 websearch_discovery.py、user_import.py，也不要创建 58/安居客/豆瓣/小红书/微博/公众号 adapter。缺失字段保持 unknown/None；L1 不能写成已验真；L3 只能来自用户联系确认或明确反馈。
```
