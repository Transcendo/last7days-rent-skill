# AGENTS.md

这是用于近 7 天租房候选发现的 Agent Skill 包，目标是从允许的公开来源中产出可行动、可溯源的房源短名单。

## 参考原则

- Provider 设计只保留公开、可移植的架构说明；不要在仓库中记录个人本地路径、设备状态、私有 token 状态或内部运行环境。

## 工作边界

- 产品目标是 `last7days-rent` skill，不是通用网页抓取器。
- 修改来源能力前，先阅读 `skills/last7days-rent/SKILL.md` 和 `docs/source-policy.md`。
- Web search 只作为发现层。搜索 snippet 可以产生 source candidate 或 URL queue，但不能直接成为正式房源。
- 正式房源必须来自允许的 P0 source adapter、详情页、平台页或用户授权输入，并保留 URL、采集时间、联系路径和字段 provenance。
- 不绕过登录墙、验证码、cookie、私域群组或其他访问控制。
