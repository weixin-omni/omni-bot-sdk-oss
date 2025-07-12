"""
插件开发统一入口

- 插件开发者只需从本模块导入 Plugin 及常用协议类型
- 便于类型提示、解耦和未来SDK升级
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from omni_bot_sdk.plugins.core.plugin_interface import (
    Plugin,
    PluginExcuteContext,
    PluginExcuteResponse,
)
from omni_bot_sdk.weixin.message_classes import Message, MessageType, DownloadStatus
from omni_bot_sdk.rpa.action_handlers import RPAActionType
from omni_bot_sdk.rpa.action_handlers import (
    DownloadImageAction,
    SendImageAction,
    SendFileAction,
    DownloadVideoAction,
    DownloadFileAction,
    ForwardMessageAction,
    SendTextMessageAction,
    PatAction,
    Invite2RoomAction,
    RemoveRoomMemberAction,
    RenameRoomNameAction,
    RenameRoomRemarkAction,
    RenameNameInRoomAction,
    LeaveRoomAction,
    SendPyqAction,
    NewFriendAction,
)


# =====================
# Bot协议
# =====================
class Bot(Protocol):
    """
    OmniBot 主体协议。
    插件通过注入获得Bot实例，访问所有核心服务、组件和生命周期管理方法。
    支持状态回调机制。
    """

    config: "ConfigService"  # 配置服务
    user_service: "UserService"  # 用户服务
    user_info: "UserInfo"  # 当前用户信息
    db: "DatabaseService"  # 数据库服务
    image_processor: "ImageProcessor"  # 图像处理服务
    ocr_processor: "OCRProcessor"  # OCR服务
    window_manager: "WindowManager"  # 窗口管理服务
    rpa_controller: "RPAController"  # RPA控制器
    plugin_manager: "PluginManager"  # 插件管理器
    dat_decrypt_service: "DatDecryptService"  # dat解密服务
    processor_service: "ProcessorService"  # 处理器服务
    # 其他服务...

    STATUS_STARTING: str
    STATUS_RUNNING: str
    STATUS_PAUSED: str
    STATUS_STOPPING: str
    STATUS_STOPPED: str
    STATUS_FAILED: str

    def add_status_callback(self, callback):
        """
        注册状态变更回调。
        Args:
            callback (Callable[[str, Bot], None]): 回调函数，参数为新状态和Bot实例。
        """

    def setup(self):
        """
        初始化Bot。
        """

    def teardown(self):
        """
        销毁Bot，释放资源。
        """

    def run_forever(self):
        """
        持续运行主循环。
        """

    def pause(self):
        """
        暂停Bot运行。
        """

    def resume(self):
        """
        恢复Bot运行。
        """

    def exit(self):
        """
        退出Bot。
        """


# =====================
# Service协议
# =====================
class ConfigService(Protocol):
    """
    配置服务协议。
    提供配置项的读取能力。
    """

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项。
        """


class UserService(Protocol):
    """
    用户服务协议。
    提供用户信息的获取、设置、密钥管理等功能。
    插件可通过 bot.user_service 访问。
    """

    user_info: "UserInfo"  # 当前用户信息

    def get_user_info(self) -> "UserInfo":
        """
        获取当前用户信息。
        Returns:
            UserInfo: 当前用户信息对象。
        """

    def set_user_info(self, user_info: "UserInfo"):
        """
        设置当前用户信息。
        Args:
            user_info (UserInfo): 要设置的用户信息对象。
        """

    def update_raw_key(self, key: str, value: str):
        """
        更新原始密钥。
        Args:
            key (str): 密钥名称。
            value (str): 密钥值。
        """

    def get_raw_key(self, key: str) -> Optional[str]:
        """
        获取原始密钥。
        Args:
            key (str): 密钥名称。
        Returns:
            Optional[str]: 密钥值，如不存在则为None。
        """

    def dump_to_file(self):
        """
        将用户信息持久化到文件。
        """


class UserInfo(Protocol):
    """
    微信用户信息协议。
    统一描述微信用户的所有关键信息。
    """

    pid: str  # 进程ID，唯一标识本地运行实例
    version: str  # 微信版本号
    alias: str  # 微信别名
    account: str  # 微信号
    nickname: str  # 微信昵称
    phone: str  # 绑定手机号
    data_dir: str  # 数据目录路径
    dbkey: str  # 数据库密钥
    raw_keys: Dict[str, str]  # 其他原始密钥信息


