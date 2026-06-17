# 北京京东总部 POC 改造计划：NestHub 知识增强与 Agent Runtime 全渠道获源

日期：2026-06-14

状态：已按本计划落地第一版可执行 POC 链路，并完成一次公开 runtime 搜索验证

范围：`last7days-rent-skill`，只聚焦北京京东总部 / 亦庄经海路租房 POC。暂不泛化到北京其他办公点，也不改造成通用爬虫。

## 0. 本阶段纠正链路

手工 e2e 已经证明 profile 链路基本可用：用户能把京东总部、经海路、正规一居、预算目标 5000/最高 6000、优先 30 分钟内、全渠道收集、先保留再筛选等约束提交给系统。当前 POC 的问题不在“用户画像是否能表达需求”，而在“拿到的公开房源候选太少，且多数停留在 L0 搜索线索”。

本阶段因此只纠正获源和证据链路：

- 不重做 profile wizard 的交互体验。
- 不调整已通过手工 e2e 的核心 profile 语义。
- 不处理与中介私域库存对齐的问题。
- 不扩展到北京其他办公点。
- 聚焦北京京东总部：用 NestHub 生成先验知识，用 Agent runtime 执行公开渠道发现和详情页核验，用本地 engine 做准入、去重、排序和 HTML 工作台。

### 0.1 Baseline vs Target

| 指标 | 当前手工 e2e baseline | 本轮 POC target |
| --- | --- | --- |
| Profile 表达 | 已可表达京东总部、预算、户型、通勤、渠道偏好 | 保持现状，只作为输入约束消费 |
| 候选总量 | 约 13 条 | 不少于 20 条 |
| 主推荐 | 不稳定，依赖少量候选 | 不少于 5 条 |
| L1+ 候选 | 约 1 条 | 不少于 8 条，或给出待打开 URL 队列和失败原因 |
| 来源覆盖 | 豆瓣/少量公开页为主 | 不少于 3 类公开来源 |
| 详情页打开 | 预算和策略不足 | 默认最多打开 48 个详情页 |
| L0 处理 | 容易混入候选展示 | 只能进线索池，不得标成已验证 |
| 失败可审计 | 不足 | 每个来源记录搜索数、打开数、入池数、拒收数 |

## 1. 结论

当前 POC 链路已经能跑通 `profile wizard -> plan -> runtime evidence -> ingest -> render`，但召回少，核心原因不是“互联网没有房源”，而是：

1. Anchor Pack 只是一组关键词，没有把 NestHub 已沉淀的通勤圈、预算带、渠道策略、风险规则变成机器可执行计划。
2. Agent runtime 搜索执行还停留在“少量查询 + 摘要整理”，没有形成“发现页 -> 详情页 -> 字段核验 -> 拒收/入池”的漏斗。
3. Web search snippet 被保守降级是正确的，但当前缺少足够的详情页打开预算和结构化提取指令，所以大量候选停留在 L0。
4. 已启用 direct source 对北京亦庄支持不足：北京经海路、次渠、马驹桥等区域缺少 source-specific descriptor，容易退回平台首页或被风控/重定向阻断。
5. 中介手里的房源包含大量私域库存、门店库存、未公开转租和实时跟进状态，公开 web search 不可能完全等价；本阶段先不处理与中介库存对齐的问题，只把它作为能力边界，POC 聚焦“公开渠道候选池 + 详情页核验漏斗”。

目标应调整为：

> 把北京京东总部打造成一个可复用的 Anchor POC：用 NestHub 做决策知识底座，用 Agent runtime 做公开发现和页面核验，用本地 engine 做证据准入、去重、排序、风险解释和 HTML 工作台。

## 2. NestHub 内容如何使用

### 2.1 可用内容

线上 NestHub 页面：

- `https://nest-hub.eggcampus.com/docs/beijing/jd-headquarters-renting-guide`
- `https://nest-hub.eggcampus.com/llms-full.txt`

NestHub 仓库内可复用材料（仅作为开发查找线索，不写入 runtime evidence）：

- `data/bj-jd.md`
- `beijing/jingdong.md`
- `nest-hub/content/docs/cities/beijing/jd-headquarters-renting-guide.mdx`

当前判断：

- 线上页面适合作为公开决策知识源，标记 `source_url=https://nest-hub.eggcampus.com/docs/beijing/jd-headquarters-renting-guide`，`source_updated_at=2026-05-07`，`confidence=medium`。
- 本地 `data/bj-jd.md` 适合作为 legacy 小区 seed，不能作为实时价格事实源。
- 本地 MDX 与线上页面存在漂移，不能当作线上页面等价源码。

### 2.2 应进入 Anchor Pack 的内容

这些是稳定决策知识，适合结构化进 `beijing-jd-hq-yizhuang.json`：

