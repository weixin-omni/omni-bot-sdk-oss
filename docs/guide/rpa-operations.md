# RPA操作

> ⚠️ 注意：所有 RPA 操作中的 <code>target</code> 参数，均为需要操作的对象“名称”（如好友昵称、群聊名称），而非 ID。由于 RPA 方案无法直接获取微信 ID，请确保名称唯一且准确。
> 
> ⚠️ 文件、图片等路径参数必须为本地磁盘的绝对路径，不能为网络URL。请在插件逻辑中提前完成下载等耗时操作，Action 只负责本地自动化。
>
> <strong>* 带星号的功能为闭源版本功能，用户需自行开发，开源版本不包含相关代码。</strong>

Omni Bot SDK 内置了丰富的 RPA 操作类型，开发者可以在插件中灵活调用，实现自动化消息、文件、群管理等多种操作。

## 可用的 RPA Action Handler 一览

<table>
  <thead>
    <tr>
      <th style="min-width:120px;">操作类型</th>
      <th style="min-width:180px;">Action 类名</th>
      <th style="min-width:260px;">主要参数说明</th>
      <th style="min-width:120px;">典型用途</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>发送文本消息</td>
      <td><code>SendTextMessageAction</code></td>
      <td><code>content</code>（消息内容）, <code>target</code>（对象名称）, <code>is_chatroom</code>（是否群聊）, <code>at_user_name</code>（@用户名，仅群聊）, <code>quote_message</code>（引用消息内容）, <code>random_at_quote</code>（是否随机@/引用）</td>
      <td>发送文字到好友/群</td>
    </tr>
    <tr>
      <td>发送图片</td>
      <td><code>SendImageAction</code></td>
      <td><code>image_path</code>（图片路径）, <code>target</code>, <code>is_chatroom</code></td>
      <td>发送图片到好友/群</td>
    </tr>
    <tr>
      <td>发送文件</td>
      <td><code>SendFileAction</code></td>
      <td><code>file_path</code>（文件路径）, <code>target</code>, <code>is_chatroom</code></td>
      <td>发送文件到好友/群</td>
    </tr>
    <tr>
      <td>转发消息</td>
      <td><code>ForwardMessageAction</code></td>
      <td>（暂无参数，后续可扩展）</td>
      <td>转发一条消息</td>
    </tr>
    <tr>
      <td>下载图片</td>
      <td><code>DownloadImageAction</code></td>
      <td><code>target</code>（对象名称）, <code>max_count</code>（下载数量，默认1）</td>
      <td>下载图片</td>
    </tr>
    <tr>
      <td>下载视频</td>
      <td><code>DownloadVideoAction</code></td>
      <td><code>target</code>, <code>name</code>（视频名称，可选）, <code>max_count</code>（下载数量，默认1）, <code>is_chatroom</code></td>
      <td>下载视频</td>
    </tr>
    <tr>
      <td>下载文件</td>
      <td><code>DownloadFileAction</code></td>
      <td><code>file_url</code>（文件URL）, <code>save_path</code>（保存路径）</td>
      <td>下载文件</td>
    </tr>
    <tr>
      <td>拍一拍</td>
      <td><code>PatAction</code></td>
      <td><code>target</code>（对象名称）, <code>user_name</code>（被拍用户昵称，群聊时用）, <code>is_chatroom</code></td>
      <td>拍一拍好友/群成员</td>
    </tr>
    <tr>
      <td>邀请进群*</td>
      <td><code>Invite2RoomAction</code></td>
      <td><code>user_name</code>（被邀请人昵称）, <code>target</code>（群聊名称）</td>
      <td>邀请用户进群</td>
    </tr>
    <tr>
      <td>新好友操作*</td>
      <td><code>NewFriendAction</code></td>
      <td><code>user_name</code>（新好友昵称）, <code>action</code>（同意/拒绝/忽略）, <code>response</code>（拒绝时回复内容）, <code>index</code>（可选）</td>
      <td>同意/拒绝/忽略新好友</td>
    </tr>
    <tr>
      <td>发送朋友圈*</td>
      <td><code>SendPyqAction</code></td>
      <td><code>images</code>（图片列表）, <code>content</code>（文案）</td>
      <td>发表朋友圈</td>
    </tr>
    <tr>
      <td>群公告</td>
      <td><code>PublicRoomAnnouncementAction</code></td>
      <td><code>content</code>（公告内容）, <code>target</code>（群聊名称）, <code>force_edit</code>（是否强制编辑）</td>
      <td>发布群公告</td>
    </tr>
    <tr>
      <td>群成员移除</td>
      <td><code>RemoveRoomMemberAction</code></td>
      <td><code>user_name</code>（被移除成员昵称）, <code>target</code>（群聊名称）</td>
      <td>移除群成员</td>
    </tr>
    <tr>
      <td>群名修改</td>
      <td><code>RenameRoomNameAction</code></td>
      <td><code>target</code>（群聊名称）, <code>name</code>（新群名）</td>
      <td>修改群名</td>
    </tr>
    <tr>
      <td>群备注修改</td>
      <td><code>RenameRoomRemarkAction</code></td>
      <td><code>target</code>（群聊名称）, <code>remark</code>（新备注）</td>
      <td>修改群备注</td>
    </tr>
    <tr>
      <td>群昵称修改</td>
      <td><code>RenameNameInRoomAction</code></td>
      <td><code>target</code>（群聊名称）, <code>name</code>（新昵称）</td>
      <td>修改自己在群的昵称</td>
    </tr>
    <tr>
      <td>退出群聊</td>
      <td><code>LeaveRoomAction</code></td>
      <td><code>target</code>（群聊名称）</td>
      <td>退出群聊</td>
    </tr>
    <tr>
      <td>切换会话</td>
      <td><code>SwitchConversationAction</code></td>
      <td><code>target</code>（对象名称）</td>
      <td>切换到指定会话</td>
    </tr>
  </tbody>