class DatabaseService(Protocol):
    """
    数据库服务协议。
    提供用户信息、联系人、消息等数据库相关操作。
    """

    user_info: "UserInfo"  # 当前用户信息

    def setup(self):
        """
        数据库初始化。
        """

    def get_db_path_by_username(self, username: str) -> Optional[str]:
        """
        根据用户名获取数据库路径。

        Args:
            username (str): 用户名。
        Returns:
            Optional[str]: 数据库路径，如不存在则为None。
        """

    def execute_query(self, db_path: str, query: str, params: tuple = ()) -> list:
        """
        执行SQL查询。

        Args:
            db_path (str): 数据库路径。
            query (str): SQL查询语句。
            params (tuple, optional): 查询参数，默认为空元组。
        Returns:
            list: 查询结果。
        """

    def get_contact_by_username(self, username: str):
        """
        根据用户名获取联系人。

        Args:
            username (str): 用户名。
        Returns:
            Contact: 联系人对象。
        """

    def get_contact_by_display_name(self, display_name: str):
        """
        根据显示名获取联系人。

        Args:
            display_name (str): 显示名。
        Returns:
            Contact: 联系人对象。
        """

    def get_room_member_list(self, room_user_name: str) -> list:
        """
        获取群成员列表。

        Args:
            room_user_name (str): 群聊用户名。
        Returns:
            list: 群成员列表。
        """

    def get_room_member_count_by_name(self, room_name: str) -> int:
        """
        获取群成员数量。

        Args:
            room_name (str): 群聊名称。
        Returns:
            int: 群成员数量。
        """

    def check_member_in_room(self, room_id, member_id) -> bool:
        """
        检查成员是否在群中。

        Args:
            room_id: 群ID。
            member_id: 成员ID。
        Returns:
            bool: 是否在群中。
        """

    def get_messages_by_username(
        self, message_db_path: str, username: str, count: int = 10, order: str = "desc"
    ) -> list:
        """
        获取指定用户的消息。

        Args:
            message_db_path (str): 消息数据库路径。
            username (str): 用户名。
            count (int, optional): 获取消息数量，默认为10。
            order (str, optional): 排序方式，默认为"desc"。
        Returns:
            list: 消息列表。
        """

    def close_all_connections(self):
        """
        关闭所有数据库连接。
        """


class ImageProcessor(Protocol):
    """
    图像处理服务协议。
    提供图像检测、截图、绘图等功能。
    """

    def setup(self):
        """
        初始化图像处理服务。
        """

    def detect_objects(self, image: Any) -> list:
        """
        检测图像中的对象。

        Args:
            image (Any): 输入的图像对象。
        Returns:
            list: 检测到的对象列表。
        """

    def take_screenshot(self, region: tuple, save_path: Optional[str] = None) -> Any:
        """
        截取屏幕区域。

        Args:
            region (tuple): 截图区域 (x, y, w, h)。
            save_path (Optional[str]): 保存路径，默认为None。
        Returns:
            Any: 截图对象。
        """

    def draw_boxes_on_screen(
        self,
        screenshot: Any,
        parsed_content: list,
        output_path: str = None,
        start: tuple = None,
    ) -> Any:
        """
        在截图上绘制检测框。

        Args:
            screenshot (Any): 截图对象。
            parsed_content (list): 检测内容。
            output_path (str, optional): 输出路径。
            start (tuple, optional): 起始坐标。
        Returns:
            Any: 绘制后的图片对象。
        """


class OCRProcessor(Protocol):
    """
    OCR服务协议。
    提供图像OCR识别功能。
    """

    def setup(self):
        """
        初始化OCR服务。
        """

    def process_image(self, image_path: str = None, image: Any = None) -> list:
        """
        对图片进行OCR识别。

        Args:
            image_path (str, optional): 图片路径。
            image (Any, optional): 图片对象。
        Returns:
            list: 识别结果。
        """

    def find_text(
        self, image: Any, target_text: str, similarity_threshold: float = 0.8
    ) -> list:
        """
        在图片中查找指定文本。

        Args:
            image (Any): 图片对象。
            target_text (str): 目标文本。
            similarity_threshold (float, optional): 相似度阈值，默认为0.8。
        Returns:
            list: 匹配结果。
        """


