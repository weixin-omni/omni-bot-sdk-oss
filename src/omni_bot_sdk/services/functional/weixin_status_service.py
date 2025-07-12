"""
微信状态服务模块。
提供微信运行状态检测、窗口状态管理等服务。
"""

import logging
import threading
import time
from typing import Optional

import pyautogui
import uuid
import boto3
import io
from omni_bot_sdk.rpa.image_processor import ImageProcessor
from omni_bot_sdk.rpa.ocr_processor import OCRProcessor
from omni_bot_sdk.rpa.window_manager import WindowManager, WindowTypeEnum
from omni_bot_sdk.utils.helpers import (
    get_center_point,
    send_dingtalk_markdown_notification,
    send_dingtalk_notification,
)


class WeixinStatusService:
    """微信状态检查服务"""

    def __init__(
        self,
        config: dict,
        window_manager: WindowManager,
        image_processor: ImageProcessor,
        ocr_processor: OCRProcessor,
    ):
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.check_interval = 120  # 2分钟检查一次
        self.check_thread: Optional[threading.Thread] = None
        self.window_manager = window_manager
        self.image_processor = image_processor
        self.ocr_processor = ocr_processor
        self.need_recover = False
        self.config = config

    def start(self):
        """启动服务"""
        if self.is_running:
            self.logger.warning("微信状态检查服务已经在运行中")
            return False

        self.is_running = True
        self.check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self.check_thread.start()
        self.logger.info("微信状态检查服务已启动")
        return True

    def stop(self):
        """停止服务"""
        if not self.is_running:
            self.logger.warning("微信状态检查服务未在运行")
            return False

        self.is_running = False
        if self.check_thread:
            self.check_thread.join(timeout=5)
        self.logger.info("微信状态检查服务已停止")
        return True

    def _check_loop(self):
        """检查循环"""
        while self.is_running:
            try:
                if not self.check_weixin_status():
                    self.logger.warning("微信状态异常，发送钉钉通知")
                    send_dingtalk_notification("微信状态异常，请检查微信是否正常运行")
                    time.sleep(10)
                    continue
                time.sleep(self.check_interval)
            except Exception as e:
                self.logger.error(f"检查微信状态时出错: {str(e)}")
                time.sleep(self.check_interval)

    def check_weixin_status(self) -> bool:
        """
        检查微信窗口是否正常
        如果不正常，检测是否掉线，走重新登录逻辑
        """
        if not self._check_wechat_window_size():
            # TODO 获取到微信的窗口
            chat_window = self.window_manager.get_window(WindowTypeEnum.MainWindow)
            if not chat_window:
                self.logger.error("微信窗口未找到，请检查微信是否正常运行")
                return False
            self.need_recover = True
            region = [
                chat_window.left,
                chat_window.top,
                chat_window.width,
                chat_window.height,
            ]

            screenshot = self.image_processor.take_screenshot(
                region=region, save_path="runtime_images/weixin_status.png"
            )
            parser_result = self.ocr_processor.process_image(image=screenshot)

            # 检查是否需要重新登录
            parser_result1 = self._calc_similarity(
                "为了你的账号安全，请重新登录", parser_result, 0.85
            )
            if len(parser_result1) == 0:
                parser_result1 = self._calc_similarity(
                    "你已退出微信", parser_result, 0.85
                )

            parser_result2 = self._calc_similarity("我知道了", parser_result, 0.85)

            if len(parser_result1) > 0 and len(parser_result2) > 0:
                self.logger.warn("微信确实被T了，准备重新登录")
                pyautogui.moveTo(
                    get_center_point(
                        parser_result2[0]["pixel_bbox"],
                        offset=(chat_window.left, chat_window.top),
                    )
                )
                pyautogui.click()
                pyautogui.sleep(1)

            # 检查是否存在"进入微信"按钮
            screenshot = self.image_processor.take_screenshot(
                region=region, save_path="runtime_images/weixin_status.png"
            )
            parser_result = self.ocr_processor.process_image(image=screenshot)
            parser_result3 = self._calc_similarity("进入微信", parser_result, 0.85)

            if len(parser_result3) > 0:
                self.logger.info("存在进入微信按钮，点击等二维码展示")
                pyautogui.moveTo(
                    get_center_point(
                        parser_result3[0]["pixel_bbox"],
                        offset=(chat_window.left, chat_window.top),
                    )
                )
                pyautogui.click()
                time.sleep(3)
            else:
                self.logger.warn("找不到进入微信的按钮，可能已经加载了二维码了")

            screenshot = self.image_processor.take_screenshot(
                region=region, save_path="runtime_images/weixin_status.png"
            )
            parser_result = self.ocr_processor.process_image(image=screenshot)
            parser_result4 = self._calc_similarity("扫码登录", parser_result, 0.85)

            if len(parser_result4) > 0:
                self.logger.info("存在扫码登录按钮，需要扫码登录")
                # 读取S3配置
                s3_conf = self.config.get("s3", {})
                object_name = f"weixin_status_{uuid.uuid4().hex}.png"
                s3_client = boto3.client(
                    service_name="s3",
                    endpoint_url=s3_conf.get("endpoint_url"),
                    aws_access_key_id=s3_conf.get("access_key"),
                    aws_secret_access_key=s3_conf.get("secret_key"),
                    region_name=s3_conf.get("region"),
                )
                bucket_name = s3_conf.get("bucket")
                public_url_prefix = s3_conf.get("public_url_prefix", "")
                try:
                    with open("runtime_images/weixin_status.png", "rb") as f:
                        s3_client.upload_fileobj(
                            io.BytesIO(f.read()), bucket_name, object_name
                        )
                    r2_url = f"{public_url_prefix.rstrip('/')}/{object_name}"
                    send_dingtalk_markdown_notification("微信二维码登录", r2_url)
                    self.logger.info(f"上传二维码到R2成功: {r2_url}")
                    time.sleep(5)
                    return False
                except Exception as e:
                    self.logger.error(f"上传二维码到R2失败: {e}")
                    send_dingtalk_notification(f"上传二维码到R2失败: {e}")
                    return False
            else:
                # self.logger.error("全部流程都找不到，但是窗口大小不正常，提示用户")
                return self._check_wechat_window_size()

        return True

    def _check_wechat_window_size(self) -> bool:
        """检查微信窗口是否在前台"""
        chat_window = self.window_manager.get_window(WindowTypeEnum.MainWindow)
        if not chat_window:
            self.logger.error("微信窗口未找到，请检查微信是否正常运行")
            return False
        if chat_window.width < 600:
            self.logger.warn("微信窗口大小不匹配，当前应该是登录窗口")
            return False
        else:
            self.logger.info("微信窗口大小正常")
            if self.need_recover:
                self.logger.info("窗口大小正常，但是需要重新初始化窗口")
                self.window_manager.init_chat_window()
                self.need_recover = False
            return True

    def _calc_similarity(
        self, search_text: str, formatted_results: list, score_cutoff: float = 0.6
    ) -> list:
        """计算文本相似度"""
        from Levenshtein import ratio

        for result in formatted_results:
            result["similarity"] = ratio(
                search_text,
                result["label"],
                processor=lambda x: x.lower().replace(" ", ""),
                score_cutoff=score_cutoff,
            )
        formatted_results = [
            result
            for result in formatted_results
            if result["similarity"] >= float(score_cutoff)
        ]
        return formatted_results