- 办公锚点：京东北京总部、亦庄经海路、科创十一街、经海路站。
- 必须确认项：具体楼栋入口、园区门、班车站点、每周到岗、晚归频率。
- 通勤圈：
  - 0-2km 近场：经海路、通泰国际、定海园、锋创科技园。
  - 2-5km 主力圈：次渠、次渠南、禧瑞天著、次渠嘉园、次渠锦园、次渠南里。
  - 5-8km 面积圈：马驹桥、富力尚悦居、星悦国际、国风美仑、珠江四季悦城。
  - 生活补充圈：东石公园、万科城市之光、亦庄文化园、荣京东街、上海沙龙。
  - 兜底外圈：台湖、通州局部、旧宫、宋家庄，只作为低优先级扩圈。
- 预算带：1500-2500、2500-4000、4000-6000、6000-8500、8500+。这些只能作为软筛选和解释，不作为实时成交价。
- 风险标签：商水商电、隔断群租、班车末班、雨天通勤、夜归打车、二房东授权、合同主体、押金路径、服务费、中介费。
- 渠道策略：贝壳/链家建立价格锚点，房天下/58/安居客扩召回，豆瓣补公开转租；Wellcee、乐乎、泊寓、蜂客、城家、有巢等品牌公寓适合短期过渡；牛客和泛公开文章不进入 runtime 获源，先验统一从 NestHub 获取。

### 2.3 Anchor Pack 目标结构

`skills/last7days-rent/anchor_packs/beijing-jd-hq-yizhuang.json` 应从当前“少量关键词”升级为可执行的北京京东先验包。建议目标结构如下：

```json
{
  "anchor_id": "beijing-jd-hq-yizhuang",
  "city": "北京",
  "company": "京东",
  "guide_sources": [
    {
      "source_name": "NestHub 京东总部租房指南",
      "source_url": "https://nest-hub.eggcampus.com/docs/beijing/jd-headquarters-renting-guide",
      "source_updated_at": "2026-05-07",
      "usage": "guide_only_not_realtime_listing",
      "confidence": "medium"
    }
  ],
  "anchor": {
    "campus_name": "京东总部",
    "office_aliases": ["北京京东总部", "京东亦庄总部", "京东总部"],
    "address_keywords": ["亦庄", "经海路", "科创十一街"],
    "needs_confirmation": ["具体楼栋入口", "园区门", "班车站点", "每周到岗频率", "晚归频率"]
  },
  "commute_zones": [
    {
      "zone_id": "near_office",
      "label": "0-2km 近场",
      "priority": "A",
      "keywords": ["经海路", "通泰国际", "定海园", "锋创科技园"],
      "query_boost": ["步行", "骑行", "京东总部", "经海路"],
      "risk_checks": ["商水商电", "公寓属性", "居住登记"]
    },
    {
      "zone_id": "main_residential",
      "label": "2-5km 主力住宅圈",
      "priority": "A",
      "keywords": ["次渠", "次渠南", "禧瑞天著", "次渠嘉园", "次渠锦园", "次渠南里"],
      "query_boost": ["一居", "整租", "京东总部", "经海路"],
      "risk_checks": ["实际通勤", "晚归路线", "班车站点"]
    },
    {
      "zone_id": "space_budget_backup",
      "label": "5-8km 面积/预算备选",
      "priority": "B",
      "keywords": ["马驹桥", "富力尚悦居", "星悦国际", "国风美仑", "珠江四季悦城"],
      "query_boost": ["预算", "面积", "整租", "一居"],
      "risk_checks": ["通勤时间", "低价引流", "房源真实性"]
    }
  ],
  "budget_bands": [
    {
      "band_id": "target_5000",
      "min": 4000,
      "max": 5000,
      "usage": "preferred_match"
    },
    {
      "band_id": "max_6000",
      "min": 5000,
      "max": 6000,
      "usage": "acceptable_if_commute_or_quality_better"
    }
  ],
  "source_matrix": [
    {
      "source_tier": "P0",
      "source_name": "fang",
      "intents": ["price_anchor", "specific_listing"],
      "query_templates": ["site:fang.com/zf/bj {zone} 一居 租房", "{community} 京东总部 租房 房天下"],
      "detail_open_policy": "open_detail_or_list_items_first"
    },
    {
      "source_tier": "P1",
      "source_name": "douban_public_group",
      "intents": ["transfer_personal", "community_supply"],
      "query_templates": ["site:douban.com/group {zone} 京东总部 租房 一居", "site:m.douban.com/group {community} 转租 京东总部"],
      "detail_open_policy": "open_topic_page_then_extract_visible_fields"
    }
  ],
  "runtime_budget": {
    "max_search_queries": 45,
    "max_results_per_query": 8,
    "max_detail_pages_total": 48,
    "max_detail_pages_per_source": 8
  },
  "entry_policy": {
    "main_recommendation_min_trust": "L1",
    "l1_required": {
      "page_opened": true,
      "min_visible_core_fields": 3,
      "required_fields": ["source_url", "observed_at", "raw_excerpt"]
    },
    "l0_policy": "lead_pool_only"
  }
}
```