class WindowManager(Protocol):
    """
    窗口管理服务协议。
    提供窗口激活、切换、获取等功能。
    """

    def activate_input_box(self, offset_x: int = 0) -> bool:
        """
        激活输入框。

        Args:
            offset_x (int, optional): X轴偏移，默认为0。
        Returns:
            bool: 是否激活成功。
        """

    def get_icon_position(self, icon_name: str) -> Optional[Dict]:
        """
        获取图标位置。

        Args:
            icon_name (str): 图标名称。
        Returns:
            Optional[Dict]: 图标位置信息。
        """

    def init_chat_window(self) -> bool:
        """
        初始化聊天窗口。

        Returns:
            bool: 是否初始化成功。
        """

    def switch_session(self, target: str) -> bool:
        """
        切换会话。

        Args:
            target (str): 目标会话。
        Returns:
            bool: 是否切换成功。
        """

    def switch_window(self, target: str) -> bool:
        """
        切换窗口。

        Args:
            target (str): 目标窗口。
        Returns:
            bool: 是否切换成功。
        """

    def switch_menu(self, target: str) -> bool:
        """
        切换菜单。

        Args:
            target (str): 目标菜单。
        Returns:
            bool: 是否切换成功。
        """

    def get_window(self, windowType: Any, all: bool = False) -> Any:
        """
        获取窗口对象。

        Args:
            windowType (Any): 窗口类型。
            all (bool, optional): 是否获取全部，默认为False。
        Returns:
            Any: 窗口对象。
        """

    def open_friend_window(self) -> Any:
        """
        打开好友窗口。

        Returns:
            Any: 窗口对象。
        """

    def open_friend_send_window(self) -> Any:
        """
        打开好友发送窗口。

        Returns:
            Any: 窗口对象。
        """

    def close_all_windows(self):
        """
        关闭所有窗口。
        """

    def open_close_sidebar(self, close: bool = False) -> bool:
        """
        打开或关闭侧边栏。

        Args:
            close (bool, optional): 是否关闭，默认为False。
        Returns:
            bool: 操作是否成功。
        """

    def wait_for_window(
        self, window_type: Any, all: bool = False, timeout: int = 5
    ) -> Any:
        """
        等待窗口出现。

        Args:
            window_type (Any): 窗口类型。
            all (bool, optional): 是否获取全部，默认为False。
            timeout (int, optional): 超时时间，默认为5秒。
        Returns:
            Any: 窗口对象。
        """


class RPAController(Protocol):
    """
    RPA控制器协议。
    负责执行RPA动作，管理RPA任务队列。
    """

    db: DatabaseService  # 数据库服务
    window_manager: WindowManager  # 窗口管理服务
    ocr_processor: OCRProcessor  # OCR服务
    image_processor: ImageProcessor  # 图像处理服务

    def execute_action(self, action: "RPAAction") -> bool:
        """
        执行RPA动作。

        Args:
            action (RPAAction): RPA动作对象。
        Returns:
            bool: 是否执行成功。
        """


class PluginManager(Protocol):
    """
    插件管理器协议。
    负责插件的自动发现、加载、优先级排序、消息处理链路分发与热重载。
    插件开发者无需直接操作，通常通过 bot.plugin_manager 访问。
    """

    bot: "Bot"  # 主Bot对象
    plugins: list  # 已加载插件列表

    def setup(self):
        """
        初始化插件管理器。
        """

    def load_plugins(self):
        """
        加载所有插件。
        """

    async def process_message(self, message: "Message", context: dict) -> list:
        """
        异步处理消息，依次调用每个插件的 handle_message 方法。
        支持 should_stop 机制（插件可中断后续处理），并收集所有插件响应。

        Args:
            message (Message): 待处理的消息对象。
            context (dict): 附加上下文信息。
        Returns:
            list: 所有插件的 PluginExcuteResponse 响应列表。
        """

    def reload_all_plugins(self):
        """
        重新加载所有插件（热重载）。
        清空当前插件实例列表，重新发现并加载所有插件。
        """


class MessageService(Protocol):
    """
    消息服务协议。
    提供消息的启动、停止、回调设置等功能。
    """

    def start(self):
        """
        启动消息服务。
        """

    def stop(self):
        """
        停止消息服务。
        """

    def set_callback(self, callback: Any):
        """
        设置消息回调。

        Args:
            callback (Any): 回调函数。
        """

    def pause(self):
        """
        暂停消息服务。
        """

    def resume(self):
        """
        恢复消息服务。
        """

    def get_status(self) -> dict:
        """
        获取服务状态。

        Returns:
            dict: 服务状态信息。
        """


