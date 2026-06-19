# 用户指南

`last7days-rent-skill` 适合在 Codex、Claude Code 等 Agent runtime 中使用。它面向一线/新一线城市互联网大厂同学，目标是在 7 天内快速完成租房决策：本地化生成租房 profile，基于最新 profile 全渠道聚合房源信息，生成个人租房 HTML，并支持持续 refresh。

它的核心功能是四件事：

1. 本地化搜集用户租房需求，生成专属租房 profile。
2. 根据 profile 全渠道搜索适配房源信息。
3. 生成专属个人租房 HTML。
4. 基于本地最新 profile 更新全渠道房源信息。

当前仓库内置的完整样例 Anchor 是北京京东总部 / 亦庄经海路；其他互联网办公点可以作为后续 Anchor Pack 扩展方向，未内置前应按用户提供的办公点信息生成通用搜索计划，不要承诺已有专门先验包。

## 安装

本地安装：

```bash
npx skills add /path/to/last7days-rent-skill -g
```

未来 GitHub 安装：

```bash
npx skills add <org>/last7days-rent-skill -g
```

## Agent 触发方式

普通用户不需要先学命令，直接对 Agent 说租房目标：

```text
我在北京京东总部亦庄经海路上班，预算 6000 内，想找一居或整租开间，通勤 45 分钟内。
```

也可以用泛化场景开始：

```text
我在上海张江某互联网公司上班，想找整租开间，预算 5500 内，地铁通勤优先。
```

或：

```text
我在深圳南山科技园上班，预算 7000 内，优先平台房源，个人转租只做备选。
```

Agent 应读取 `skills/last7days-rent/SKILL.md`，优先调用 CLI，不手工编造房源。

## 默认流程

用户自然语言目标进入 Agent 后，默认流程是：

```text
profile wizard -> refresh --prepare -> runtime web search/browser -> refresh --evidence -> report
```

对应 CLI 路径：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard start \
  --goal-seed "北京京东总部亦庄经海路，一居室，预算 6000 RMB 以内，通勤 45 分钟内"

python skills/last7days-rent/scripts/last7days_rent.py profile wizard next
python skills/last7days-rent/scripts/last7days_rent.py profile wizard answer --question-id <id> --value <A|B|C|D>
python skills/last7days-rent/scripts/last7days_rent.py profile wizard commit
python skills/last7days-rent/scripts/last7days_rent.py refresh --prepare
python skills/last7days-rent/scripts/last7days_rent.py refresh --evidence <runtime-evidence.json>
python skills/last7days-rent/scripts/last7days_rent.py report --latest
```

`plan`、`ingest`、`render` 保留为底层调试命令。`search` 只保留为兼容提示，不是默认使用路径。

## Profile 问答

Agent 应一次只问一个决策题，优先确认：

- 城市、公司、办公点、园区、楼宇或最近地铁站。
- 预算目标、预算硬上限、户型和是否接受合租。
- 通勤上限、通勤方式、是否接受扩圈。
- 平台房源、品牌公寓、个人转租等来源偏好。
- 风险过滤强度和是否要求明确联系路径。

用户明确要求查看 JSON、查看当前 profile 或解释为什么这么搜时，才展示内部结构。

## Runtime 获源

Agent runtime 负责公开线索发现：

- 有 web search/browser 能力时，按 `refresh --prepare` 生成的 search brief 执行公开搜索和页面核验。
- 没有 web search/browser 能力时，请用户提供公开链接、截图或复制文本。
- 只记录公开可见字段、来源链接、采集时间、联系路径和必要摘要。
- 不绕过登录墙、验证码、cookie、私域群组或其他访问控制。

这里的“全渠道”不是私域自动采集，而是：

- 公开租房平台和公开列表页。
- 品牌公寓公开页。
- 公开转租社区或公开帖子。
- 用户明确授权导入的链接、截图、复制文本。

微信群、公司群、朋友圈、登录后页面、验证码后内容不纳入自动采集。

## 查看报告

```bash
python skills/last7days-rent/scripts/last7days_rent.py report --latest
```

报告默认写入：

```text
~/.last7days-rent/reports/
```

每份 HTML 报告应包含当前 profile、候选房源、联系方式或平台联系入口、渠道覆盖、新增房源、已有候选、被阻断来源、字段 provenance、可信等级、风险标签、下一步核验问题和 7 天行动计划。

## 反馈结果

```bash
python skills/last7days-rent/scripts/last7days_rent.py feedback \
  --listing-id <listing-id> \
  --event-type real_viewable \
  --notes "已联系，确认可看房"
```

常用反馈：

| 类型 | 含义 |
| --- | --- |
| `real_viewable` | 已确认真实可看 |
| `track` | 继续关注 |
| `rented` | 已出租 |
| `expired` | 已失效 |
| `too_far` | 通勤过远 |
| `too_expensive` | 超预算 |
| `lead_gen_suspected` | 疑似引流 |
| `reject_agent` | 拒绝该中介或来源 |
| `untrusted_source` | 来源不可信 |
| `contact_failed` | 联系不上 |
| `wrong_contact` | 联系方式错误 |

只有用户明确反馈或联系确认后，候选房源才能进入 L3。
