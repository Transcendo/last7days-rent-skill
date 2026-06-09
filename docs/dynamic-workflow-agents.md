# Dynamic Workflow Agents

last7days-rent-skill 的开发和运行默认是单入口：用户只给 main orchestrator 一个 prompt。main orchestrator 根据任务耦合度决定是否启动 subagent，并最终合并、验收和修复。

## 角色

- `main-orchestrator`：读取全部 task、做产品和隐私判断、拆分/合并、最终验证。
- `profile-agent`：profile 建档、办公点锚点、决策题和反馈。
- `source-agent`：P0 source registry、adapter 和 fixture parser。
- `privacy-risk-agent`：schema、脱敏和风险阻断。
- `ranking-render-agent`：normalize、dedupe、scoring、rerank、render。
- `docs-agent`：README、prompts、troubleshooting。
- `qa-agent`：fixtures、pytest 和隐私守卫。
- `integration-agent`：dry run、release checklist 和最终校验辅助。

## 并行规则

- 同编号 task 可并行。
- 同编号任务不得编辑同一写入范围。
- 2.* 完成后，profile/source/ranking/docs 可并行。
- final integration 必须最后由 main agent 完成。
- subagent 不要同时编辑同一个核心文件；需要接线 CLI 时由 main agent 收口。

## 不适合 Multi-Agent 的情况

- 任务足够小，单 agent 可在当前 context 内准确完成。
- 任务需要持续共享同一段复杂上下文。
- 多个任务会频繁修改同一核心文件。
- 拆分后的 handoff 成本高于执行收益。
- 需要 main agent 做产品判断、隐私判断或最终验收。

## 交接物

每个 subagent 汇报：

- changed files。
- tests run。
- warnings。
- remaining risks。

main orchestrator 必须复核结果，不把 subagent 输出直接当最终验收。

## 防止 Context 爆掉

- 长流程状态写入 `docs/progress-ledger-template.md` 的格式。
- 每个 subagent 只读自己的 task、共享契约和必要代码。
- main agent 最后只汇总 changed files、测试输出和风险。

## 可复制 Goal Prompt

```text
/goal 请读取 task/mvp-core/ 并完成 last7days-rent-skill MVP。按编号执行，严格遵守每个 task 的写入范围。multi-agent 只在准确、高效且写入范围互不冲突时使用；不适合拆分时由 main agent 串行完成。每个 subagent 完成后汇报 changed files、tests run、warnings、remaining risks。main agent 最后运行 task validator、CLI smoke、pytest 和 git status。
```

## 用户运行时的 Dynamic Workflow

```text
profile agent 建档
  -> source agents 读取 P0 来源
  -> privacy/risk agent 脱敏与风险阻断
  -> ranking/render agent 输出短名单
  -> main orchestrator 给出核验问题和 7 天行动计划
```