这个 schema 的验收标准：

- `plan` 能从 `commute_zones`、`source_matrix`、`runtime_budget` 生成 search brief。
- 不在 `profile_wizard.py` 里重复维护区域和来源列表。
- NestHub 内容只作为 guide source 和 query/risk seed，不作为实时房源事实。

### 2.4 不应进入实时匹配的内容

这些只能做解释和风险提示，不能当作自动过滤或实时房源事实：

- 单个小区历史租金。
- “京东员工多”“班车房”“性价比最高”等主观表述。
- `in 北京`、`莲水怡园` 等负面点名，不应在没有当前证据时自动封禁。
- 同事群、校友群、公司群等私域来源，不得自动采集。
- 公司房补、班车规则、楼栋入口、团队作息，必须由用户或当前公开信息确认。

## 3. Agent Runtime 全渠道获源方案

### 3.1 全渠道不是全自动爬虫

POC 的“全渠道”定义：

- 使用 Agent runtime 的 web search/browser 能力做公开发现和页面核验。
- 本地 engine 不绕登录墙、验证码、cookie、token、私域群组或反爬。
- Web search snippet 只能生成 `SourceCandidate` / L0，不直接变正式 listing。
- 正式 listing 来自详情页、平台页、允许的 P0 adapter，或被打开页面后足够字段可见的 evidence。

### 3.2 渠道分层

| 层级 | 渠道 | 获取方式 | 入池策略 |
| --- | --- | --- | --- |
| P0 | 贝壳 / 链家 / Ke | search 发现 + 可访问页面 adapter / mobile 页面 | 满足 L1 硬条件后入主候选，多源重复可 L2 |
| P0 | Wellcee 详情页 | search 发现具体 URL + JSON-LD 解析 | 满足 L1 硬条件后入主候选 |
| P0 | 房天下 | search 发现 + 页面 parser | 满足 L1 硬条件后入主候选，强去重 |
| P0 | 官方核验入口 | 用户提供编号或公开页面 | 只做 verifier，不生成 listing |
| 后续 | 用户/中介授权导入 | URL、文本、截图、经纪人发来的房源清单 | 本阶段不实现，仅保留为后续方向 |
| P1 | 自如 / 品牌公寓 / 园区公寓 | search 发现 + browser 打开页面 | 满足 L1 硬条件后入主候选，服务费和退租条款强风险 |
| P1 | 豆瓣公开小组 | search 发现 + 公开详情页 | 默认 L0，详情页打开且字段足够可 L1 |
| P1 | 乐乎 / 泊寓 / 蜂客 / 城家 / 有巢 | search 发现 + browser 打开公开页 | 作为品牌公寓/过渡候选，满足 L1 硬条件后入池 |
| P2 | 58 / 安居客 | search 发现 + mobile 页面优先 | 高召回高风险，默认 L0，打开详情后可 L1 |
| P2 | 小红书 / 抖音 / 微博 / B站 | search 发现区域体验和转租线索 | 默认 L0，不直接当正式房源 |
| 排除 | 微信群 / 公司群 / 同事私聊 | 本阶段不采集 | 只记录为隐私边界，禁止自动读取 |

L1 不是平台默认值，而是 evidence 质量等级。任何渠道都必须满足以下硬条件才能成为 L1：

- `page_opened=true`，且页面不是登录墙、验证码页、app下载墙或纯搜索结果页。
- `source_url` 是可回访的公开 URL，`observed_at` 是本次采集时间。
- `raw_excerpt` 包含页面可见原文摘录。
- 至少 3 类核心字段可见：价格、片区/小区、户型/面积、联系方式入口、发布时间/更新时间。
- 不输出原发帖人姓名、手机号、微信号、群名或私域原文。
- 不满足上述条件时只能进入 L0 线索池，并写明缺失字段或阻断原因。

### 3.3 为什么现在召回少

当前 runtime 执行更像“人工搜索摘要”：

```text
少量 query -> 搜索结果 snippet -> 手工挑 13 条 -> ingest -> 12 条 L0 + 1 条 L1
```

要变成可用，应改成“多阶段漏斗”：

```text
Anchor Pack
  -> zone/source/query matrix
  -> discovery search
  -> URL classification
  -> detail open queue
  -> field extraction
  -> evidence validation
  -> listing pool merge
  -> HTML decision desk
```

