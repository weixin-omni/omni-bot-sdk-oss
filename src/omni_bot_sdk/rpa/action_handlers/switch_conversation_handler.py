from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from omni_bot_sdk.rpa.action_handlers import (
    BaseActionHandler,
    RPAActionType,
)


@dataclass
class SwitchConversationAction:
    """
    切换会话操作。
    Attributes:
        target (str): 目标用户或群聊的标识。
        is_chatroom (bool): 是否为群聊。
    """

    target: str = None
    is_chatroom: bool = False

    def __post_init__(self):
        self.action_type = RPAActionType.SWITCH_CONVERSATION
        self.is_send_message = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "timestamp": self.timestamp.isoformat(),
        }


class SwitchConversationHandler(BaseActionHandler):
    """
    切换会话操作的处理器。
    """

    def execute(self, action: SwitchConversationAction) -> bool:
        """
        执行切换会话操作。
        Args:
            action (SwitchConversationAction): 操作对象。
        Returns:
            bool: 操作是否成功。
        """
        try:
            return self.window_manager.switch_session(action.target)
        finally:
            self._cleanup()