class RPAService(Protocol):
    """
    RPA服务协议。
    提供RPA服务的启动、停止、状态获取等功能。
    """

    def start(self):
        """
        启动RPA服务。
        """

    def stop(self):
        """
        停止RPA服务。
        """

    def get_status(self) -> dict:
        """
        获取RPA服务状态。

        Returns:
            dict: 服务状态信息。
        """


class MQTTService(Protocol):
    """
    MQTT服务协议。
    提供MQTT消息的初始化、启动等功能。
    """

    def setup(self):
        """
        初始化MQTT服务。
        """

    def start(self):
        """
        启动MQTT服务。
        """


class DatDecryptService(Protocol):
    """
    dat解密服务协议。
    提供dat图片异步解密、回调注册、最近解密图片队列等能力。
    """

    def register_decrypt_callback(self, filename: str, callback: callable):
        """
        注册图片解密回调。用户可传入回调方法和图片文件名，
        如果该文件名已解密则立即触发，否则等待解密后触发。

        Args:
            filename (str): 图片文件名（不含路径）。
            callback (Callable[[str], None]): 回调函数，参数为解密后图片路径。
        """
        ...

    @property
    def recent_decrypts(self) -> list:
        """
        最近解密成功的图片队列，最多保留20条，元素为(filename, path)。

        Returns:
            list: [(str, str)] 最近解密的图片文件名和路径。
        """
        ...


class NewFriendCheckService(Protocol):
    """
    新好友检测服务协议。
    提供新好友检测功能。
    """

    pass


class ProcessorService(Protocol):
    """
    处理器服务协议。
    负责处理消息、RPA任务、插件管理等核心业务逻辑。
    """

    user_info: "UserInfo"  # 当前用户信息
    db: "DatabaseService"  # 数据库服务
    message_factory_service: Any  # 消息工厂服务
    message_queue: Any  # 消息队列
    rpa_task_queue: Any  # RPA任务队列
    is_running: bool  # 是否正在运行
    plugin_manager: Any  # 插件管理器

    def setup(self):
        """
        初始化处理器服务。
        """

    def start(self):
        """
        启动处理器服务。
        """

    def stop(self):
        """
        停止处理器服务。
        """

    def get_status(self) -> dict:
        """
        获取处理器服务状态。

        Returns:
            dict: 服务状态信息。
        """

    def add_rpa_actions(self, actions: list):
        """
        线程安全地批量添加RPA动作到队列。

        Args:
            actions (list): RPA动作对象列表。
        """


# =====================
# RPAAction协议（所有Action类型）
# =====================
class RPAAction(Protocol):
    """
    RPA动作协议，所有RPA相关动作的基类。
    定义RPA动作的基本属性和方法。
    """

    action_type: RPAActionType  # 动作类型
    timestamp: datetime  # 时间戳

    def to_dict(self) -> Dict[str, Any]:
        """
        转为字典。

        Returns:
            Dict[str, Any]: 字典形式的动作信息。
        """


__all__ = [
    # 插件基类
    "Plugin",
    # 常量类
    "MessageType",
    "DownloadStatus",
    "RPAActionType",
    # 主要服务协议
    "Bot",
    "ConfigService",
    "UserService",
    "UserInfo",
    "DatabaseService",
    "ImageProcessor",
    "OCRProcessor",
    "WindowManager",
    "RPAController",
    "PluginManager",
    "MessageService",
    "RPAService",
    "MQTTService",
    "DatDecryptService",
    "NewFriendCheckService",
    "ProcessorService",
    # 插件上下文与响应
    "PluginExcuteContext",
    "PluginExcuteResponse",
    # RPA动作实现类
    "SendTextMessageAction",
    "SendImageAction",
    "SendFileAction",
    "DownloadImageAction",
    "DownloadVideoAction",
    "DownloadFileAction",
    "ForwardMessageAction",
    "PatAction",
    "Invite2RoomAction",
    "RemoveRoomMemberAction",
    "RenameRoomNameAction",
    "RenameRoomRemarkAction",
    "RenameNameInRoomAction",
    "LeaveRoomAction",
    "SendPyqAction",
    "NewFriendAction",
]
