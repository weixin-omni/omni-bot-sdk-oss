import logging
import queue
import signal
import time
from typing import Any, List, Tuple
import threading

from omni_bot_sdk.common.queues import message_queue, rpa_task_queue

# 导入所有将被实例化的核心组件类
from omni_bot_sdk.common.config import Config
from omni_bot_sdk.mcp.app import create_app
from omni_bot_sdk.models import UserInfo
from omni_bot_sdk.plugins.plugin_manager import PluginManager
from omni_bot_sdk.rpa.action_handlers import SendImageAction
from omni_bot_sdk.rpa.controller import RPAController
from omni_bot_sdk.rpa.image_processor import ImageProcessor
from omni_bot_sdk.rpa.ocr_processor import OCRProcessor
from omni_bot_sdk.rpa.window_manager import WindowManager
from omni_bot_sdk.services.core.database_service import DatabaseService
from omni_bot_sdk.services.core.message_factory_service import MessageFactoryService
from omni_bot_sdk.services.core.message_service import MessageService
from omni_bot_sdk.services.core.mqtt_service import MQTTService
from omni_bot_sdk.services.core.processor_service import ProcessorService
from omni_bot_sdk.services.core.rpa_service import RPAService
from omni_bot_sdk.services.core.user_service import UserService
from omni_bot_sdk.services.functional.dat_decrypt_service import DatDecryptService
from omni_bot_sdk.services import NewFriendCheckService
from omni_bot_sdk.services.functional.weixin_status_service import WeixinStatusService
from omni_bot_sdk.utils.logging_setup import setup_logging
from omni_bot_sdk.utils.helpers import ensure_dir_exists


