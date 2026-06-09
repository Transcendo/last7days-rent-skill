# Troubleshooting

## `python` command not found

本机可能只有 `python3`。可以在用户级 PATH 中创建轻量入口：

```bash
mkdir -p ~/.local/bin
ln -s "$(command -v python3)" ~/.local/bin/python
```

## `profile show --redacted` 返回未找到 profile

这是预期行为。先运行：

```bash
python skills/last7days-rent/scripts/last7days_rent.py profile init --office-anchor "上海五角场"
```

## fixture search 没有网络

MVP 的 `search --fixture` 必须离线运行，不依赖网络。它使用合成 P0 fixture 或内置 fixture。

## 报告被隐私守卫拦截

说明公开输出中仍包含手机号、微信号、私域群名、真实姓名、头像或截图来源身份线索。先修 `privacy.py` 的脱敏规则，再重新生成报告。

## 看到 P1/P2 来源进入报告

这是阻断失败。检查 `sources/registry.py`、`risk.py` 和 `normalize.py`，确保自如、我爱我家、58/安居客、豆瓣、小红书、微博、公众号、私域、WebSearch discovery、用户授权导入都不能进入 MVP listing pipeline。