</table>

> 具体参数和更多操作请参考源码 <code>omni_bot_sdk/rpa/action_handlers/</code> 目录。

---

## 在插件中返回RPA操作的示例

插件开发者可以在 `handle_message` 方法中，构造对应的 Action 并通过 `add_rpa_action` 或 `add_rpa_actions` 返回。例如：

### 发送文本消息

```python
from omni_bot_sdk.plugins.interface import Plugin, PluginExcuteContext
from omni_bot_sdk.rpa.action_handlers import SendTextMessageAction

class DemoPlugin(Plugin):
    # ... 省略其它方法 ...
    async def handle_message(self, context: PluginExcuteContext):
        # 假设收到特定消息时自动回复
        message = context.get_message()
        if message.text == "你好":
            action = SendTextMessageAction(
                content="你好，我是机器人！",
                target=message.from_user,  # 目标用户
                is_chatroom=message.is_group  # 是否群聊
            )
            self.add_rpa_action(action)
```

### 发送图片

```python
from omni_bot_sdk.rpa.action_handlers import SendImageAction

# ... 在 handle_message 内部 ...
action = SendImageAction(
    image_path="/path/to/image.jpg",
    target=message.from_user,
    is_chatroom=message.is_group
)
self.add_rpa_action(action)
```

### 邀请用户进群

```python
from omni_bot_sdk.rpa.action_handlers import Invite2RoomAction

# ... 在 handle_message 内部 ...
action = Invite2RoomAction(
    user_name="wxid_xxx",
    target="群聊名称"
)
self.add_rpa_action(action)
```

### 发送朋友圈

```python
from omni_bot_sdk.rpa.action_handlers import SendPyqAction

# ... 在 handle_message 内部 ...
action = SendPyqAction(
    images=["/path/to/img1.jpg", "/path/to/img2.jpg"],
    content="自动发朋友圈测试"
)
self.add_rpa_action(action)
```

---

## 开发建议

- 每个 Action 类的参数请参考源码注释，确保传递正确。
- 支持批量操作：`self.add_rpa_actions([action1, action2, ...])`
- 插件可组合多种 Action，实现复杂自动化流程。

如需更多 Action Handler 的用法和参数说明，请查阅源码或联系开发者社区。 