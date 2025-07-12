# mcp/dispatchers.py
import time
from typing import Any, Dict

from omni_bot_sdk.clients.mqtt_client import MQTTClient
from omni_bot_sdk.models import UserInfo
from omni_bot_sdk.rpa.action_handlers import RPAActionType


class MqttCommandDispatcher:
    """
    使用MQTT实现的命令分发器。
    支持通用消息分发和RPA操作分发。
    """

    def __init__(self, mqtt_client: MQTTClient, user_info: UserInfo):
        """
        初始化分发器，注入MQTT客户端和用户信息。
        """
        self.mqtt = mqtt_client
        self.user = user_info

    def dispatch(self, topic: str, payload: Dict[str, Any]) -> None:
        """
        发送通用MQTT消息。
        检查MQTT连接状态，异常时抛出错误。
        """
        if not self.mqtt.client.connected_flag or self.mqtt.client.bad_connection_flag:
            raise ConnectionError("MQTT连接不可用，请检查MQTT服务状态。")
        self.mqtt.publish(topic, payload)

    def dispatch_rpa(self, action_type: str, action_data: Dict[str, Any]) -> str:
        """
        发送RPA操作到专用MQTT主题。
        返回操作提交结果字符串。
        """
        topic = f"msg/{self.user.account}/other_rpa_action"
        payload = {
            "create_time": int(time.time()),
            "action_type": action_type,
            "action_data": action_data,
        }
        self.dispatch(topic, payload)
        return f"RPA操作 '{str(action_type)}' 已成功提交。"
