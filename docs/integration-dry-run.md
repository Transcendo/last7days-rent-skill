# Integration Dry Run

## 目标

模拟一次完整用户流程：安装 skill、创建本地 profile、fixture/offline 搜索、生成报告、写反馈、再次搜索。

## 步骤

1. 安装 skill。

```bash
npx skills add /path/to/last7days-rent-skill -g
```

2. 创建本地 profile，第一步从办公点开始。

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile init --office-anchor "上海五角场" --budget-min 3500 --budget-max 5200
```

3. 脱敏展示 profile。

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile show --redacted
```

4. 离线 fixture 搜索并生成报告。

```bash
python skills/last7days-rent/scripts/last7days_rent.py search --fixture
```

5. 写入反馈。

```bash
python skills/last7days-rent/scripts/last7days_rent.py feedback --listing-id fixture-beike-001 --source-id beike_lianjia --event-type real_viewable
```

6. 再次搜索，观察反馈 boost 后排序。

```bash
python skills/last7days-rent/scripts/last7days_rent.py search --fixture
```

## 验收点

- profile 和 reports 默认写入 `~/.nesthub-rent/`。
- Markdown report 与 JSON evidence package 均生成。
- 报告含 profile 脱敏摘要、P0 source coverage、短名单、L0-L3、风险标签、字段 provenance、下一步核验问题和 7 天行动计划。
- P1/P2、私域、WebSearch、用户授权导入不会进入报告。
