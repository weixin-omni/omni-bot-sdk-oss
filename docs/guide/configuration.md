# 配置指南

本章节详细说明所有可用的配置项及其作用，无需再查阅配置文件。

---

## 顶层配置

### dbkey
- **说明**：数据库加密密钥，必须设置。
- **类型**：字符串

### aes_xor_key
- **说明**：AES加密用的密钥和XOR，格式为字符串，设置为空时自动查找。
- **示例**：`1234567890,17`

---

## MCP 服务配置（mcp）
- **host**：监听主机地址，通常为`0.0.0.0`表示所有网卡。
- **port**：监听端口，默认`8000`。

---

## 钉钉机器人（dingtalk）
- **webhook_url**：钉钉机器人Webhook地址，当微信异常时，将推送异常消息和登录二维码。

---

## 日志配置（logging）
- **backup_count**：日志文件最多保留数量。
- **level**：日志级别，可选：`DEBUG`/`INFO`/`WARNING`/`ERROR`。
- **max_size**：单个日志文件最大字节数，默认`10485760`（10MB）。
- **path**：日志文件存放路径。

---

## MQTT 配置（mqtt）
- **client_id**：MQTT客户端ID前缀。
- **host**：MQTT服务器地址。
- **password**：MQTT密码。
- **port**：MQTT端口，默认`1883`。
- **username**：MQTT用户名。

---

## 插件配置（plugins）
- **block-empty-room-plugin**：空群屏蔽插件，`enabled`（是否启用），`priority`（优先级）。
- **chat-context-plugin**：聊天上下文插件，`enabled`，`priority`。
- **openai-bot-plugin**：OpenAI对话插件，`enabled`，`priority`，`openai_api_key`，`openai_base_url`，`openai_model`（模型名），`prompt`（对话提示词模板）。
- **self-msg-plugin**：自发消息插件，`enabled`，`priority`。

---

## RPA 相关参数（rpa）
- **action_delay**：操作延迟（秒）。
- **scroll_delay**：滚动延迟（秒）。
- **max_retries**：最大重试次数。
- **switch_contact_delay**：切换联系人延迟（秒）。
- **ocr**：OCR相关配置：
  - `merge_threshold`：OCR合并阈值。
  - `min_confidence`：最小置信度。
  - `remote_url`：远程OCR服务地址。
  - `use_remote`：是否使用远程OCR。
- **room_action_offset**：房间操作偏移量，数组。
- **search_contact_offset**：搜索联系人偏移量，数组。
- **side_bar_delay**：侧边栏延迟（秒）。
- **timeout**：超时时间（秒）。
- **window_margin**：窗口边距。
- **window_show_delay**：窗口显示延迟（秒）。
- **short_term_rate**：短期速率。
- **short_term_capacity**：短期容量。
- **long_term_rate**：长期速率。
- **long_term_capacity**：长期容量。

---

## 微信GF解析（wxgf）
- **api_url**：微信GF解析API地址。

---

## S3 存储配置（s3）
- **endpoint_url**：S3服务端点。
- **access_key**：S3访问密钥。
- **secret_key**：S3密钥。
- **region**：S3区域。
- **bucket**：桶名称。
- **public_url_prefix**：公开访问前缀。

---

如需详细配置示例，请参考 `config.example.yaml` 文件。 