"""
自定义异常类模块
"""


class WeixinOmniError(Exception):
    """
    Omni-Bot项目的基础异常类。
    所有自定义异常均应继承自该类，便于统一捕获和处理。
    """

    pass


class ConfigError(WeixinOmniError):
    """
    配置相关错误。
    用于配置文件缺失、格式错误等场景。
    """

    pass


class DatabaseError(WeixinOmniError):
    """
    数据库相关错误。
    用于数据库连接、查询、操作等异常。
    """

    pass


class MQTTError(WeixinOmniError):
    """
    MQTT相关错误。
    用于MQTT连接、消息发布/订阅等异常。
    """

    pass


class RPAError(WeixinOmniError):
    """
    RPA相关错误。
    用于RPA流程、任务等异常。
    """

    pass


class WorkerError(WeixinOmniError):
    """
    Worker相关错误。
    用于多进程/多线程Worker异常。
    """

    pass


class APIError(WeixinOmniError):
    """
    API相关错误。
    用于接口调用、参数校验、状态码异常等。
    """

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code
