from dataclasses import dataclass, field
from typing import List

from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAAction,
    RPAActionType,
)


@dataclass
class SendPyqAction(RPAAction):
    """
    朋友圈发送操作的数据结构。
    """

    images: List[str] = field(default_factory=list)
    content: str = ""

    def __post_init__(self):
        self.action_type = RPAActionType.SEND_PYQ
        self.is_send_message = True


class SendPyqHandler(BaseActionHandler):
    def execute(self, action: SendPyqAction) -> bool:
        self.logger.warn("SendPyqHandler is not implemented")
        return False
