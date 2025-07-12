import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAAction,
    RPAActionType,
)
from omni_bot_sdk.utils.helpers import set_clipboard_text


@dataclass
class SendTextMessageAction(RPAAction):
    """
    发送消息操作。

    Attributes:
        content (str): 要发送的消息内容。
        target (str): 目标用户或群聊的标识。
        is_chatroom (bool): 是否为群聊。
        at_user_name (str): 需要@的用户名（仅群聊有效）。
        quote_message (str): 需要引用的消息内容。
        random_at_quote (bool): 是否随机@或引用。
    """

    content: str = field(default=None)
    target: str = field(default=None)
    is_chatroom: bool = field(default=False)
    at_user_name: str = field(default=None)
    quote_message: str = field(default=None)
    random_at_quote: bool = field(default=False)

    def __post_init__(self):
        self.action_type = RPAActionType.SEND_TEXT_MESSAGE
        self.is_send_message = True


class SendTextMessageHandler(BaseActionHandler):
    """
    发送消息操作的处理器。
    """

    def execute(self, action: SendTextMessageAction) -> bool:
        """
        执行发送消息操作。
        Args:
            action (SendTextMessageAction): 操作对象。
        Returns:
            bool: 操作是否成功。
        """
        try:
            if not self.window_manager.switch_session(action.target):
                return False
            if action.at_user_name:
                self.controller.message_sender.clear_input_box()
                self.controller.message_sender.mention_user(action.at_user_name)
                time.sleep(self.controller.window_manager.action_delay)
            return self.controller.message_sender.send_message(
                action.content, action.at_user_name is None
            )
        finally:
            self._cleanup()
