# Release Checklist

## 文档

- README 首屏包含产品名、slogan、一句话定位、快速开始和非承诺边界。
- `docs/product-contract.md`、`docs/mvp-boundaries.md`、`docs/architecture.md` 存在。
- prompts、troubleshooting、dynamic workflow、dry run 文档存在。

## Skill 安装

- `skills/last7days-rent/SKILL.md` 包含触发条件、隐私边界和 P0-only MVP。
- 安装命令存在：`npx skills add /path/to/last7days-rent-skill -g`。

## CLI Smoke

```bash
python skills/last7days-rent/scripts/last7days_rent.py --help
python skills/last7days-rent/scripts/last7days_rent.py profile show --redacted || true
python skills/last7days-rent/scripts/last7days_rent.py search --fixture
```

## 测试

```bash
python -m pytest
```

## Privacy Scan

- 报告不含手机号明文。
- 报告不含微信号明文。
- 报告不含私域群名。
- 报告不含原发帖人真实姓名。
- 报告不含头像或截图来源身份线索。

## Task Validator

```bash
node /Users/annacheng/.codex/skills/goal-task-planner/scripts/validate_goal_tasks.mjs task/mvp-core
```

## Git Status

```bash
git status --short --branch
```
