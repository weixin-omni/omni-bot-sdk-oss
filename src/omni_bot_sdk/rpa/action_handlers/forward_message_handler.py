import time
from dataclasses import dataclass, field

import pyautogui
from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAAction,
    RPAActionType,
)


@dataclass
class ForwardMessageAction(RPAAction):
    def __post_init__(self):
        self.action_type = RPAActionType.FORWARD_MESSAGE
        self.is_send_message = False


class ForwardMessageHandler(BaseActionHandler):
    """
    转发消息操作的处理器。
    """

    def execute(self, action: ForwardMessageAction) -> bool:
        """
        执行转发消息操作。
        Args:
            action (ForwardMessageAction): 操作对象。
        Returns:
            bool: 操作是否成功。
        """
        try:
            self.logger.warn("未实现转发消息操作")
            return False
        finally:
            self._cleanup()
