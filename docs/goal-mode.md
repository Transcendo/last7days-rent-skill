# Goal Mode

## 执行顺序

1. `1.product_contract_and_scope.md`
2. `2.schema_privacy_risk_contract.md` 与 `2.skill_runtime_contract.md`
3. `3.*` 任务，根据写入范围和耦合度决定并行或串行
4. `4.tests_fixtures_privacy.md` 与 `4.integration_dry_run_docs.md`
5. `5.final_integration_and_validation.md`

## 决策准则

multi-agent 是手段，不是仪式。只有当任务边界清晰、写入范围互不冲突、handoff 成本低于收益时才拆分。否则 main agent 串行完成更准确。

## 必跑命令

```bash
node /Users/annacheng/.codex/skills/goal-task-planner/scripts/validate_goal_tasks.mjs task/mvp-core
python skills/last7days-rent/scripts/last7days_rent.py --help
python skills/last7days-rent/scripts/last7days_rent.py profile show --redacted || true
python skills/last7days-rent/scripts/last7days_rent.py search --fixture
python -m pytest
git status --short --branch
```
