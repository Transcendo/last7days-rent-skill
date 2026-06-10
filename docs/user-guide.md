# 用户指南

`last7days-rent-skill` 适合在 Codex、Claude Code 等 Agent runtime 中使用。它把租房需求转成可执行的搜索计划，再把候选房源整理成短名单、联系方式、证据包和核验动作。

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

可以直接对 Agent 说：

```text
帮我用 last7days-rent-skill 找上海五角场附近、预算 5200 以内、通勤 35 分钟内的近 7 天候选房源，并告诉我每套房怎么联系。
```

Agent 应读取 `skills/last7days-rent/SKILL.md`，优先调用 CLI，不手工编造房源。

## 创建本地画像

首次建档必须从公司、办公点或园区开始：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile init \
  --office-anchor "上海五角场" \
  --city 上海 \
  --budget-min 3500 \
  --budget-max 5200 \
  --commute-minutes 35 \
  --rental-mode either
```

查看本地画像：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile show
```

## 搜索候选房源

使用本地画像：

```bash
python skills/last7days-rent/scripts/last7days_rent.py search --days 7 --limit 10
```

不预先建档，直接传入一次性参数：

```bash
python skills/last7days-rent/scripts/last7days_rent.py search \
  --office-anchor "上海五角场" \
  --city 上海 \
  --budget-max 5200 \
  --days 7 \
  --limit 10
```

如果公开来源被 403、429、验证码或登录墙阻断，命令会输出 source warning 和 HTTP 状态，并继续尝试可访问的 P0 来源，而不是伪造房源。

## 查看报告

```bash
python skills/last7days-rent/scripts/last7days_rent.py report --latest
```

报告默认写入：

```text
~/.last7days-rent/reports/
```

每份报告应包含候选短名单、联系方式或平台联系入口、source coverage、warnings、字段 provenance、风险标签、下一步核验问题和 7 天行动计划。

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

## 本地测试模式

```bash
python skills/last7days-rent/scripts/last7days_rent.py search --fixture
```

`--fixture` 使用合成样本验证本地链路，不请求网络，也不代表真实房源获取能力。
