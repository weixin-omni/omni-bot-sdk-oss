"""
通用工具函数模块。
包含剪贴板、图片、字符串处理等常用工具方法。
"""

import json
import logging
import os
import random
import struct
import tempfile
import time
import winreg
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx
import requests
import win32clipboard
import win32com.client
import win32con
from ruamel.yaml import YAML
from PIL import Image

logger = logging.getLogger(__name__)


def get_center_point(
    bbox: List[int], offset: Tuple[int, int] = (0, 0)
) -> Tuple[int, int]:
    """
    获取bbox的中心点，并在bbox范围内随机漂移

    Args:
        bbox: 边界框坐标 [x1, y1, x2, y2]
        offset: 额外的偏移量 (x, y)

    Returns:
        Tuple[int, int]: 随机漂移后的中心点坐标
    """
    # 计算中心点
    center_x = (bbox[0] + bbox[2]) / 2
    center_y = (bbox[1] + bbox[3]) / 2

    # 计算最大漂移范围（取bbox宽高的20%）
    max_x_offset = (bbox[2] - bbox[0]) * 0.2
    max_y_offset = (bbox[3] - bbox[1]) * 0.2

    # 在范围内随机漂移
    random_x = random.uniform(-max_x_offset, max_x_offset)
    random_y = random.uniform(-max_y_offset, max_y_offset)

    # 计算最终坐标（加上偏移量）
    final_x = center_x + random_x + offset[0]
    final_y = center_y + random_y + offset[1]

    return final_x, final_y


def get_weixin_path_from_registry():
    """
    从注册表中查找微信的安装路径。

    Returns:
        微信的安装路径，如果找到；否则返回 None。
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Tencent\Weixin"
        )  # 微信通常将安装信息存储在这里, HKCU更合适

        try:
            # 微信可能不直接存储可执行文件的路径，而是存储安装目录。
            # 尝试读取 InstallPath 或类似的键
            path = winreg.QueryValueEx(key, "InstallPath")[
                0
            ]  # 注意使用QueryValueEx，可以拿到数值，而不是handle
            winreg.CloseKey(key)

            # 验证路径是否存在且是目录
            if path and os.path.isdir(path):
                # 尝试找到微信的可执行文件。 微信的可执行文件名通常是 WeChat.exe 或 Weixin.exe
                executable_path = os.path.join(
                    path, "Weixin.exe"
                )  # 某些版本可能叫 Weixin.exe
                if os.path.exists(executable_path):
                    return executable_path
                print("在安装目录下没有找到微信.lnk")
                return None  # 未找到可执行文件

            else:
                print("注册表中的路径无效或不是目录。")
                return None

        except FileNotFoundError:
            winreg.CloseKey(key)
            print("注册表项中没有找到 'InstallPath'。")
            return None

    except FileNotFoundError:
        print("未找到微信的注册表项。")
        return None


def launch_wechat_via_shell(program_path: str):
    """
    通过 COM ShellExecute 接口启动程序，这是最接近用户双击行为的方式。
    可以有效绕过父进程检查，并确保子进程独立运行。

    Args:
        program_path: 要启动的程序的完整路径。
    """
    if not os.path.exists(program_path):
        print(f"错误: 找不到程序 '{program_path}'。")
        return

    print(f"[*] 正在通过 COM ShellExecute 模拟用户启动: {program_path}")

    try:
        # 创建 Shell.Application 对象
        # 这是与 Windows 外壳 (Explorer) 交互的 COM 接口
        shell = win32com.client.Dispatch("Shell.Application")

        # 调用 ShellExecute 方法
        # 参数说明：
        # 1. File: 要执行的文件路径
        # 2. Arguments: 传递给文件的参数 (这里为空)
        # 3. Directory: 工作目录 (我们让 Shell 自动处理，传 None 或空字符串)
        # 4. Verb: 操作动词，"open" 是默认操作，等同于双击
        # 5. Show: 窗口显示方式 (1 = 正常显示)
        shell.ShellExecute(program_path, "", "", "open", 1)

        print(f"[*] 启动请求已发送给 Windows Shell。")
        print("[*] 程序将由系统独立启动，Python 脚本现在可以安全退出了。")

    except Exception as e:
        import traceback

        print(f"[*] 通过 ShellExecute 启动时发生错误: {e}")
        traceback.print_exc()


def send_dingtalk_notification(
    message: str, at_mobiles: Optional[list] = None, is_at_all: bool = False
) -> bool:
    """
    发送钉钉通知消息

    Args:
        message: 要发送的消息内容
        at_mobiles: 要@的手机号列表
        is_at_all: 是否@所有人

    Returns:
        bool: 发送是否成功
    """
    try:
        # 读取配置文件
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = YAML().load(f)
            webhook_url = config["dingtalk"]["webhook_url"]
    except Exception as e:
        print(f"读取钉钉配置失败: {str(e)}")
        return False

    # 添加前缀
    full_message = f"微信：{message}"

    # 构建消息体
    data = {
        "msgtype": "text",
        "text": {"content": full_message},
        "at": {"atMobiles": at_mobiles or [], "isAtAll": is_at_all},
    }

    try:
        # 发送POST请求
        response = requests.post(
            webhook_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(data),
        )

        # 检查响应
        result = response.json()
        if result.get("errcode") == 0:
            return True
        else:
            print(f"钉钉消息发送失败: {result.get('errmsg')}")
            return False

    except Exception as e:
        print(f"钉钉消息发送异常: {str(e)}")
        return False


def send_dingtalk_markdown_notification(
    title: str, url: str, at_mobiles: Optional[list] = None, is_at_all: bool = False
) -> bool:
    """
    发送钉钉 Markdown 格式的通知消息，包含图片url

    Args:
        title: 消息标题
        url: 图片的url
        at_mobiles: 要@的手机号列表
        is_at_all: 是否@所有人

    Returns:
        bool: 发送是否成功
    """
    try:
        # 读取配置文件
        with open("config.yaml", "r", encoding="utf-8") as f:
            config = YAML().load(f)
            webhook_url = config["dingtalk"]["webhook_url"]
    except Exception as e:
        print(f"读取钉钉配置失败: {str(e)}")
        return False

    # 构建 Markdown 内容
    markdown_content = f"""### {title}
