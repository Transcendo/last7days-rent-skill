# 来源政策

`last7days-rent-skill` 的目标是给用户一份可溯源、可联系的候选短名单，而不是承诺所有房源都已经验真。来源策略优先考虑可访问性、字段结构、联系方式可行动性和后续核验动作。

## 来源分层

| 层级 | 说明 | 默认处理 |
| --- | --- | --- |
| P0 | 可公开访问、字段相对稳定、适合结构化的来源 | 只有通过 promotion gate 后可进入 listing pipeline |
| P1 | 有价值但访问、授权或稳定性存在限制的来源 | 默认不自动进入正式 listing |
| P2 | 高噪声、高风险或强登录/私域依赖来源 | 只做风险情报或显式授权输入 |

## 当前 Search Provider

- Runtime web search JSON import：用于导入 Codex / Claude Code / Hermes 等宿主 Agent 的 web search 结果；默认优先使用，不需要 API key，不在 CLI 内触网。
- Brave Search API：用于发现网页级 SearchLead；默认 `freshness=pw`、`count<=20`、`result_filter=web`。
- Tavily API：用于发现网页级 SearchLead；默认 `search_depth=basic`、`include_answer=false`、`include_raw_content=false`。`extract` 只能作为用户显式开启的少量 URL 核验，不进入默认 live search。
- Exa API：用于发现网页级 SearchLead；使用 `includeDomains` 和发布时间窗口；`summary` 不用于填价格、地址、联系方式等事实字段。

Search provider 是发现层，不是验真层。runtime web search 导入结果、Brave/Tavily/Exa API 响应和 snippet 都不能直接写事实字段。无 API key、限流、鉴权失败、请求非法或 provider 5xx 都应进入 provider warning，不得伪造结果。

## 当前 P0 Listing Source

- 贝壳 / 链家 / Ke：SearchLead URL 域名命中 `ke.com/lianjia.com` 且 title/snippet 有租房语义时，可 promotion 为 L1。
- Wellcee：SearchLead URL 域名命中 `wellcee.com` 且 title/snippet 有租房语义时，可 promotion 为 L1。
- 房天下：SearchLead URL 域名命中 `fang.com` 且 title/snippet 有租房语义时，可 promotion 为 L1。
- 官方核验入口：只作为 `VerificationEvidence`，不作为高召回来源。

## 默认不自动采集的来源

- 自如、我爱我家。
- 58 / 安居客。
- 豆瓣、小红书、微博、公众号。
- 微信群、朋友圈、公司群、校友群。
- 其他需要登录、验证码、cookie、token 或批量反机器人绕过的来源。

这些来源后续可以通过合作接口、用户显式授权导入或人工核验方式重新评估，但不能在默认 live search 中自动采集。默认 live search 不启用 crawl，不启用登录态，不启用 Tavily extract 或 Exa full text。宿主 Agent web search 也只能作为公开网页发现能力使用，不能绕过验证码、登录墙或私域访问限制。

## 联系方式政策

可公开访问页面展示的联系方式是房源可用性的核心字段，应作为 `contact_methods` 保留。平台只提供站内联系时，报告应展示原始 URL 和联系动作说明。

核心短名单里的房源必须至少有一种可行动联系路径：

- 平台联系入口。
- 电话。
- 微信、QQ、飞书。
- 邮箱。
- 原帖联系说明。
- 用户授权导入联系人。

没有联系方式且没有可打开联系入口的候选，只能作为低价值线索或 warning，不能当成可行动房源推荐。

## 用户授权导入

用户可以显式提供公开 URL、本地文本或剪贴文本。导入内容按原文结构化，保留用户提供的联系方式，并记录 provenance。用户授权导入的候选最高为 L1，除非用户后续反馈确认。

不允许自动读取用户聊天记录、私域群、朋友圈、公司群或校友群。不得保存 cookie、token、secret 或登录态凭证。

## Runtime web search 和 Web Search API discovery

Codex / Claude Code / Hermes 等宿主 Agent 的 web search 结果默认优先导入为 `runtime_web_search` SearchLead。Brave/Tavily/Exa API 是 runtime 搜索没有 promoted listing 时的 fallback。

Web Search discovery 可以用于发现入口和来源分类，但搜索结果 snippet 不能直接转成正式房源。SearchLead 默认 `can_promote=false`；只有 URL 域名匹配 P0 allowlist，并且 title/snippet 至少能识别租房语义和可打开 URL，才可 promotion 为低置信 L1 ListingItem。

SearchLead/snippet 不能直接证明价格、发布时间、联系方式或仍在租。Search API 的 freshness 只能证明搜索索引或页面日期信号，不能等同于房源发布时间。

## 验证边界

- L1：单源结构化，有真实 URL 或用户授权导入证据，并有可行动联系路径。
- L2：多源佐证或重复出现，关键字段和联系路径基本一致。
- L3：用户联系确认或明确反馈仍在租、可看房。

平台编号、官方核验码、多源重复都不能单独把候选房源提升为 L3。