关键不是多搜几条，而是每个搜索结果必须经过 URL 分类和详情页打开，尽量把 L0 推进到 L1；推进不了的要记录原因。

### 3.4 Runtime 执行预算

建议北京京东 POC 的默认预算：

```json
{
  "target_candidates_total": 30,
  "target_main_recommendations": 5,
  "target_l1_or_better": 8,
  "max_search_queries": 45,
  "max_results_per_query": 8,
  "max_detail_pages_total": 48,
  "max_detail_pages_per_source": 8,
  "expand_if_l1_below": 5,
  "stop_after_consecutive_empty_batches": 2
}
```

查询预算分配：

| 批次 | 查询数 | 目标 |
| --- | --- | --- |
| P0 价格锚点 | 10 | 贝壳、链家、链家移动列表、房天下、Wellcee |
| 近场区域 | 8 | 经海路、通泰国际、定海园、锋创科技园 |
| 主力住宅圈 | 8 | 次渠、次渠南、次渠嘉园、次渠锦园、禧瑞天著 |
| 面积/预算备选 | 6 | 马驹桥、富力尚悦居、星悦国际、国风美仑 |
| 转租/个人房源 | 4 | 豆瓣公开小组 |
| 品牌公寓/过渡 | 9 | Wellcee、自如、乐乎、泊寓、蜂客、城家、有巢等公开入口 |

### 3.5 Runtime input/output contract

当前 CLI 已有可落地链路：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile wizard inspect --format json

python skills/last7days-rent/scripts/last7days_rent.py plan \
  --anchor-id beijing-jd-hq-yizhuang \
  --output /tmp/jd-search-brief.json \
  --explain

# Agent runtime 读取 /tmp/jd-search-brief.json，执行公开 web search/browser，
# 并写出 /tmp/jd-runtime-evidence.json。

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

`plan --output` 应产出 runtime 可直接执行的 search brief：

```json
{
  "anchor_id": "beijing-jd-hq-yizhuang",
  "profile_constraints": {
    "budget_target": 5000,
    "budget_max": 6000,
    "preferred_bedrooms": 1,
    "commute_minutes": 30,
    "source_strategy": "all_public_channels"
  },
  "search_batches": [
    {
      "batch_id": "p0_price_anchor",
      "intent": "price_anchor",
      "priority": 1,
      "sources": ["fang", "beike_lianjia", "wellcee"],
      "queries": [
        {
          "query_id": "fang-near-office-001",
          "query": "site:fang.com/zf/bj 经海路 一居 租房 京东总部",
          "zone_id": "near_office",
          "expected_url_classes": ["platform_listing_detail", "platform_list_page"]
        }
      ],
      "max_results_per_query": 8,
      "max_detail_pages": 8
    }
  ],
  "run_budget": {
    "max_search_queries": 45,
    "max_detail_pages_total": 48,
    "expand_if_l1_below": 5
  },
  "collection_rules": {
    "l0_policy": "lead_pool_only",
    "l1_requires_page_opened": true,
    "min_visible_core_fields_for_l1": 3,
    "privacy_policy": "redact_private_identity"
  }
}
```

Agent runtime 执行 search brief 后，必须写出 evidence JSON：

```json
{
  "runtime_meta": {
    "runtime_name": "codex",
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
  "items": []
}
```

`ingest --validate` 的成功标准：

- schema 合法。
- 每个 item 都有 `evidence_id`、`batch_id`、`query_id`、`source_url`、`observed_at`。
- `candidate_l1` 必须满足 L1 硬条件。
- 被阻断的页面不得静默丢弃，必须进入 `blocked/rejected` 统计或 evidence item 的 `reject_reasons`。
- 同一 URL、同一小区同价同面积、同一帖子跨域转载要可合并或解释。

### 3.6 Search matrix

不要只搜 `北京 京东总部 一居室 6000 租房`。应生成矩阵：

```text
{city} {office_alias} {bedroom_label} {budget_max}以内 租房
{zone} {community} {bedroom_label} 租房 京东总部
site:douban.com/group {zone} 京东总部 租房 一居
site:m.douban.com/group {zone} 租房 经海路
site:bj.zu.anjuke.com {community} 一居 京东总部
site:m.58.com/bj/zufang {zone} 一居 租房
site:fang.com/zf/bj {zone} 一居 租房
site:m.ke.com/chuzu/bj {zone} 公寓 京东总部
{community} 京东总部 班车 租房
{zone} 转租 一居 免中介费 京东总部
```

每条 query 还要带意图：

- `price_anchor`
- `specific_listing`
- `community_supply`
- `transfer_personal`
- `brand_apartment`
- `risk_context`

这样后续 evidence 才知道该把搜索结果当房源、当价格参考，还是当风险/通勤解释。

### 3.7 URL classification

