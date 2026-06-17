# 北京京东总部 Runtime Search Playbook

日期：2026-06-14

用途：指导 Agent runtime 按 `beijing-jd-hq-yizhuang` Anchor Pack 执行公开渠道发现、详情页核验和 evidence handoff。本 playbook 不处理中介私域库存，不读取微信群、公司群、校友群或登录后内容。

## 1. 运行入口

先确认本地 profile 已通过 wizard 写入：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard inspect --format json
```

生成北京京东 search brief：

```bash
python skills/last7days-rent/scripts/last7days_rent.py plan \
  --anchor-id beijing-jd-hq-yizhuang \
  --output /tmp/jd-search-brief.json \
  --explain
```

Agent runtime 读取 `/tmp/jd-search-brief.json` 后执行公开 web search/browser。完成后写出：

```text
/tmp/jd-runtime-evidence.json
```

校验、导入、渲染：

```bash
python skills/last7days-rent/scripts/last7days_rent.py ingest \
  --evidence /tmp/jd-runtime-evidence.json \
  --validate

python skills/last7days-rent/scripts/last7days_rent.py ingest \
  --evidence /tmp/jd-runtime-evidence.json \
  --output-pool /tmp/jd-hq-beijing.listing-pool.json

python skills/last7days-rent/scripts/last7days_rent.py render \
  --pool /tmp/jd-hq-beijing.listing-pool.json \
  --output /tmp/jd-hq-beijing-rentals.html
```

## 2. 执行顺序

按 `search_batches` 顺序执行，不要先跳到低质量来源：

1. `p0_price_anchor`：房天下、贝壳/链家、链家移动列表、Wellcee，用于价格锚点和可打开平台页。
2. `near_office`：经海路、通泰国际、定海园、锋创科技园，重点补 Wellcee 和链家移动列表。
3. `main_residential`：次渠、次渠南、次渠嘉园、次渠锦园、禧瑞天著。
4. `space_budget_backup`：马驹桥、富力尚悦居、星悦国际、国风美仑、珠江四季悦城。
5. `transfer_personal`：只保留豆瓣公开帖；牛客和泛公开文章不进入 runtime 获源。
6. `brand_apartment`：Wellcee、自如、乐乎、泊寓、蜂客、城家、有巢等公开品牌公寓入口，只作为过渡选项。

## 3. 打开策略

每条搜索结果先分类，再决定是否打开：

| URL 类型 | 处理 |
| --- | --- |
| `platform_listing_detail` | 打开详情页，抽字段，可成为 L1 |
| `platform_list_page` | 抽列表条目或进入 detail queue |
| `community_topic` | 打开公开正文，脱敏后抽字段 |
| `guide/article` | 不入 listing，只作为上下文 |
| `video/social_search_result` | 只做 L0 source candidate |
| `login/captcha/app_wall` | 记录 blocked，不绕过 |
| `duplicated` | 合并 observation |

默认预算：

- 最多执行 45 条 query。
- 每条 query 最多看 8 个结果。
- 总详情页最多打开 48 个。
- 每个来源最多打开 8 个详情页。
- 若 L1+ 少于 5 条，应扩圈继续执行后续 batch。
- 连续 2 个 batch 没有新增主候选时停止。

## 4. 字段抽取

每个 evidence item 必须包含：

- `evidence_id`
- `batch_id`
- `query_id`
- `query`
- `collected_via`
- `source_url`
- `source_name`
- `source_type`
- `page_opened`
- `title`
- `snippet`
- `raw_excerpt`
- `observed_at`
- `visible_fields`

建议包含：

- `canonical_url`
- `source_domain`
- `source_tier`
- `url_class`
- `listing_candidate_status`
- `normalized_fields`
- `contact_path`
- `runtime_actions`
- `reject_reasons`

## 5. L1 硬条件

任何来源都不能默认 L1。`listing_candidate_status=candidate_l1` 必须同时满足：

- 已打开公开详情页：`page_opened=true`。
- 页面不是登录墙、验证码、app下载墙或纯搜索结果页。
- `source_url` 可回访，`observed_at` 是本次采集时间。
- `raw_excerpt` 包含页面可见原文摘录。
- 至少 3 类核心字段可见：价格、片区/小区、户型/面积、联系方式入口、发布时间/更新时间。
- 原发帖人姓名、手机号、微信号、群名或私域原文已经脱敏。

不满足 L1 的内容可以进入 L0 线索池，但不能进入主推荐。

## 6. Evidence 骨架

```json
{
  "runtime_meta": {
    "runtime_name": "unknown",
    "adapter_version": "0.2.0",
    "capabilities": ["web_search", "browser_open", "local_file_write", "structured_output"]
  },
  "query_context": {
    "anchor_id": "beijing-jd-hq-yizhuang",
    "brief_path": "/tmp/jd-search-brief.json",
    "profile_summary": "北京京东总部，经海路，正规一居，目标 5000，最高 6000，优先 30 分钟内"
  },
  "execution_summary": {
    "queries_executed": 45,
    "search_results_seen": 160,
    "detail_pages_opened": 48,
    "items_emitted": 30,
    "blocked_pages": 6,
    "l1_or_better_estimate": 8
  },
  "source_attempts": [
    {
      "source_id": "wellcee",
      "attempted_queries": 4,
      "zero_yield_reasons": []
    },
    {
      "source_id": "lianjia_mobile_list",
      "attempted_queries": 6,
      "blocked_reasons": ["detail_page_login_or_security_wall"]
    }
  ],
  "attempted_queries": [],
  "items": []
}
```

## 7. POC 验收口径

本阶段只验公开渠道：

- 候选总量不少于 20 条。
- 主推荐不少于 5 条。
- L1+ 不少于 8 条，或清楚说明待打开 URL 队列和失败原因。
- 覆盖不少于 3 类公开来源。
- rejected/blocked reason 100% 可审计。
- HTML 里 L0 只能出现在线索池，不能写成真实房源、已验证或主推荐。
