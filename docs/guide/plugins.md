# 插件开发

Omni Bot SDK 支持插件化架构，开发者可以通过自定义插件，扩展机器人的消息处理能力和自动化操作。插件开发简单、灵活，支持热重载和优先级排序。

## 插件开发流程

1. **继承基类**  
   所有插件需继承 `Plugin` 抽象基类（位于 `omni_bot_sdk.plugins.interface`），实现核心接口。

2. **实现必要方法**  
   - `get_plugin_name(self) -> str`：返回插件唯一名称
   - `get_plugin_description(self) -> str`：返回插件描述
   - `get_priority(self) -> int`：返回插件优先级（数字越大越先执行）
   - `get_plugin_config_schema(cls) -> Type[BaseModel]`：返回插件配置的 Pydantic schema
   - `async handle_message(self, context: PluginExcuteContext)`：插件的核心消息处理逻辑

3. **插件配置**  
   插件配置通过 `config.yaml` 的 `plugins` 字段进行集中管理。每个插件可定义自己的配置 schema，自动校验。

4. **插件注册与加载**  
   插件需通过 Python entry_points 机制注册到 `omni_bot.plugins` 组，或直接放入 SDK 的插件目录。插件管理器会自动发现、加载并按优先级排序。

5. **消息处理链**  
   插件按优先级依次处理消息。可通过 `context.should_stop = True` 中断后续插件处理。

## 插件基类主要接口

- `handle_message(context: PluginExcuteContext)`：异步消息处理主入口
- `add_rpa_action(action)` / `add_rpa_actions(actions)`：向 RPA 队列添加自动化动作
- `get_plugin_config(key, default)`：获取插件配置项
- `reload_plugin_config()`：热重载插件配置
- `get_plugin_config_schema()`：返回配置 schema（Pydantic）

## 最简单的插件开发 Demo

下面是一个最简单的“自发消息拦截”插件示例：

```python
from omni_bot_sdk.plugins.interface import Plugin, PluginExcuteContext
from pydantic import BaseModel

class SelfMsgPluginConfig(BaseModel):
    enabled: bool = True
    priority: int = 1000

class SelfMsgPlugin(Plugin):
    priority = 1000
    name = "self-msg-plugin"

    def __init__(self, bot=None):
        super().__init__(bot)
        self.priority = getattr(self.plugin_config, "priority", self.__class__.priority)

    def get_priority(self) -> int:
        return self.priority

    async def handle_message(self, context: PluginExcuteContext):
        message = context.get_message()
        if message.is_self:
            self.logger.info("检测到是自己的消息，直接拦截")
            context.should_stop = True
        else:
            context.should_stop = False

    def get_plugin_name(self) -> str:
        return self.name

    def get_plugin_description(self) -> str:
        return "拦截自己发送的消息，防止进入后续插件处理"

    @classmethod
    def get_plugin_config_schema(cls):
        return SelfMsgPluginConfig
```

## 插件配置示例

在 `config.yaml` 中添加：

```yaml
plugins:
  self-msg-plugin:
    enabled: true
    priority: 1000
```

## 开发建议

- 插件应尽量无副作用，避免阻塞主线程
- 合理设置优先级，避免插件间冲突
- 可通过 `add_rpa_action`/`add_rpa_actions` 触发自动化操作
- 推荐使用类型提示和 Pydantic 进行配置校验

---

如需更复杂的插件开发示例、插件热重载、插件间通信等进阶内容，请查阅[插件仓库](https://github.com/weixin-omni/omni-bot-plugins-oss)或联系开发者社区。 