![图片]({url})
"""

    # 构建消息体
    data = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": markdown_content},
        "at": {"atMobiles": at_mobiles or [], "isAtAll": is_at_all},
    }

    try:
        # 发送POST请求
        response = requests.post(
            webhook_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(data),
        )

        # 检查响应
        result = response.json()
        if result.get("errcode") == 0:
            return True
        else:
            print(f"钉钉消息发送失败: {result.get('errmsg')}")
            return False

    except Exception as e:
        print(f"钉钉消息发送异常: {str(e)}")
        return False


def save_clipboard_image_to_temp() -> Optional[str]:
    """
    将剪贴板中的图片保存到临时文件

    Returns:
        str: 临时文件的路径，如果失败则返回 None
    """
    try:
        import tempfile
        from io import BytesIO

        import win32clipboard

        # 打开剪贴板
        win32clipboard.OpenClipboard()

        # 检查剪贴板中是否有图片
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            # 获取图片数据
            image_data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)

            # 创建临时文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_path = temp_file.name

            # 将图片数据写入临时文件
            with open(temp_path, "wb") as f:
                f.write(image_data)

            win32clipboard.CloseClipboard()
            return temp_path

        win32clipboard.CloseClipboard()
        return None

    except Exception as e:
        print(f"保存剪贴板图片时出错: {str(e)}")
        return None


def read_temp_image(image_path: str) -> bool:
    """
    读取临时图片文件并复制到剪贴板

    Args:
        image_path: 图片文件路径

    Returns:
        bool: 操作是否成功
    """
    try:
        from io import BytesIO

        import win32clipboard

        if not os.path.exists(image_path):
            print(f"图片文件不存在: {image_path}")
            return False

        # 打开图片
        image = Image.open(image_path)

        # 将图片转换为位图格式
        output = BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]  # 去掉BMP文件头
        output.close()

        # 打开剪贴板并写入数据
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

        return True

    except Exception as e:
        print(f"读取图片到剪贴板时出错: {str(e)}")
        return False


def activate_weixin_window():
    """
    激活微信窗口
    """
    weixin_path = get_weixin_path_from_registry()
    if weixin_path:
        launch_wechat_via_shell(weixin_path)


def set_clipboard_text(text: str) -> bool:
    """设置剪贴板文本"""
    logger.info(f"设置剪切板内容：{text}")
    try:
        if not text or not text.strip():
            return False

        try:
            import pyperclip

            pyperclip.copy(text)
            time.sleep(0.3)
            return True
        except Exception as e:
            pass

        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()
            time.sleep(0.3)
            return True
        except Exception as e:
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
            return False

    except Exception as e:
        return False


def copy_file_to_clipboard(file_path: str) -> bool:
    """
    将文件路径放入Windows剪贴板，使其可以作为文件被粘贴。
    """
    if not os.path.exists(file_path):
        logger.error(f"错误：文件不存在于路径 '{file_path}'")
        return False

    # 获取文件的绝对路径，确保格式正确
    abs_path = os.path.abspath(file_path)

    # 1. 准备文件路径字节数据
    # Windows API 期望 UTF-16 little endian 编码的路径，并以 '\0' 字节终止。
    # 对于 CF_HDROP，整个路径列表需要以额外的 '\0' 字节终止。
    # Python 的 str.encode('utf-16-le') 会自动在字符串末尾添加一个 '\0' 字节。
    # 所以，我们需要再添加一个 '\0' 字节来表示列表的结束。
    # 如果有多个文件，每个文件路径都以 '\0' 结束，整个列表以 '\0\0' 结束。
    # 对于单个文件，就是 'path\0\0'
    path_bytes = abs_path.encode("utf-16-le") + b"\0"

    # 2. 构建 DROPFILES 结构体
    # struct DROPFILES {
    #   DWORD pFiles;  // 偏移量，从结构体开始到第一个文件名的字节数
    #   POINT pt;      // 拖放点 (x, y)，通常为 (0,0) 用于剪贴板
    #   BOOL  fNC;     // 非客户区标志，剪贴板通常为 FALSE (0)
    #   BOOL  fWide;   // 宽字符标志，TRUE (1) 表示路径是 Unicode
    # };
    #
    # 在Windows API中，DWORD, POINT的成员(LONG), BOOL通常都是4字节。
    # 所以 DROPFILES 结构体总共 4(pFiles) + 4(pt.x) + 4(pt.y) + 4(fNC) + 4(fWide) = 20字节。
    # struct.pack 的格式字符串：
    # '<' 表示 little-endian (Windows 默认)
    # 'I' 表示 unsigned int (4字节)
    # 'i' 表示 signed int (4字节)
    # 这里我们都用 'I' 因为它们都是无符号或布尔值，且通常是4字节。

    # pFiles: 文件名数据开始的偏移量，即 DROPFILES 结构体的大小 (20字节)
    pFiles_offset = 20  # sizeof(DROPFILES)

    drop_files_header = struct.pack(
        "<IIIII",  # < (little-endian) + 5个 I (unsigned int, 4字节)
        pFiles_offset,  # pFiles: 偏移量
        0,  # pt.x: 拖放点X坐标 (用于剪贴板时通常为0)
        0,  # pt.y: 拖放点Y坐标 (用于剪贴板时通常为0)
        0,  # fNC: 非客户区标志 (用于剪贴板时通常为0)
        1,  # fWide: 宽字符标志 (1表示Unicode, 0表示ANSI)
    )

    # 3. 将头部和文件路径数据拼接起来
    clipboard_data = drop_files_header + path_bytes

    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        # CF_HDROP 是文件拖放格式，表示剪贴板中是文件列表
        win32clipboard.SetClipboardData(win32con.CF_HDROP, clipboard_data)
        win32clipboard.CloseClipboard()
        logger.info(f"文件 '{file_path}' 已复制到Windows剪贴板，可以粘贴为文件。")
        return True
    except Exception as e:
        logger.error(f"复制文件到剪贴板失败：{e}")
        return False


async def download_file_if_url(file_path: str) -> str:
    """
    如果 file_path 是网络地址，则下载到本地临时文件夹，返回本地文件路径。
    优先使用响应头 Content-Disposition 的文件名。
    禁止下载可执行程序，单文件最大200MB。
    如果已存在同名文件，则在文件名后依次添加 (1)、(2) 等，直到文件不存在。
    如果不是网络地址，则直接返回原路径。
    """
    MAX_SIZE = 200 * 1024 * 1024  # 200MB
    DANGEROUS_EXTS = {
        ".exe",
        ".bat",
        ".cmd",
        ".msi",
        ".dll",
        ".scr",
        ".com",
        ".vbs",
        ".js",
        ".ps1",
        ".cpl",
        ".jar",
        ".pif",
        ".gadget",
        ".msc",
    }

    parsed = urlparse(file_path)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("只允许 http/https 协议下载")

    async with httpx.AsyncClient() as client:
        response = await client.get(file_path, follow_redirects=True)
        response.raise_for_status()

        # 优先从 Content-Disposition 获取文件名
        filename = None
        content_disp = response.headers.get("content-disposition")
        if content_disp:
            import re

            match = re.search(r"filename\*=UTF-8\'\\?([^\s;]+)", content_disp)
            if match:
                from urllib.parse import unquote

                filename = unquote(match.group(1))
            else:
                match = re.search(r'filename="?([^";]+)"?', content_disp)
                if match:
                    filename = match.group(1)
        if not filename:
            filename = os.path.basename(parsed.path) or "downloaded_file"

        # 路径穿越检查
        if ".." in filename or os.path.isabs(filename):
            raise ValueError("文件名非法，存在路径穿越风险")

        # 检查危险扩展名
        ext = os.path.splitext(filename)[1].lower()
        if ext in DANGEROUS_EXTS:
            raise ValueError(f"禁止下载可执行或危险类型文件: {ext}")

        temp_dir = tempfile.gettempdir()
        base, ext2 = os.path.splitext(filename)
        candidate = filename
        i = 1
        while os.path.exists(os.path.join(temp_dir, candidate)):
            candidate = f"{base}({i}){ext2}"
            i += 1
        local_path = os.path.join(temp_dir, candidate)

        # 检查 Content-Length
        content_length = response.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_SIZE:
                    raise ValueError("文件过大，超过200MB限制")
            except Exception:
                pass

        # 流式写入，防止超大文件
        total = 0
        with open(local_path, "wb") as f:
            async for chunk in response.aiter_bytes(chunk_size=8192):
                if chunk:
                    total += len(chunk)
                    if total > MAX_SIZE:
                        f.close()
                        os.remove(local_path)
                        raise ValueError("文件写入超出200MB限制，已中断并删除")
                    f.write(chunk)
        return local_path


def ensure_dir_exists(path: str):
    """
    确保目录存在，不存在则创建。
    Args:
        path (str): 目录路径
    """
    if not os.path.exists(path):
        os.makedirs(path)
