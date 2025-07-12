"""
共享队列实例模块
"""

from queue import Queue
from typing import Any, Dict

# 全局消息队列，供消息分发与处理模块使用
message_queue = Queue()

# 全局RPA任务队列，供RPA相关服务使用
rpa_task_queue = Queue()

# 全局状态队列，用于状态变更通知
status_queue = Queue()


def get_queue_stats() -> Dict[str, Any]:
    """
    获取所有全局队列的状态信息（队列长度及是否为空）。
    """
    return {
        "message_queue": {
            "size": message_queue.qsize(),
            "empty": message_queue.empty(),
        },
        "rpa_task_queue": {
            "size": rpa_task_queue.qsize(),
            "empty": rpa_task_queue.empty(),
        },
        "status_queue": {"size": status_queue.qsize(), "empty": status_queue.empty()},
    }
