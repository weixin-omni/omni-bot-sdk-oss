# omni-bot-sdk-oss 贡献指南

感谢你对 omni-bot-sdk-oss 的关注！在提交贡献前，请阅读本指南，以便更高效地协作。

## 项目简介

omni-bot-sdk-oss 是 omni-bot 项目的开源 SDK，提供了 bot 框架、插件加载、消息分发等核心能力。该仓库主要包含：

- SDK 核心代码（`src/omni_bot_sdk/`）
- 示例（`examples/`）
- 文档（`docs/`）

## 开发环境

- Python 3.12
- Windows 10/11
- 推荐编辑器：VS Code + Python 扩展
- 依赖管理：pip（或 poetry，如有）
- 代码格式化/检查：ruff、black
- 单元测试：pytest

## 快速开始

1. 克隆仓库并进入目录

   ```bash
   git clone git@github.com:weixin-omni/omni-bot-sdk-oss.git
   cd omni-bot-sdk-oss
   ```

2. 建议使用虚拟环境

   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   ```

3. 安装依赖

   ```bash
   pip install -e .
   ```

4. 运行示例

   ```bash
   cd examples/simple-bot
   python bot.py
   ```

## 代码结构

```text
src/omni_bot_sdk/           # SDK 主体
  ├── bot.py                # Bot 主类
  ├── plugins/              # 插件相关
  ├── clients/              # 外部服务客户端
  ├── rpa/                  # RPA 相关
  ├── mcp/                  # 消息分发/协议
  ├── utils/                # 工具函数
  └── ...                   # 其他模块
examples/                   # 示例代码
docs/                       # 文档
tests/                      # 测试用例（如有）
```

## 贡献流程

1. Fork 仓库，创建新分支
2. 保持代码风格一致，建议提交前运行

   ```bash
   black .
   ```

3. 保证测试通过

   ```bash
   pytest
   ```

4. 提交 PR，建议标题格式为 `<type>: <subject>`，如 `feat: 新增插件管理功能`
5. 如需文档更新，请同步修改 `docs/` 目录

## 插件开发建议

- 插件需实现 `src/omni_bot_sdk/plugins/interface.py` 中定义的接口
- 插件注册与加载请参考 `plugin_manager.py`
- 示例插件可参考 `examples/simple-bot/`

## 版本发布（维护者）

- 版本号请同步修改 `pyproject.toml`、`src/omni_bot_sdk/__init__.py` 等相关文件
- 构建与发布请参考 `MANIFEST.in` 和相关脚本

## 其他说明

- 建议所有新代码添加类型注解和必要注释
- 如有疑问，请在 issue 区留言，或参与讨论

---

因为有你，omni-bot-sdk-oss 会变得更好，感谢你的贡献！
