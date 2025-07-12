# Dify 接入指南

> ⚠️ Dify 插件为高级版功能，用户需自行开发，Omni Bot SDK 已提供底层 Dify API 支持。如需直接使用官方插件，可联系作者获取闭源插件。

Dify 是一个强大的 LLM 应用开发平台，支持多种大模型和对话能力。Omni Bot SDK 支持通过插件方式集成 Dify，实现智能对话、知识库问答等功能。

## 1. 启用 Dify 插件

在 `config.yaml` 的 `plugins` 配置中，启用 `dify-bot-plugin`，并填写 Dify 的 API Key 及相关参数：

```yaml
plugins:
  dify-bot-plugin:
    enabled: true
    priority: 100
    dify_api_key: "你的 Dify API Key"
    dify_base_url: "https://api.dify.ai/v1"
    conversation_ttl: 180  # 会话过期时间（秒）
```

- `dify_api_key`：在 Dify 控制台获取的 API Key。
- `dify_base_url`：Dify 的 API 地址，通常为 `https://api.dify.ai/v1`。
- `conversation_ttl`：会话过期时间，单位为秒。
- `priority`：插件优先级，数值越大越优先。

## 2. 最简插件用法示例

Dify 插件会自动拦截文本消息，并调用 Dify API 进行智能回复。你只需在配置文件中正确填写参数并启用插件，无需手动调用。

如需自定义调用，可在自定义插件中这样使用：

```python
from omni_bot_sdk.plugins.interface import Plugin, PluginExcuteContext, SendTextMessageAction

class MyDifyDemoPlugin(Plugin):
    async def handle_message(self, context: PluginExcuteContext):
        # 获取用户消息内容
        message = context.get_message()
        # 伪代码：调用 Dify API 获取回复
        ai_reply = "这里是 Dify 返回的智能回复"
        # 回复用户
        context.add_response(
            # 这里只是演示，实际建议直接用官方 dify-bot-plugin
            SendTextMessageAction(
                content=ai_reply,
                target=message.contact.display_name,
                is_chatroom=message.is_chatroom,
            )
        )
```

> 推荐直接使用官方 `dify-bot-plugin`，无需重复造轮子。

## 3. 获取 Dify API Key

1. 注册并登录 [Dify 官网](https://dify.ai/)
2. 进入「API 密钥」页面，创建并复制你的 API Key
3. 将 API Key 填入 `config.yaml` 的 `dify_api_key` 字段

## 4. 常见问题

- **Q: Dify 返回 401/403 错误？**
  - 检查 API Key 是否正确，是否有调用权限。
- **Q: 如何切换模型？**
  - 在 Dify 后台切换模型，无需在插件中配置。
- **Q: 支持知识库问答吗？**
  - 支持，需在 Dify 后台配置知识库。

## 5. 参考链接

- [Dify 官方文档](https://docs.dify.ai/zh/)
- [Omni Bot SDK 插件开发](./plugins.md)

如有更多 Dify 集成问题，欢迎在社区或 Issue 区反馈。 