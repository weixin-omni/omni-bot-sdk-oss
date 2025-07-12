# 消息处理

Omni Bot SDK 的消息处理机制高度模块化，支持多种消息类型、插件链式处理、上下文注入和自动化响应。核心流程如下：

## 1. 消息流转全景

1. **消息监听**  
   SDK 通过数据库轮询准实时监听微信消息。
2. **消息解析**  
   收到原始消息后，使用消息工厂（MessageFactory）自动识别类型（文本、图片、语音、文件、系统等），并构建为统一的消息对象（如 `TextMessage`、`ImageMessage`）。
3. **上下文注入**  
   每条消息会自动注入丰富的上下文信息，包括联系人、群聊、用户信息、数据库句柄等，便于插件开发者灵活处理。
4. **插件链分发**  
   消息对象和上下文会依次传递给所有已启用插件的 `handle_message` 方法。插件可根据优先级排序，链式处理消息。
5. **中断与响应**  
   插件可通过 `should_stop` 机制中断后续插件处理，或通过 `add_response` 返回自动化动作（如回复、RPA操作）。
6. **异常与去重**  
   SDK 内部自动处理插件异常，保证单个插件异常不会影响整体消息流转。重复消息、无效消息会被自动过滤。

## 2. 支持的消息类型

SDK 支持微信绝大多数消息类型，包括但不限于：

- 文本消息（TextMessage）
- 图片消息（ImageMessage）
- 文件消息（FileMessage）
- 语音消息（AudioMessage）
- 视频消息（VideoMessage）
- 表情包（EmojiMessage）
- 链接/小程序/名片/红包/转账/系统消息等

每种消息类型都封装为独立的数据类，支持内容解析、格式化、转文本等操作。

## 3. 插件链与上下文机制

- 插件链采用优先级排序，依次调用每个插件的 `handle_message` 方法。
- 每个插件可访问 `PluginExcuteContext`，获取当前消息、上下文、历史响应、错误等。
- 插件可通过 `add_response` 返回自动化动作（如回复消息、触发RPA），也可通过 `should_stop` 中断后续插件处理。
- 插件链支持热重载，开发者可随时增删插件，无需重启主程序。

## 4. 典型插件处理流程

```python
async def handle_message(self, context: PluginExcuteContext):
    message = context.get_message()
    # 判断消息类型
    if message.local_type == MessageType.Text:
        # 处理文本消息
        if '你好' in message.content:
            context.add_response(
                SendTextMessageAction(
                    content='你好，有什么可以帮您？',
                    target=message.contact.display_name,
                    is_chatroom=message.is_chatroom,
                )
            )
            context.should_stop = True  # 阻止后续插件处理
```

## 5. 异常与去重机制

- 插件处理异常会被自动捕获并记录日志，不影响主流程。
- SDK 内部自动去重，防止重复消息被多次处理。
- 支持消息上下文扩展，便于实现多轮对话、上下文感知等高级功能。

## 6. 高级用法

- 支持自定义消息类型扩展
- 支持多线程/异步消息处理，性能优异
- 支持消息队列分发、会话隔离、群聊/私聊自动区分

---

如需补充具体插件开发示例或消息类型扩展方法，请在github仓库提交issue。 