class Bot:
    """
    Omni-Bot的核心平台运行时环境。
    负责生命周期管理、组件初始化、插件上下文注入等。
    不直接处理业务逻辑，而是为插件和服务提供统一的运行支撑。
    """

    STATUS_STARTING = "starting"  # 启动中
    STATUS_RUNNING = "running"  # 运行中
    STATUS_PAUSED = "paused"  # 已暂停
    STATUS_STOPPING = "stopping"  # 停止中
    STATUS_STOPPED = "stopped"  # 已停止
    STATUS_FAILED = "failed"  # 启动/运行失败

    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化Bot对象，仅完成依赖注入和对象组装，不执行耗时操作。
        """
        ensure_dir_exists("runtime_images")
        self.config: Config = Config(config_path)
        setup_logging(
            log_dir=self.config.get("logging.path", "logs"),
            log_level=self.config.get("logging.level", logging.INFO),
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.warn(
            "图片AES key需要在微信启动后一小段时间内才能获取，如果无法获取请重新启动微信后重试"
        )

        self.is_running = False
        self.is_paused = False  # 标记是否处于暂停状态
        self._status = None  # 当前状态
        self._status_callbacks = []  # 状态变更回调列表

        # 用户服务与用户信息初始化
        self.user_service: UserService = UserService(self.config.get("dbkey"))
        self.user_info: UserInfo = self.user_service.get_user_info()
        # 数据库服务初始化（需最先初始化）
        self.db: DatabaseService = DatabaseService(self.user_service)
        # RPA相关组件初始化
        self.image_processor: ImageProcessor = self._create_image_processor()
        self.ocr_processor: OCRProcessor = self._create_ocr_processor()
        self.window_manager: WindowManager = self._create_window_manager()
        self.rpa_controller: RPAController = self._create_rpa_controller()
        # 核心队列
        self.message_queue: queue.Queue = message_queue
        self.rpa_task_queue: queue.Queue = rpa_task_queue
        # 插件管理器
        self.plugin_manager: PluginManager = PluginManager(self)
        # 所有服务初始化
        all_services = self._create_services()
        # 统一收集所有需生命周期管理的组件
        self._components: List[Any] = [
            self.user_service,
            self.db,
            self.image_processor,
            self.ocr_processor,
            self.plugin_manager,
            *all_services,
        ]

    def _create_image_processor(self) -> ImageProcessor:
        """
        创建ImageProcessor实例。
        """
        return ImageProcessor()

    def _create_ocr_processor(self) -> OCRProcessor:
        """
        创建OCRProcessor实例，并注入OCR相关配置。
        """
        ocr_config = self.config.get("rpa.ocr", {})
        self.logger.info(f"OCRProcessor configured with: {ocr_config}")
        return OCRProcessor(ocr_config=ocr_config)

    def _create_window_manager(self) -> WindowManager:
        """
        创建WindowManager实例，并注入依赖和RPA配置。
        """
        rpa_config = self.config.get("rpa", {})
        return WindowManager(
            image_processor=self.image_processor,
            ocr_processor=self.ocr_processor,
            rpa_config=rpa_config,
        )

    def _create_rpa_controller(self) -> RPAController:
        """
        创建RPAController实例，并注入所有依赖。
        """
        return RPAController(
            db=self.db,
            window_manager=self.window_manager,
            ocr_processor=self.ocr_processor,
            image_processor=self.image_processor,
            rpa_config=self.config.get("rpa", {}),
        )

    def _create_services(self) -> Tuple[ProcessorService, List[Any]]:
        """
        创建所有服务实例，并返回服务列表。
        """
        self.logger.info("Initializing all services...")

        weixin_status_service = WeixinStatusService(
            self.config, self.window_manager, self.image_processor, self.ocr_processor
        )
        message_service = MessageService(self.message_queue, self.db)
        message_factory_service = MessageFactoryService(self.user_info, self.db)
        processor_service = ProcessorService(
            user_info=self.user_info,
            message_queue=self.message_queue,
            rpa_task_queue=self.rpa_task_queue,
            db=self.db,
            message_factory_service=message_factory_service,
            plugin_manager=self.plugin_manager,
        )
        rpa_service = RPAService(self.rpa_task_queue, self.rpa_controller)
        mqtt_service = None
        if self.config.get("mqtt", {}).get("host", None) and self.config.get(
            "mqtt", {}
        ).get("port", None):
            mqtt_service = MQTTService(
                user_info=self.user_info,
                db=self.db,
                rpa_task_queue=self.rpa_task_queue,
                mqtt_config=self.config.get("mqtt", {}),
            )
        else:
            self.logger.warn(
                "MQTT服务未配置，将无法接收MCP消息，请在config.yaml中配置mqtt服务"
            )
        dat_decrypt_service = DatDecryptService(self.user_info, self.config)
        new_friend_check_service = NewFriendCheckService(self.rpa_task_queue, self.db)

        services_list = [
            weixin_status_service,
            message_service,
            message_factory_service,
            processor_service,
            rpa_service,
            dat_decrypt_service,
            new_friend_check_service,
        ]
        if mqtt_service:
            services_list.append(mqtt_service)

        self.dat_decrypt_service = dat_decrypt_service
        self.processor_service = processor_service

        return services_list

    def add_status_callback(self, callback):
        """
        注册状态变更回调。
        回调函数签名: callback(new_status: str, bot: Bot)
        """
        self._status_callbacks.append(callback)

    def _notify_status(self, status):
        """
        内部方法：触发所有已注册的状态回调。
        """
        self._status = status
        for cb in self._status_callbacks:
            try:
                cb(status, self)
            except Exception as e:
                self.logger.error(f"Status callback error: {e}")

    def setup(self):
        """
        执行所有耗时和阻塞的启动操作。
        自动调用所有注册组件的setup方法，并确保微信和主窗口初始化。
        """
        self._notify_status(self.STATUS_STARTING)
        self.logger.info("--- Starting Bot Setup ---")

        for component in self._components:
            if hasattr(component, "setup"):
                self.logger.info(f"Setting up {component.__class__.__name__}...")
                component.setup()

        # 检查微信客户端状态，等待其准备就绪
        status_service = next(
            (s for s in self._components if isinstance(s, WeixinStatusService)), None
        )
        if status_service:
            self.logger.info("Checking WeChat status...")
            while not status_service.check_weixin_status():
                self.logger.info("Waiting for WeChat client to be ready...")
                time.sleep(5)

        # 初始化主聊天窗口
        self.logger.info("Initializing main chat window...")
        while not self.window_manager.init_chat_window():
            self.logger.warning(
                "Failed to initialize chat window, retrying in 2 seconds..."
            )
            time.sleep(2)
        self.logger.info("Initializing pyq window...")

        # not include action in oss version
        """ if not self.window_manager.init_pyq_window():
            self.logger.warn("Failed to initialize pyq window, exiting...") """

        # 启动所有支持start方法的服务
        for component in self._components:
            if hasattr(component, "start"):
                self.logger.info(f"Starting service {component.__class__.__name__}...")
                component.start()
        self.is_running = True
        self._notify_status(self.STATUS_RUNNING)
        self.logger.info("--- Bot Setup Complete. All services are running. ---")

    def teardown(self):
        """
        按逆序安全地关闭和清理所有资源。
        """
        if not self.is_running:
            return
        self._notify_status(self.STATUS_STOPPING)
        self.logger.info("--- Starting Bot Teardown ---")
        for component in reversed(self._components):
            if hasattr(component, "stop"):
                self.logger.info(f"Stopping service {component.__class__.__name__}...")
                try:
                    component.stop()
                except Exception as e:
                    self.logger.error(
                        f"Error stopping {component.__class__.__name__}: {e}",
                        exc_info=True,
                    )
            if hasattr(component, "close"):
                self.logger.info(f"Closing resource {component.__class__.__name__}...")
                try:
                    component.close()
                except Exception as e:
                    self.logger.error(
                        f"Error closing {component.__class__.__name__}: {e}",
                        exc_info=True,
                    )
        if self.mcp_app:
            pass
            # self.mcp_app.stop()
        self.is_running = False
        self._notify_status(self.STATUS_STOPPED)
        self.logger.info("--- Bot Teardown Complete. ---")

    def start(self):
        """
        启动Bot并阻塞主线程，直到接收到终止信号。
        包含信号处理、setup、主循环、异常捕获与资源清理。
        """
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        try:
            self.setup()
            self.mcp_app = create_app(self.db, self.user_info, self.config)
            self.mcp_app.run("streamable-http")
        except Exception as e:
            self._notify_status(self.STATUS_FAILED)
            self.logger.critical(
                f"A critical error occurred during bot runtime: {e}", exc_info=True
            )
        finally:
            self.teardown()
            self.logger.info("Bot has shut down.")

    def _signal_handler(self, sig: int, frame: Any):
        """
        内部信号处理函数，触发关闭流程。
        """
        if self.is_running:
            self.logger.info(
                f"Received signal {signal.Signals(sig).name}, initiating graceful shutdown..."
            )
            self.is_running = False

    def register_legacy_plugins(self, plugins: List[Any]):
        """
        注册从文件系统加载的插件列表到ProcessorService。
        """
        if not hasattr(self, "processor_service") or not self.processor_service:
            self.logger.error(
                "ProcessorService is not initialized. Cannot register plugins."
            )
            return
        self.logger.info(f"Registering {len(plugins)} legacy plugins...")
        self.processor_service.register_plugins(plugins)

    def pause(self):
        """
        暂停Bot的消息获取（MessageService），使后续功能无法被触发。
        """
        if not self.is_running or self.is_paused:
            self.logger.info("Bot 已经处于暂停状态或未运行，无需重复暂停。")
            return
        self.is_paused = True
        self._notify_status(self.STATUS_PAUSED)
        # 定位MessageService实例
        message_service = next(
            (s for s in self._components if isinstance(s, MessageService)), None
        )
        if message_service and hasattr(message_service, "pause"):
            self.logger.info("暂停消息监听服务（MessageService）...")
            message_service.pause()
        else:
            self.logger.warning("MessageService 不支持暂停操作。")
        self.logger.info("Bot 已暂停。")

    def resume(self):
        """
        恢复Bot的消息获取（MessageService）。
        """
        if not self.is_running or not self.is_paused:
            self.logger.info("Bot 未处于暂停状态或未运行，无需恢复。")
            return
        self.is_paused = False
        self._notify_status(self.STATUS_RUNNING)
        message_service = next(
            (s for s in self._components if isinstance(s, MessageService)), None
        )
        if message_service and hasattr(message_service, "resume"):
            self.logger.info("恢复消息监听服务（MessageService）...")
            message_service.resume()
        else:
            self.logger.warning("MessageService 不支持恢复操作。")
        self.logger.info("Bot 已恢复运行。")

    def exit(self):
        """
        主动退出Bot，安全关闭所有服务。
        """
        self.logger.info("收到退出指令，开始关闭Bot...")
        self.teardown()
        self.logger.info("Bot 已安全退出。")
        # 触发状态变动通知
        self._notify_status(self.STATUS_STOPPED)