Agent runtime 搜到 URL 后，先分类，不要马上入池：

| URL 类型 | 处理 |
| --- | --- |
| platform listing detail | 打开详情页，抽字段，候选 L1 |
| platform list/community page | 抽出列表条目或进入 detail queue |
| community topic | 打开正文，抽字段，脱敏，候选 L0/L1 |
| guide/article | 不入 listing，进入 context evidence |
| video/social search result | 只做 L0 source candidate 或风险上下文 |
| login/captcha/app wall | 记录 blocked，不绕过 |
| duplicated/canonicalized URL | merge observation |

### 3.8 Runtime evidence JSON 增强

当前 evidence 字段够基础，但不够表达漏斗。建议每个 item 增加：

```json
{
  "evidence_id": "jd-20260614-001",
  "batch_id": "community_transfer",
  "query_id": "douban-ciqunan-001",
  "query": "site:douban.com/group 次渠南 京东总部 租房 一居",
  "collected_via": "runtime_web_search_and_browser",
  "source_url": "https://m.douban.com/group/topic/...",
  "canonical_url": "https://www.douban.com/group/topic/...",
  "source_name": "豆瓣亦庄租房小组",
  "source_domain": "douban.com",
  "source_type": "community_post",
  "source_tier": "P1",
  "page_opened": true,
  "url_class": "community_topic",
  "listing_candidate_status": "candidate_l1",
  "title": "京东总部附近次渠南里一居室出租",
  "snippet": "...",
  "raw_excerpt": "...",
  "observed_at": "2026-06-14T10:30:00+08:00",
  "visible_fields": {
    "price_text": "待核验",
    "area_text": "60平米",
    "layout_text": "一居室",
    "community": "次渠南里",
    "district_hint": "次渠南 / 京东总部附近"
  },
  "normalized_fields": {
    "price_monthly": null,
    "area_sqm": 60,
    "bedrooms": 1
  },
  "contact_path": {
    "type": "platform_entry",
    "entry_url": "https://www.douban.com/group/topic/...",
    "contact_visibility": "platform_required"
  },
  "runtime_actions": [
    "search_result_seen",
    "page_opened",
    "fields_extracted"
  ],
  "reject_reasons": [],
  "risk_flags": [
    "price_missing",
    "community_post"
  ]
}
```

## 4. 暂缓项：中介库存差距

这部分本阶段先不处理，后续再单独设计。

当前 POC 不做：

- 中介房源清单导入。
- 微信/飞书/短信截图 OCR 导入。
- 私域群、公司群、同事私聊采集。
- 中介报价对比模式。
- 以中介库存覆盖率作为验收指标。

这里只保留一个边界判断：公开搜索不可能完全对齐中介手里的实时库存。中介优势在于：

- 私域库存和门店内部房源。
- 实时知道是否可看、是否已租、钥匙在谁手里。
- 能快速推相似房源。
- 有同小区大量历史成交和业主委托信息。

所以本阶段验收口径应改为：把公开渠道召回、详情页打开、字段抽取、证据准入、去重和 HTML 展示做到稳定；不要要求系统和中介私域库存做数量对比。

## 5. 代码改造任务

实施顺序必须围绕“先让 plan 变聪明，再让 runtime 按计划执行，再让 ingest 严格准入”。不要先改 HTML，也不要先扩大城市。

### Phase 1：Anchor Pack 与计划生成

1. 修改 `skills/last7days-rent/anchor_packs/beijing-jd-hq-yizhuang.json`
   - 增加 `anchor`、`source`、`commute_zones`、`budget_bands`、`scenario_rules`、`risk_checks`、`source_matrix`。
   - 标记 NestHub 线上指南为 `guide_only_not_realtime_listing`。
   - 输出必须能覆盖经海路、次渠/次渠南、马驹桥三个核心圈层。

2. 收窄 `skills/last7days-rent/scripts/lib/profile_wizard.py` 改动
   - 本阶段不重做 profile wizard。
   - 只允许做低风险改动：从 anchor pack 读取默认办公锚点和 `needs_confirmation`，避免区域、小区、来源列表在 wizard 和 anchor pack 中重复维护。
   - 不新增用户问题，除非缺失字段会直接阻断 search brief。

3. 修改 `skills/last7days-rent/scripts/lib/anchor_pack.py`
   - `plan` 输出 search matrix，而不是平铺 query。
   - 明确 P0/P1/P2、`entry_policy`、`max_detail_pages`、`expected_output`。
   - `plan --output /tmp/jd-search-brief.json --explain` 必须可生成 runtime input/output contract 中定义的 search brief。

Phase 1 完成标准：

