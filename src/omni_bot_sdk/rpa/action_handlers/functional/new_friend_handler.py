from dataclasses import dataclass
from typing import Optional

from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAActionType,
    RPAAction,
)
from omni_bot_sdk.rpa.action_handlers.mixins.window_operations_mixin import (
    WindowOperationsMixin,
)


@dataclass
class NewFriendAction(RPAAction):
    """
    新好友操作。
    TODO 必须重新实现，目前方案不稳定
    Attributes:
        user_name (str): 新好友用户名。
        action (str): 操作类型（同意、拒绝、忽略）。
        response (str): 拒绝时的回复内容。
    """

    user_name: Optional[str] = None
    action: Optional[str] = None
    response: Optional[str] = None
    index: Optional[int] = None

    def __post_init__(self):
        self.action_type = RPAActionType.NEW_FRIEND
        self.is_send_message = True


class NewFriendHandler(WindowOperationsMixin, BaseActionHandler):
    """
    新好友操作的处理器。
    """

    def execute(self, action: NewFriendAction) -> bool:
        self.logger.warn("NewFriendHandler is not implemented")
        return False
