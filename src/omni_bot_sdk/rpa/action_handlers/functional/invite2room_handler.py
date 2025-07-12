from dataclasses import dataclass, field

from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAAction,
    RPAActionType,
)


@dataclass
class Invite2RoomAction(RPAAction):
    """
    邀请加群操作。

    Attributes:
        user_name (str): 被邀请的用户名。
        target (str): 目标群聊的名称。
    """

    user_name: str = field(default=None)
    target: str = field(default=None)

    def __post_init__(self):
        self.action_type = RPAActionType.INVITE_2_ROOM
        self.is_send_message = True


class Invite2RoomHandler(BaseActionHandler):
    """邀请好友进群操作的处理器。"""

    def execute(self, action: Invite2RoomAction) -> bool:
        self.logger.warn("Invite2RoomHandler is not implemented")
        return False