- `python skills/last7days-rent/scripts/last7days_rent.py plan --anchor-id beijing-jd-hq-yizhuang --output /tmp/jd-search-brief.json --explain` 成功。
- `/tmp/jd-search-brief.json` 包含 `search_batches`、`run_budget`、`collection_rules`。
- snapshot test 能证明 query matrix 使用了 NestHub 派生的区域和渠道策略。

### Phase 2：Runtime acquisition 协议

4. 修改 `docs/runtime-adapter-contract.md`
   - 增加 discovery queue、detail queue、blocked queue、rejected queue。
   - 明确 Agent runtime 必须打开详情页才能产出 L1。
   - 增加本文件 3.5 中的 search brief 和 evidence JSON 示例。

5. 修改 `skills/last7days-rent/scripts/lib/agent_evidence.py`
   - 强化 validator：source tier、page_opened、observed_at、domain match、normalized consistency、privacy fields。
   - 输出 rejected evidence，不能静默丢弃。
   - `candidate_l1` 不满足 L1 硬条件时自动降级为 L0 或 reject，并记录原因。

6. 新增 `docs/jd-runtime-search-playbook.md`
   - 写清 Agent runtime 如何按 query matrix 执行。
   - 包含搜索模板、打开策略、字段抽取、阻断记录。
   - 包含一次北京京东运行的 checklist：执行多少 query、打开多少 detail、何时扩圈、何时停止。

Phase 2 完成标准：

- `ingest --validate` 能拒绝伪 L1 evidence。
- 被验证码、登录墙、app下载墙阻断的 URL 有明确 `blocked/rejected` 记录。
- evidence fixture 覆盖 L0、L1、blocked、rejected 四种路径。

### Phase 3：Source descriptor 与入池逻辑

7. 修改 `skills/last7days-rent/scripts/lib/sources/query.py`
   - 补北京京东 source descriptors。
   - 一个 source 可以生成多个区域 URL / search descriptor。
   - 至少覆盖房天下、贝壳/链家、链家移动列表、Wellcee、豆瓣公开帖、58/安居客 mobile 入口、乐乎/泊寓/品牌公寓公开入口。

8. 修改 `skills/last7days-rent/scripts/lib/listing_pool.py`
   - 入池时计算 `match_score`、`risk_score`、`recommendation_band`。
   - L0 可保留在线索池，主推荐要求 L1+。
   - 增强弱去重和 L2 判定。
   - 同一 URL、同一小区同价同面积、同一标题跨平台转载应合并或标记疑似重复。

9. 修改 `skills/last7days-rent/scripts/lib/risk.py`
   - 增加京东/亦庄风险标签：商水商电、班车未核验、夜归不稳、隔断群租、二房东授权缺失、费用不清。

Phase 3 完成标准：

- 同一份 runtime evidence 导入后，L0 只进入线索池，L1+ 才能进入主推荐候选。
- 来源覆盖、阻断数量、拒收原因可以从 listing pool 或 evidence summary 追溯。
- 去重结果可解释，不把不同房源误合并成一条。

### Phase 4：HTML 工作台

10. 修改 `skills/last7days-rent/scripts/lib/render.py`
    - 改成四区工作台：主推荐、线索池、拒收、来源覆盖。
    - 卡片展示通勤圈、推荐理由、风险、联系路径、证据数量、最后打开时间、下一步问题。

11. 增加状态操作字段
    - `new`
    - `shortlisted`
    - `contacted`
    - `scheduled`
    - `viewed`
    - `rejected`
    - `stale`
    - `leased`

Phase 4 完成标准：

- HTML 首页能一眼看到：主推荐、线索池、拒收、来源覆盖。
- 每条主推荐显示 trust level、证据数量、最后打开时间、推荐理由、风险标签、下一步核验问题。
- L0 不得使用“真实房源”“已验证”“推荐”这类文案。

### Phase 5：测试与验收

12. 新增/更新 tests
    - Anchor Pack schema test。
    - 北京 JD search brief snapshot test。
    - 北京 source descriptor test。
    - Evidence validator rejection test。
    - L0/L1/L2 trust transition test。
    - HTML 工作台字段 test。
    - 隐私输出 test。

13. 新增 POC fixture
    - `tests/fixtures/search_briefs/jd_hq_search_brief.json`
    - `tests/fixtures/evidence/jd_hq_runtime_evidence_l0_l1_blocked.json`
    - `tests/fixtures/pools/jd_hq_listing_pool_expected.json`

Phase 5 完成标准：

- `python -m pytest` 通过。
- 至少一条 end-to-end fixture 能覆盖：search brief -> runtime evidence -> ingest validate -> listing pool -> render HTML。
- README 或 playbook 有一段可复制的北京京东 POC 运行命令。

## 6. POC 验收标准

### 成功阈值

一次完整北京京东运行应满足，并且要相对 baseline 有可量化提升：

