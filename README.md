# last7days-rent-skill

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Local](https://img.shields.io/badge/local--first-agent%20skill-0f766e)

`last7days-rent-skill` 是一个面向一线/新一线城市互联网大厂同学的 7 天快速租房 Skill。它基于用户自己的租房需求，全渠道聚合公开可用和用户授权输入的房源信息，帮助用户建立本地 profile、持续刷新候选池，并生成个人租房 HTML。

这个仓库提供：

- 一个可安装的 `last7days-rent` Skill。
- 一个本地 CLI engine，用于保存 private profile、生成全渠道 search brief、导入公开 evidence、去重排序并渲染个人 HTML 房源列表。
- 一套公开来源和隐私边界规则，避免把租房助手做成平台爬虫或私域采集器。

仓库职责固定为四件事：

1. 本地化收集用户租房需求，生成专属租房 profile。
2. 基于最新 profile 生成全渠道搜索 brief，并适配公开房源信息。
3. 生成专属个人租房 HTML 候选池。
4. 基于本地最新 profile 持续更新全渠道房源信息。

## 适合谁

- 在北京、上海、深圳、杭州、广州、成都、南京、武汉、西安等一线/新一线城市租房的互联网公司员工。
- 需要围绕公司、办公园区、楼宇、地铁站或班车点评估通勤圈的人。
- 想把公开房源、平台入口、个人转租线索和风险标签整理成一个可更新候选池的人。

## 能做什么

- 本地化收集租房需求，生成专属 profile：城市、公司/办公点、预算、户型、通勤、来源偏好和风险偏好。
- 根据 profile 生成全渠道搜索 brief，例如当前内置样例 Anchor：北京京东总部 / 亦庄经海路。
- 使用 Agent runtime 的公开 web search/browser，或用户授权导入的公开链接、截图、复制文本，整理房源 evidence。
- 为候选做去重、可信等级、风险标签、联系路径和下一步核验动作。
- 输出本地可更新的个人租房 HTML 候选池；JSON 只作为 profile、evidence 和 listing pool 状态。
- 后续基于本地最新 profile 继续 refresh，不覆盖用户反馈状态。

字节、腾讯、阿里、美团、百度、网易、小米等办公点可以作为后续 Anchor Pack 扩展方向；当前仓库只把北京京东总部样例作为完整可执行先验包。

## 怎么开始

普通用户不需要先学 CLI，直接把租房目标告诉 Agent：

```text
我在北京京东总部亦庄经海路上班，预算 6000 内，想找一居或整租开间，通勤 45 分钟内。
```

也可以这样说：

```text
我在上海张江某互联网公司上班，想找整租开间，预算 5500 内，地铁通勤优先。
```

Agent 会先补齐 profile，再执行全渠道 refresh：生成搜索 brief、收集公开 evidence，最后给出本地个人 HTML 候选池。

默认工作流：

```text
profile wizard -> refresh --prepare -> runtime web search/browser -> refresh --evidence -> report
```

## 适用场景

- 基于互联网公司、办公园区、楼宇、班车点、商圈或地铁站附近找房。
- 按预算、户型、通勤时间、入住时间和风险偏好整理候选。
- 把公开网页、搜索结果、用户提供链接、截图或复制文本整理成可筛选房源列表。
- 为每条候选保留来源链接、可信等级、风险标签、联系路径和下一步核验动作。

## 快速开始

安装本地 skill：

```bash
npx skills add /path/to/last7days-rent-skill -g
```

查看命令：

```bash
python skills/last7days-rent/scripts/last7days_rent.py --help
```

启动 profile wizard：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard start \
  --goal-seed "北京京东总部亦庄经海路，一居室，预算 6000 RMB 以内，通勤 45 分钟内"
```

逐题确认偏好：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard next
python skills/last7days-rent/scripts/last7days_rent.py profile wizard answer --question-id <id> --value <A|B|C|D>
```

确认 profile 并生成搜索计划：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard commit
python skills/last7days-rent/scripts/last7days_rent.py refresh --prepare
```

导入 Agent runtime 整理出的 evidence，并自动更新个人 HTML：

```bash
python skills/last7days-rent/scripts/last7days_rent.py refresh \
  --evidence <runtime-evidence.json>
```

查看最近的 HTML 房源列表：

```bash
python skills/last7days-rent/scripts/last7days_rent.py report --latest
```

`plan`、`ingest`、`render` 仍保留为底层调试命令；普通用户主路径是 `refresh`。

默认本地输出路径：

```text
~/.last7days-rent/profile.json
~/.last7days-rent/profiles/
~/.last7days-rent/pools/
~/.last7days-rent/reports/
~/.last7days-rent/feedback.jsonl
```

## Agent 工作方式

这个 skill 不内置通用搜索引擎，也不要求搜索 API key。Agent runtime 负责使用自身可用能力发现公开线索：

- 用短问答确认用户的租房 profile。
- 按 `refresh --prepare` 生成的 brief 执行公开 web search 和页面核验。
- 只记录公开可见字段、来源链接、采集时间和必要摘要。
- 将结构化 evidence 交给 CLI 的 `refresh --evidence` 命令。
- 由本地 CLI 负责校验 evidence、去重、可信等级、排序、风险标签和 HTML 渲染。

如果 runtime 没有 web search/browser 能力，可以让用户提供公开链接、截图或复制文本，再导入为 evidence。

## 输出内容

默认人类交付物是单文件 HTML：

- profile 摘要：位置锚点、预算、户型、通勤策略。
- 房源卡片：标题、小区、价格、面积、户型、片区、来源链接。
- 筛选控件：关键词、可信等级、状态、风险标签。
- 可信等级：L0/L1/L2/L3。
- 风险标签：片段线索、缺少联系路径、字段待核验等。
- 下一步动作：打开来源、确认仍在租、核验费用和联系入口。

机器产物是本地 JSON 状态：

- profile draft / committed profile。
- search brief。
- runtime evidence。
- listing pool。

## 可信等级

| 等级 | 含义 | 使用方式 |
| --- | --- | --- |
| L0 | 搜索结果、片段、复制文本或未打开页面 | 只能作为待核验候选 |
| L1 | 已打开公开页面，且至少 3 个关键字段可见 | 可低置信展示 |
| L2 | 至少两个独立来源交叉确认同一房源，且价格、小区、户型、面积、联系入口等关键字段一致 | 可进入短名单 |
| L3 | 用户已联系、约看、实看或明确反馈仍在租 | 可重点推荐 |

同一中介在多个平台重复分发不算独立来源。L3 只能来自用户反馈，不能由搜索、模型推断或多源重复自动升级。

## 隐私和来源边界

- 不要求用户提供 cookie、token、secret 或登录态。
- 不绕验证码、不登录、不做反自动化对抗。
- 不保存平台内部接口响应。
- 不自动抓微信群、朋友圈、公司群、校友群等私域内容。
- 不保存或公开原发帖人的真实身份。
- 不用模型补全未知价格、地址、押金、入住时间或联系方式。
- 不承诺每套房仍在租，不替代线下看房、付款、签约和合同审查。

## 开发验证

```bash
python3 -m pytest
python skills/last7days-rent/scripts/last7days_rent.py --help
python skills/last7days-rent/scripts/last7days_rent.py report --latest
```

## 更多文档

- [User Guide](docs/user-guide.md)
- [Source Policy](docs/source-policy.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Runtime Adapter Contract](docs/runtime-adapter-contract.md)

## License

MIT License. See [LICENSE](LICENSE).
