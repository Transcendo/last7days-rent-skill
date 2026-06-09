# Subagent Handoffs

## Handoff 格式

```markdown
## Task

- task id:
- owner agent:
- write scope:

## Changed Files

- path:

## Tests Run

- command:
- result:

## Warnings

- warning:

## Remaining Risks

- risk:
```

## 共享规则

- 每个 subagent 先读 `docs/product-contract.md`、`docs/mvp-boundaries.md` 和 `docs/architecture.md`。
- 不要越过 task 写入范围。
- 不要把 P1/P2、私域、WebSearch 或用户授权导入放进 MVP pipeline。
- 不要输出私人联系方式。
- L1 不能写成已验真，L3 只能来自用户联系确认或明确反馈。