- 总候选不少于 20 条。
- 主推荐不少于 5 条。
- L1+ 不少于 8 条，或 L1+ 不足时必须清楚说明原因和待打开 URL 队列。
- 覆盖不少于 3 类来源。
- 每条主推荐有来源 URL、价格或缺价说明、小区/片区、户型/面积、联系路径、风险标签、下一步核验问题。
- 至少 80% 候选具备 5 类核心字段中的 4 类：价格、小区/片区、户型/面积、来源、采集时间。
- rejected reason 100% 可审计。
- HTML 单文件可打开。
- JSON evidence 可复跑 merge。
- 隐私检查 100% 通过。

### 对比验收

| 指标 | Baseline | Target | 验收方法 |
| --- | --- | --- | --- |
| 候选总量 | 约 13 | >= 20 | listing pool item count |
| L1+ | 约 1 | >= 8 | trust level summary |
| 主推荐 | 不稳定 | >= 5 | HTML main recommendations |
| 来源类型 | 少量 | >= 3 | source coverage summary |
| 详情页打开 | 不足 | <= 48 且有记录 | execution summary |
| 拒收可解释 | 不足 | 100% | rejected reasons |

### 失败阈值

任一情况视为 POC 未达标：

- 有效候选少于 10 条。
- 主推荐少于 3 条且没有明确下一轮扩圈计划。
- 超过 30% 候选缺少关键字段且未记录原因。
- 无法解释每个来源搜了多少、打开多少、入池多少、失败多少。
- HTML 把 L0 写成“已验证”或“真实房源”。
- 输出原发帖人姓名、手机号、微信号、群名或私域原文。

## 7. Review 重点

请重点 review 这些取舍：

1. 是否认可本阶段暂不处理中介私域库存，POC 目标只聚焦公开候选池 + 详情页核验漏斗。
2. 是否认可 L0 可以展示，但必须放在线索池；主推荐尽量要求 L1+。
3. 是否认可 NestHub 线上指南作为中等置信的 guide source，本地旧稿只作为 legacy seed。
4. 是否认可先把北京京东做到完美，再复制到北京其他办公点。
5. 是否认可本阶段不重做 profile wizard，只消费已确认 profile 并优化获源链路。
6. 是否认可成功阈值：20 条候选、5 条主推荐、8 条 L1+、3 类来源覆盖。

## 8. 当前实施结果

本文件已不只是方案草案。当前仓库已按 Phase 1-5 落地第一版可执行链路，重点是让北京京东总部 POC 具备“先验知识 -> runtime search brief -> evidence validate -> listing pool -> HTML 工作台”的纵向闭环。

### 8.1 已落地内容

Phase 1：Anchor Pack 与计划生成

- 已升级 `skills/last7days-rent/anchor_packs/beijing-jd-hq-yizhuang.json`。
- 已加入 NestHub guide source、北京京东办公锚点、经海路/次渠/马驹桥等核心圈层、预算带、风险项、source matrix、runtime budget 和 entry policy。
- 已重写 `skills/last7days-rent/scripts/lib/anchor_pack.py`，`plan --output` 现在输出 `profile_constraints`、`search_batches`、`run_budget`、`collection_rules` 和 `execution_contract`。

Phase 2：Runtime acquisition 协议

- 已更新 `docs/runtime-adapter-contract.md`。
- 已新增 `docs/jd-runtime-search-playbook.md`。
- 已增强 `skills/last7days-rent/scripts/lib/agent_evidence.py` validator：伪 L1、source domain mismatch、隐私泄漏、非法 URL、字段缺失都会返回字段级错误。

Phase 3：Source descriptor 与入池逻辑

- 已扩展 `skills/last7days-rent/scripts/lib/sources/query.py`，北京京东 discovery descriptor 覆盖房天下、贝壳/链家、链家移动列表、Wellcee、58、安居客、豆瓣公开帖、乐乎、泊寓和品牌公寓公开入口。
- 已增强 `skills/last7days-rent/scripts/lib/listing_pool.py`，支持 `recommendation_band=main/lead_pool`、`source_coverage`、`execution_summary`、`rejected_items`、`match_score`、`risk_score` 和 L0/L1 分层。
- 已补充 `skills/last7days-rent/scripts/lib/risk.py` 的亦庄/京东风险项：商水商电、隔断群租、二房东授权、班车/晚归、费用项待确认。

Phase 4：HTML 工作台

- 已重写 `skills/last7days-rent/scripts/lib/render.py`。
- HTML 已拆成四区：主推荐、线索池、拒收 / 阻断、来源覆盖。
- L0 明确只能显示在线索池，页面文案不把 L0 写成真实房源、已验证或主推荐。

Phase 5：测试与 fixture

