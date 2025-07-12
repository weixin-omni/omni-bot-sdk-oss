"""
MQTT客户端模块
"""

import json
import logging
import time
from typing import Callable, Optional

import paho.mqtt.client as mqtt


class MQTTClient:
    """
    MQTT 客户端封装。
    支持自动重连、消息回调、主题订阅与发布等常用功能。
    """

    def __init__(
        self,
        host: str,
        port: int,
        client_id: str,
        username: str = None,
        password: str = None,
    ):
        """
        初始化MQTT客户端。
        支持用户名密码认证，自动生成唯一client_id。
        """
        self.client_id = client_id + "_" + str(time.time())
        self.client = mqtt.Client(client_id=self.client_id)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.message_callback: Optional[Callable] = None
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"MQTTClient initialized with client_id: {self.client_id}")
        if username and password:
            self.client.username_pw_set(username, password)
            self.logger.info(f"已设置MQTT认证信息 - 用户名: {username}")

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

        # 设置自动重连延迟
        self.client.reconnect_delay_set(min_delay=1, max_delay=120)

    def on_connect(self, client, userdata, flags, rc):
        """
        连接回调。
        连接成功/失败时自动触发。
        """
        if rc == 0:
            self.logger.info(f"MQTT连接成功:{self.client_id}")
            client.connected_flag = True
            client.bad_connection_flag = False
        else:
            self.logger.error(f"MQTT连接失败，错误码: {rc}")
            client.bad_connection_flag = True
            if rc == 7:
                self.logger.error("MQTT认证失败，请检查用户名和密码是否正确")

    def on_disconnect(self, client, userdata, rc):
        """
        断开连接回调。
        包含自动重连逻辑。
        """
        self.logger.info("MQTT连接断开")
        client.connected_flag = False
        if rc != 0:
            self.logger.error(f"意外断开连接，错误码: {rc}")
            client.bad_connection_flag = True
            try:
                self.connect()
            except Exception as e:
                self.logger.error(f"自动重连失败: {e}")

    def on_message(self, client, userdata, msg):
        """
        消息接收回调。
        自动解码JSON消息并调用用户自定义回调。
        """
        try:
            payload = json.loads(msg.payload.decode())
            if self.message_callback:
                self.message_callback({"topic": msg.topic, "payload": payload})
        except Exception as e:
            self.logger.error(f"处理MQTT消息时出错: {e}")

    def connect(self):
        """
        连接到MQTT服务器。
        支持匿名连接和认证连接。
        """
        if not (self.username and self.password):
            self.logger.warning("未提供MQTT认证信息，尝试匿名连接")
        try:
            self.client.connect(self.host, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            self.logger.error(f"MQTT连接失败: {e}")
            raise

    def subscribe(self, topic: str):
        """
        订阅指定主题。
        """
        self.client.subscribe(topic)
        self.logger.info(f"已订阅主题: {topic}")

    def publish(self, topic: str, payload: dict):
        """
        发布消息到指定主题。
        """
        try:
            self.client.publish(topic, json.dumps(payload))
        except Exception as e:
            self.logger.error(f"发布MQTT消息时出错: {e}")

    def set_message_callback(self, callback: Callable):
        """
        设置自定义消息回调函数。
        回调参数为dict，包含topic和payload。
        """
        self.message_callback = callback

    def disconnect(self):
        """
        断开与MQTT服务器的连接。
        """
        self.client.loop_stop()
        self.client.disconnect()
