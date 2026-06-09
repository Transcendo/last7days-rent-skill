# Architecture

## 目标结构

```text
last7days-rent-skill/
  README.md
  pyproject.toml
  skills/
    last7days-rent/
      SKILL.md
      scripts/
        last7days_rent.py
        lib/
          env.py
          store.py
          schema.py
          privacy.py
          risk.py
          profile_schema.py
          profile_store.py
          office_anchor.py
          commute_plan.py
          preference_questions.py
          feedback.py
          sources/
            __init__.py
            registry.py
            router.py
            beike_lianjia.py
            wellcee.py
            fang.py
            official_verifier.py
          normalize.py
          dedupe.py
          scoring.py
          rerank.py
          pipeline.py
          render.py
          seven_day_plan.py
  docs/
    product-contract.md
    mvp-boundaries.md
    architecture.md
    dynamic-workflow-agents.md
    goal-mode.md
    subagent-handoffs.md
    prompts.md
    troubleshooting.md
    integration-dry-run.md
    progress-ledger-template.md
    release-checklist.md
  tests/
    fixtures/
```

## 禁止创建

MVP 不包含这些文件或 adapter：

- `websearch_discovery.py`
- `user_import.py`
- 58 / 安居客 source adapter。
- 豆瓣 source adapter。
- 小红书 source adapter。
- 微博 source adapter。
- 公众号 source adapter。
- 微信群、朋友圈、公司群、校友群或任何私域 source adapter。

## 模块职责

- `env.py`：解析默认本地目录，所有 private profile 与报告默认写入 `~/.nesthub-rent/`。
- `store.py`：通用 JSON、Markdown、JSONL 读写。
- `schema.py`：共享数据模型和序列化。
- `privacy.py`：脱敏和公开输出守卫。
- `risk.py`：风险标签和非 MVP source 阻断。
- `profile_*`：办公点锚点、决策题、profile 存储和反馈。
- `sources/*`：仅 P0 source adapter 和 registry。
- `normalize.py`、`dedupe.py`、`scoring.py`、`rerank.py`：结构化、聚合、评分和重排。
- `pipeline.py`：离线 fixture 与 source adapter 编排。
- `render.py`：Markdown report、聊天短名单和 JSON evidence package。
- `seven_day_plan.py`：7 天租房行动计划。

## 数据流

```text
profile -> query plan -> P0 source candidates -> listing items -> privacy
  -> normalize -> risk -> dedupe -> scoring -> rerank -> render
  -> Markdown report + JSON evidence package
```

## 写入边界

真实用户 profile、feedback 和 reports 不进入 repo，默认写入：

- `~/.nesthub-rent/profile.json`
- `~/.nesthub-rent/profile.md`
- `~/.nesthub-rent/feedback.jsonl`
- `~/.nesthub-rent/reports/`

测试 fixture 必须使用合成数据，不保存真实用户隐私或真实私聊截图。