- 已新增北京京东 profile fixture：`tests/fixtures/profile/jd_hq_profile.json`。
- 已新增 search brief fixture：`tests/fixtures/search_briefs/jd_hq_search_brief.json`。
- 已新增 L0/L1/blocked runtime evidence fixture：`tests/fixtures/evidence/jd_hq_runtime_evidence_l0_l1_blocked.json`。
- 已新增 expected listing pool fixture：`tests/fixtures/pools/jd_hq_listing_pool_expected.json`。
- 已新增 `tests/test_jd_poc_runtime.py`，覆盖 search brief -> evidence validate -> listing pool -> render HTML。

### 8.2 当前验证结果

已执行：

```bash
python -m pytest -q
```

结果：

```text
58 passed
```

已执行：

```bash
python skills/last7days-rent/scripts/last7days_rent.py plan \
  --profile tests/fixtures/profile/jd_hq_profile.json \
  --anchor-id beijing-jd-hq-yizhuang \
  --output tests/fixtures/search_briefs/jd_hq_search_brief.json \
  --explain

python skills/last7days-rent/scripts/last7days_rent.py ingest \
  --evidence tests/fixtures/evidence/jd_hq_runtime_evidence_l0_l1_blocked.json \
  --validate

python skills/last7days-rent/scripts/last7days_rent.py ingest \
  --evidence tests/fixtures/evidence/jd_hq_runtime_evidence_l0_l1_blocked.json \
  --output-pool tests/fixtures/pools/jd_hq_listing_pool_expected.json
```

验证结论：

- search brief 已包含 6 个 batch：`p0_price_anchor`、`near_office`、`main_residential`、`space_budget_backup`、`transfer_personal`、`brand_apartment`。
- runtime budget 已提升到 45 条 query、48 个详情页、8 条 L1+ 目标。
- L1 fixture 能进入主推荐。
- L0 fixture 只能进入线索池。
- app wall fixture 进入拒收 / 阻断。
- HTML 能展示主推荐、线索池、拒收 / 阻断、来源覆盖。

### 8.3 真实公开 runtime 搜索验证

已按 `docs/jd-runtime-search-playbook.md` 用公开 web search/browser 执行一轮北京京东总部搜索，并将 evidence、listing pool 和 HTML report 落盘：

- Evidence：`docs/runtime-evidence/jd-hq-public-runtime-evidence-2026-06-14.json`
- Listing pool：`docs/runtime-evidence/jd-hq-public-runtime-pool-2026-06-14.json`
- HTML report：`docs/runtime-evidence/jd-hq-public-runtime-report-2026-06-14.html`

验证命令：

```bash
python skills/last7days-rent/scripts/last7days_rent.py ingest \
  --evidence docs/runtime-evidence/jd-hq-public-runtime-evidence-2026-06-14.json \
  --validate

python skills/last7days-rent/scripts/last7days_rent.py ingest \
  --evidence docs/runtime-evidence/jd-hq-public-runtime-evidence-2026-06-14.json \
  --output-pool docs/runtime-evidence/jd-hq-public-runtime-pool-2026-06-14.json

python skills/last7days-rent/scripts/last7days_rent.py render \
  --pool docs/runtime-evidence/jd-hq-public-runtime-pool-2026-06-14.json \
  --output docs/runtime-evidence/jd-hq-public-runtime-report-2026-06-14.html
```

结果：

```json
{
  "listings": 20,
  "main": 17,
  "l1_or_better": 17,
  "source_count": 5,
  "rejected": 2,
  "trust_levels": {
    "L0": 3,
    "L1": 16,
    "L2": 1,
    "L3": 0
  },
  "sources": [
    "58",
    "安居客",
    "房天下",
    "豆瓣公开小组",
    "豆瓣公开小组列表"
  ]
}
```

对照第 6 节成功阈值：

| 指标 | Target | 本次真实公开 runtime 结果 | 状态 |
| --- | --- | --- | --- |
| 候选总量 | >= 20 | 20 | 通过 |
| 主推荐 | >= 5 | 17 | 通过 |
| L1+ | >= 8 | 17 | 通过 |
| 来源类型 | >= 3 | 5 | 通过 |
| 拒收可解释 | 100% | 2 条 rejected 均有原因 | 通过 |
| HTML L0 文案 | 不得写成已验证 | L0 只在线索池，footer 明确“L0 不代表已验证房源” | 通过 |

本次真实验证说明：NestHub 先验 + search matrix + detail/list-page opening budget 确实改善了召回数量和证据分层。公开渠道 POC 已达到当前阶段目标。

仍需注意：

- L1 代表“公开页面已打开且字段足够”，不代表房源仍在租。
- L3 仍为 0，因为本阶段没有做联系、约看、实看反馈。
- 58 移动端本轮仍表现为阻断/不可稳定抽取，已进入 rejected，而不是被伪装成正式候选。
