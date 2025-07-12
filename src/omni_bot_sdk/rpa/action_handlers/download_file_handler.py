from dataclasses import dataclass, field
from typing import Optional

from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAAction,
    RPAActionType,
)


@dataclass
class DownloadFileAction(RPAAction):
    file_url: Optional[str] = None
    save_path: Optional[str] = None

    def __post_init__(self):
        self.action_type = RPAActionType.DOWNLOAD_FILE
        self.is_send_message = False


class DownloadFileHandler(BaseActionHandler):
    """
    下载文件操作的处理器。
    """

    def execute(self, action: DownloadFileAction) -> bool:
        """
        执行下载文件操作。
        Args:
            action (DownloadFileAction): 操作对象。
        Returns:
            bool: 操作是否成功。
        """
        try:
            self.logger.info(f"下载文件: {action.to_dict()}")
            # TODO: 实现具体的下载文件逻辑，这里能拿到文件的地址应该，可以转发出去，下载功能先不做了
            return True
        finally:
            self._cleanup()
