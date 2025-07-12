# 快速开始

> ⚠️ <strong>重要提醒：</strong>RPA 初始化需要扫描窗口并定位，请勿在此期间操作电脑。初始化过程中微信窗口将会自动缩放并移动到屏幕左上角位置。

> 注意，基于RPA方案，在运行时，请勿操作鼠标键盘，以免影响RPA运行

## 环境准备

**务必使用 Python 3.12**

### 获取数据库密钥

本项目不提供此工具，可自行通过github获取 DbkeyHookCMD.exe 或 DbkeyHookUI.exe 进行获取。
获取数据库密钥后，填入配置文件中的 dbkey。

### 启动MQTT服务

mqtt服务用于MCP消息转发，以及后续更新任务执行结果回调，windows可以使用nanomq直接启动本地服务。

## 安装

通过 pip 从 PyPI 安装：

```bash
pip install omni-bot-sdk
```

## 第一个机器人

1. 参考 config.example.yaml 生成 config.yaml
2. 启动微信并登录
3. 启动机器人脚本
4. 机器人会自动给文件传输助手发送一张图片，然后执行获取密钥

### Hello, World 示例

```python
from omni_bot_sdk.bot import Bot

def main():
    bot = Bot(config_path="config.yaml")
    bot.start()

if __name__ == "__main__":
    main()
```

现在，去和你的机器人聊天吧！ 