# MVP Boundaries

## P0 来源

MVP 只允许这些 source 进入 listing pipeline：

- 贝壳 / 链家 / Ke 列表：P0，访问等级 A/B，默认 L1。
- Wellcee JSON-LD：P0，访问等级 A，默认 L1。
- 房天下：P0，访问等级 A/B，默认 L1。
- 官方核验入口：P0 校验层，只输出 `VerificationEvidence`，不作为高召回来源。

## 非 MVP 来源

以下来源必须在 registry 中标记为 `disabled` 或 `non_mvp`，不能进入 MVP listing pipeline：

- 自如。
- 我爱我家。
- 58 / 安居客。
- 豆瓣。
- 小红书。
- 微博。
- 公众号。
- 微信群、朋友圈、公司群、校友群。
- 私域内容。
- WebSearch discovery。
- 用户授权导入。

后续阶段可以重新评估 P1/P2，但不得混入当前 MVP scope。

## 隐私边界

MVP 不保存或输出：

- 手机号明文。
- 微信号明文。
- 私域群名。
- 原发帖人真实姓名。
- 头像或截图来源身份线索。
- cookie、token、secret。
- 用户真实私聊截图。

即使 MVP 不做私域导入，也必须有隐私守卫测试，确保敏感文本误入时不会出现在公开报告里。

## 验证边界

L1 不能写成“已验真”。L3 只能来自用户联系确认或明确反馈。官方核验入口和平台编号是证据，不等于线下真实性承诺。

## 输出边界

报告可以显示脱敏来源类型、平台 URL、字段 provenance、核验问题和行动计划。报告不能显示私人联系方式、群名、真实姓名或未授权私域身份线索。
