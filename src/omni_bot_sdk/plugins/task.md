omni-bot-sdk 插件协议同步维护说明
任务目标
实现插件开发的解耦与类型安全：通过 omni_bot_sdk/plugins/interface.py 统一导出所有插件开发所需的基类、协议（Protocol）、服务类型和常用类型，插件开发者只需从该文件导入即可获得完整类型提示和文档说明。
自动化、结构化注释：所有协议类、属性、方法均补充了 Google 风格的 docstring，详细说明参数（Args）、返回值（Returns）及字段含义，极大提升开发体验和可维护性。
主要内容
1. 协议分类与导出
插件基类：Plugin
Bot协议：Bot（主Bot对象，聚合所有服务和生命周期方法）
Service协议：如 UserService、DatabaseService、ImageProcessor、OCRProcessor、WindowManager、RPAController、PluginManager、MessageService、RPAService、MQTTService、ProcessorService 等
RPAAction协议：所有RPA相关Action类型及 RPAActionType、RPAAction
消息类型协议：MessageType
插件上下文协议：PluginExcuteContext
用户信息协议：UserInfo，已补全所有字段和注释
2. 注释与类型提示规范
每个协议类均有简明 docstring，说明用途和典型用法
每个属性/方法均有中文注释
每个方法均有 Google 风格的 Args/Returns 说明，参数类型、含义、返回值一目了然
所有类型提示均与实际实现严格对应
后续维护与同步流程
> 当你修改了某个服务、协议或数据类（如 UserService、UserInfo、DatabaseService 等）时，请按照以下流程同步更新 interface.py，以保证类型提示和注释始终与实现一致。
步骤
定位变更点
明确你修改了哪个服务/类/协议（如新增字段、方法、参数、类型变更等）
同步到 interface.py
在 omni_bot_sdk/plugins/interface.py 中找到对应的 Protocol 协议
补充/修改属性、方法签名，确保与实现完全一致
补充/修改 docstring，详细说明新增/变更的参数、返回值、用途
保持注释风格与 Google 风格一致
检查 _all_ 导出
如有新增协议类型，记得补充到 __all__ 列表
插件开发者同步
通知插件开发者只需从 interface.py 导入协议类型，无需关心 SDK 内部结构
可选：自动化校验
推荐后续可开发脚本自动比对实现与 interface.py 的一致性，减少人工遗漏
示例（同步 UserInfo 字段）
假设你在 models.py 中为 UserInfo 新增了 email: str 字段：
在 interface.py 的 UserInfo(Protocol) 中同步新增
Apply to interface.py
在 docstring 中补充说明
Apply to interface.py
维护建议
每次服务/协议/数据类有变更，务必同步更新 interface.py
保持注释和类型提示的准确性、完整性
如有大规模重构，建议全量比对实现与协议定义

