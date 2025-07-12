"""
窗口管理模块。
提供微信窗口的查找、激活、区域分析、会话切换等自动化能力。
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, Optional, Tuple

import pyautogui
import win32gui
from omni_bot_sdk.rpa.image_processor import ImageProcessor
from omni_bot_sdk.rpa.ocr_processor import OCRProcessor
from omni_bot_sdk.utils.helpers import get_center_point, set_clipboard_text
from omni_bot_sdk.utils.mouse import human_like_mouse_move
from omni_bot_sdk.utils.size_config import suggest_size

pyautogui.FAILSAFE = False


class MenuTypeEnum(Enum):
    """
    菜单类型
    """

    Chat = "聊天"
    Contact = "联系人"
    Favorite = "收藏"
    Friend = "朋友圈"

    FriendNotification = "朋友圈通知"
    FriendSend = "朋友圈发送"
    FrendRefresh = "朋友圈刷新"


class WindowTypeEnum(Enum):
    """
    对使用到的窗口进行归类，方便查找，只使用title不可靠
    似乎微信4.x 的类名都是 Qt51514QWindowIcon，切记不可直接用类名，万一更新Qt版本就完蛋拉~
    """

    MainWindow = "MainWindow"  # <Win32Window left="0", top="0", width="1008", height="1360", title="微信">
    InviteMemberWindow = "InviteMemberWindow"  # <Win32Window left="34", top="310", width="938", height="738", title="微信添加群成员">
    InviteConfirmWindow = "InviteConfirmWindow"  # <Win32Window left="298", top="536", width="413", height="288", title="Weixin">
    InviteResonWindow = "InviteResonWindow"  # <Win32Window left="298", top="505", width="413", height="350", title="Weixin">
    RemoveMemberWindow = "RemoveMemberWindow"  # <Win32Window left="34", top="310", width="938", height="738", title="微信移出群成员">
    AddFriendWindow = "AddFriendWindow"  # <Win32Window left="274", top="312", width="450", height="825", title="通过朋友验证">
    UnableInviteWindow = "UnableInviteWindow"  # <Win32Window left="298", top="559", width="413", height="243", title="Weixin">
    SearchHistoryWindow = "SearchHistoryWindow"  # <Win32Window left="214", top="372", width="913", height="800", title="搜索聊天记录">
    FriendWindow = "FriendWindow"  # <Win32Window left="1015", top="1", width="688", height="1358", title="朋友圈">
    PublicAnnouncementWindow = "PublicAnnouncementWindow"  # <Win32Window left="158", top="278", width="709", height="812", title="“微信 GUI RPA 开发群”的群公告">
    RoomInputConfirmBox = "RoomInputConfirmBox"  # 窗口类名: Qt51514QWindowIcon <Win32Window left="298", top="556", width="413", height="246", title="Weixin">
    MenuWindow = "MenuWindow"  # <Win32Window left="0", top="0", width="1008", height="1360", title="Weixin">
    # ToolSaveBitsWindow = "ToolSaveBitsWindow"  # 搜索联系人也是这个 <Win32Window left="61", top="61", width="460", height="128", title="Weixin">
    SearchContactWindow = "SearchContactWindow"  # <Win32Window left="61", top="61", width="460", height="128", title="Weixin">


class WindowManager:
    """窗口管理器，处理所有窗口相关的操作"""

    # TODO 重新登陆以后，需要重新初始化，否则的话，window都变了，操作无效
    def __init__(
        self,
        image_processor: ImageProcessor,
        ocr_processor: OCRProcessor,
        rpa_config: dict = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.size_config = suggest_size()
        self.weixin_windows = {}
        self.current_window = None
        self.ROOM_SIDE_BAR_WIDTH = 0
        self.MSG_TOP_X = 0
        self.MSG_TOP_Y = 0
        self.MSG_WIDTH = 0
        self.MSG_HEIGHT = 0
        self.SIDE_BAR_WIDTH = 0
        self.SESSION_LIST_WIDTH = 0
        self.TITLE_BAR_HEIGHT = 0
        self.ICON_CONFIGS = {
            "send_button": {
                "name": "发送按钮",
                "color": "red",
                "position": None,
            },
            "search_icon": {
                "name": "搜索输入框",
                "color": "yellow",
                "position": None,
            },
        }
        self.image_processor = image_processor
        self.ocr_processor = ocr_processor
        self.last_switch_session = None
        self.last_switch_session_time = None
        self.rpa_config = rpa_config or {}
        # 直接将常用配置项赋值为实例属性，便于后续直接访问
        self.action_delay = self.rpa_config.get("action_delay", 0.3)
        self.side_bar_delay = self.rpa_config.get("side_bar_delay", 3)
        self.scroll_delay = self.rpa_config.get("scroll_delay", 1)
        self.switch_contact_delay = self.rpa_config.get("switch_contact_delay", 0.3)
        self.window_show_delay = self.rpa_config.get("window_show_delay", 1.5)
        self.window_margin = self.rpa_config.get("window_margin", 20)
        self.room_action_offset = tuple(
            self.rpa_config.get("room_action_offset", (0, -30))
        )
        self.search_contact_offset = tuple(
            self.rpa_config.get("search_contact_offset", (0, 40))
        )
        self.color_ranges = self.rpa_config.get("color_ranges", {})

    def activate_input_box(self, offset_x: int = 0) -> bool:
        """
        激活输入框
        这里的offset时为了处理多个窗口，目前没有使用
        点击两次是为了处理有可能的存在的侧边栏没有关闭的情况，暂时不使用vl模型解决
        """
        try:
            send_button = self.get_icon_position("send_button")
            if not send_button:
                return False

            send_x, send_y = get_center_point(send_button)
            pyautogui.click(self.MSG_TOP_X + 50 + offset_x, send_y)
            time.sleep(self.action_delay)
            pyautogui.click(self.MSG_TOP_X + 50 + offset_x, send_y)
            return True

        except Exception as e:
            self.logger.error(f"激活输入框时出错: {str(e)}")
            return False

    def get_icon_position(self, icon_name: str) -> Optional[Dict]:
        """获取图标位置"""
        if icon_name in self.ICON_CONFIGS:
            return self.ICON_CONFIGS[icon_name]["position"]
        return None

    def init_chat_window(self) -> bool:
        """
        初始化聊天窗口
        TODO 核心，需要做好鲁棒性
        """
        self.logger.info("开始初始化聊天窗口...")
        # 切换到微信到前台
        # 对当前页面进行截图
        # 然后根据像素进行匹配
        # 部分区域需要使用OCR匹配
        # 也可以考虑先用OCR来识别一次
        # 添加异常逻辑，像素扫描数组越界
        try:
            if self._is_wechat_foreground():
                time.sleep(self.scroll_delay)
                init_result = self._init_window_part_size()
                if init_result:
                    self.weixin_windows["微信"] = {
                        "window": pyautogui.getWindowsWithTitle("微信")[0],
                        "MSG_TOP_X": self.MSG_TOP_X,
                        "MSG_TOP_Y": self.MSG_TOP_Y,
                        "MSG_WIDTH": self.MSG_WIDTH,
                        "MSG_HEIGHT": self.MSG_HEIGHT,
                        "region": [
                            0,
                            0,
                            self.size_config.width,
                            self.size_config.height,
                        ],
                    }
                    return True
                return False
            else:
                self.logger.info("微信窗口未激活，重新激活")
                return False
        except Exception as e:
            self.logger.error(f"初始化聊天窗口时出错: {str(e)}")
            return False

    def _init_window_part_size(self):
        """
        直接扫描截图像素，分析功能区域
        需要增加 通讯录 和 朋友圈
        """
        self.logger.info(
            f"微信窗口预设尺寸：{self.size_config.width}, {self.size_config.height}"
        )
        pyautogui.moveTo(150, 150)
        pyautogui.scroll(10000)
        time.sleep(self.action_delay)
        pyautogui.click()
        time.sleep(self.scroll_delay)
        # 主窗口截图，初始化布局完全按照这个截图进行
        screenshot = self.image_processor.take_screenshot(
            region=[
                0,
                0,
                self.size_config.width,
                self.size_config.height,
            ],
        )

        # 读取图片
        # 获取像素数据
        pixels = screenshot.load()
        SIDE_BAR_WIDTH = 0
        SESSION_LIST_WIDTH = 0
        MSG_WIDTH = 0
        breakPoint = []
        # 第一个变化点是 侧边栏和会话列表，第二个变化点是会话列表右侧和聊天详情，每次变化产生两个点
        j = 10
        for i in range(10, 450):
            if i == 10:
                pass
            else:
                if pixels[i, j] != pixels[i - 1, j]:
                    breakPoint.append(i)
                    if len(breakPoint) == 4:
                        break
        SIDE_BAR_WIDTH = breakPoint[1]
        SESSION_LIST_WIDTH = breakPoint[3] - SIDE_BAR_WIDTH
        # 从 SIDE_BAR_WIDTH + SESSION_LIST_WIDTH + 1 开始，向下匹配，第一个变色就是标题栏的高度，第二个就是消息栏的区域
        self.MSG_TOP_X = breakPoint[3]
        breakPoint.clear()
        j = SIDE_BAR_WIDTH + SESSION_LIST_WIDTH + 3
        for i in range(10, 500):
            if pixels[j, i] != pixels[j, i - 1]:
                breakPoint.append(i)
                if len(breakPoint) == 4:
                    break
        TITLE_BAR_HEIGHT = breakPoint[0]
        self.MSG_TOP_Y = TITLE_BAR_HEIGHT

        breakPoint.clear()
        j = self.MSG_TOP_X + 2
        TITLE_BAR_HEIGHT = 0
        MSG_HEIGHT = 0
        for i in range(10, self.size_config.height - 10):
            if i == 10:
                pass
            else:
                if pixels[j, i] != pixels[j, i - 1]:
                    breakPoint.append(i)
                    if len(breakPoint) == 4:
                        break
        # 如果一路找下来，一片白板，明显就是右侧没有加载东西，是刚刚启动，还有一种情况，就是在公众号那些页面也有可能，其实这里是好弄的，主要是不在聊天页面，发送按钮不好找
        # TODO 用 yolo找头像，然后确定点击的位置更加好
        if len(breakPoint) < 3:
            # 主动去点击第一个存在的用户，让他切换一下
            # pyautogui.moveTo()
            # pyautogui.click()
            return False
        TITLE_BAR_HEIGHT = breakPoint[1]
        self.MSG_TOP_Y = TITLE_BAR_HEIGHT
        MSG_HEIGHT = breakPoint[3] - TITLE_BAR_HEIGHT - 2
        MSG_WIDTH = self.size_config.width - SIDE_BAR_WIDTH - SESSION_LIST_WIDTH - 2
        # 联系人区域的右上角，就是MSG_TOP的坐标，同时也是MSG的左上角，发送内容工具栏的右上角就是MSG区域的右下角
        self.MSG_WIDTH = MSG_WIDTH
        self.MSG_HEIGHT = MSG_HEIGHT
        self.logger.info(f"MSG_WIDTH: {self.MSG_WIDTH}, MSG_HEIGHT: {self.MSG_HEIGHT}")

        # 计算搜索框的坐标，直接取会话列表的中间位置，从上到下扫描高度范围内就行啦~
        # TODO 优化，找到上下边框，再从中点向左右两侧扫描，可以拿到更完整的区域，目前先这样
        search_box_point = [SIDE_BAR_WIDTH + SESSION_LIST_WIDTH // 2, 0]
        breakPoint.clear()
        for i in range(10, TITLE_BAR_HEIGHT):
            if pixels[search_box_point[0], i] != pixels[search_box_point[0], i - 1]:
                breakPoint.append(i)
                if len(breakPoint) == 3:
                    break
        search_box_point[1] = (breakPoint[1] + breakPoint[2]) // 2
        self.logger.info(f"search_btn_bbox: {search_box_point}")

        # 计算发送按钮的坐标, 从右下角开始找，而不是左上角，只要斜向找到变色的元素就可以了，注意那个圆角, 第一个元素就是那个发送的右下角，然后查找一下发送按钮的高度和宽度就可以了
        # 这里实际上需要保留一下右下角的距离，这样的话，就不用管窗口的大小，直接用距离算就行了
        send_btn_bbox = [0, 0, 0, 0]
        for i in range(20, 200):
            if (
                pixels[self.size_config.width - 1 - i, self.size_config.height - 1 - i]
                != pixels[
                    self.size_config.width - 1 - i, self.size_config.height - 1 - i - 1
                ]
            ):
                send_btn_bbox[2] = self.size_config.width - 1 - i
                send_btn_bbox[3] = self.size_config.height - 1 - i
                break

        button_right_x = send_btn_bbox[2] - 3
        button_right_y = send_btn_bbox[3] - 3
        # 从 button_right_x 向左侧扫描200个像素，第一个变化的像素就是  send_btn_bbox[0]
        for i in range(0, 200):
            if (
                pixels[button_right_x - i, button_right_y]
                != pixels[button_right_x - i - 1, button_right_y]
            ):
                send_btn_bbox[0] = button_right_x - i
                break
            if (
                pixels[button_right_x, button_right_y - i]
                != pixels[button_right_x, button_right_y - i - 1]
            ):
                send_btn_bbox[1] = button_right_y - i

        self.logger.info(f"send_btn_bbox: {send_btn_bbox}")

        breakPoint.clear()
        icons = []
        for i in range(TITLE_BAR_HEIGHT, self.size_config.height // 2):
            if pixels[SIDE_BAR_WIDTH // 2, i] != pixels[SIDE_BAR_WIDTH // 2, i - 1]:
                breakPoint.append(i)
                if len(icons) == 0:
                    icons.append(i)
                if len(breakPoint) > 1:
                    if breakPoint[-1] - breakPoint[-2] > 30:
                        # self.logger.info(f"间隔 {breakPoint[-1] - breakPoint[-2]}")
                        icons.append(breakPoint[-2])
                        icons.append(breakPoint[-1])
        icons.append(breakPoint[-1])
        # self.logger.info(icons)
        # 两两一组，目前先关心前面两个是聊天和联系人
        all_result = []

        # 这里可能会出现多个菜单，数量不确定，所以要复杂处理
        menu_labels = [
            MenuTypeEnum.Chat.value,
            MenuTypeEnum.Contact.value,
            MenuTypeEnum.Favorite.value,
            MenuTypeEnum.Friend.value,
        ]

        for idx, i in enumerate(range(0, len(icons), 2)):
            bbox = [
                0,
                icons[i],
                SIDE_BAR_WIDTH,
                icons[i + 1],
            ]
            # 保存到 ICON_CONFIGS
            name = menu_labels[idx] if idx < len(menu_labels) else f"菜单{idx}"
            self.ICON_CONFIGS[name] = {
                "name": name,
                "color": None,
                "position": bbox,
            }
            all_result.append(
                {
                    "pixel_bbox": bbox,
                    "content": name,
                    "label": name,
                    "source": "动态计算",
                }
            )
        all_result.append(
            {
                "pixel_bbox": [
                    SIDE_BAR_WIDTH,
                    TITLE_BAR_HEIGHT,
                    SIDE_BAR_WIDTH + SESSION_LIST_WIDTH,
                    self.size_config.height,
                ],
                "content": "会话列表区域",
                "label": "会话列表区域",
                "source": "动态计算",
            }
        )
        all_result.append(
            {
                "pixel_bbox": [
                    self.MSG_TOP_X,
                    self.MSG_TOP_Y,
                    self.MSG_TOP_X + self.MSG_WIDTH,
                    self.MSG_TOP_Y + self.MSG_HEIGHT,
                ],
                "content": "消息区域",
                "label": "消息区域",
                "source": "动态计算",
            }
        )
        all_result.append(
            {
                "pixel_bbox": send_btn_bbox,
                "content": "发送按钮",
                "label": "发送按钮",
                "source": "动态计算",
            }
        )
        all_result.append(
            {
                "pixel_bbox": [
                    search_box_point[0] - 10,
                    search_box_point[1] - 10,
                    search_box_point[0] + 10,
                    search_box_point[1] + 10,
                ],
                "content": "搜索框",
                "label": "搜索框",
                "source": "动态计算",
            }
        )

        self.ICON_CONFIGS["search_icon"]["position"] = [
            search_box_point[0] - 10,
            search_box_point[1] - 10,
            search_box_point[0] + 10,
            search_box_point[1] + 10,
        ]
        self.ICON_CONFIGS["send_button"]["position"] = send_btn_bbox

        screenshot = self.image_processor.take_screenshot(
            region=[
                0,
                0,
                self.size_config.width,
                self.size_config.height,
            ],
        )
        self.SIDE_BAR_WIDTH = SIDE_BAR_WIDTH
        self.SESSION_LIST_WIDTH = SESSION_LIST_WIDTH
        self.TITLE_BAR_HEIGHT = TITLE_BAR_HEIGHT

        self.open_close_sidebar()
        # 先给他打开，然后从底部开始扫像素
        screenshot = self.image_processor.take_screenshot(
            region=[
                0,
                0,
                self.size_config.width,
                self.size_config.height,
            ],
        )
        # 读取图片
        # 获取像素数据
        pixels = screenshot.load()
        # Y从底部发送按钮相同位置开始，X从去掉侧边栏位置开始, 偏移50，防止遇到分割线
        startx = SIDE_BAR_WIDTH + SESSION_LIST_WIDTH + 50
        starty = get_center_point(send_btn_bbox)[1]
        for i in range(startx, self.size_config.width):
            if pixels[i, starty] != pixels[i - 1, starty]:
                self.ROOM_SIDE_BAR_WIDTH = self.size_config.width - i
                self.logger.info(f"侧边栏宽度: {self.ROOM_SIDE_BAR_WIDTH}")
                break
        self.open_close_sidebar(close=True)
        return True

    def init_split_sessions(self):
        """初始化分割的会话"""
        windows = pyautogui.getAllWindows()
        for window in windows:
            if "元宝" in window.title:
                self.logger.info("元宝窗口独立设置")
                self.weixin_windows[window.title] = {
                    "window": window,
                    "MSG_TOP_X": self.size_config.width,
                    "MSG_TOP_Y": self.MSG_TOP_Y,
                    "MSG_WIDTH": self.size_config.width,
                    "MSG_HEIGHT": self.MSG_HEIGHT,
                    "region": [
                        self.size_config.width,
                        self.MSG_TOP_Y,
                        self.size_config.width,
                        self.MSG_HEIGHT,
                    ],
                }
                window.size = (self.size_config.width, self.size_config.height)
                window.topleft = (self.size_config.width, 0)

    def init_pyq_window(self) -> bool:
        """初始化朋友圈窗口"""
        friend_window = self.open_friend_window()
        if friend_window:
            # 这里宽度是固定的无所谓，高度设置为和主窗口一样，方便处理
            friend_window.size = (10, self.size_config.height)
            friend_window.left = self.size_config.width
            friend_window.top = 0
            time.sleep(self.scroll_delay)
            human_like_mouse_move(
                friend_window.left + friend_window.width // 2,
                friend_window.top + friend_window.height // 2,
            )
            time.sleep(self.scroll_delay)
            pyautogui.scroll(-friend_window.height // 2)
            time.sleep(self.scroll_delay)
            # 这里就需要查找顶部的控件了，1. 移动到窗口然后向下滚动，把顶部的banner滚掉 2 查找title高度，取中点 3. 从左侧开始向右遍历 50%宽度 4. 找到三个控件
            screenshot = self.image_processor.take_screenshot(
                region=[
                    friend_window.left,
                    friend_window.top,
                    friend_window.width,
                    friend_window.height,
                ],
            )
            # 读取图片
            # 获取像素数据
            pixels = screenshot.load()
            # 从上到下扫描高度范围内，找到第一个变化的像素，就是标题栏的高度
            title_bar_height = 0
            for i in range(10, 100):
                if pixels[10, i] != pixels[10, i - 1]:
                    title_bar_height = i
                    break
            if title_bar_height > 0:
                self.logger.info(f"朋友圈窗口标题栏高度: {title_bar_height}")
            else:
                self.logger.error("朋友圈窗口标题栏高度未找到，请检查微信是否正常运行")
                return None
            # 参考主菜单查找的方式，这里还是采用间隔法吧？这里其实写死都可以？就怕分辨率导致不同？
            breakPoint = []
            breakPoint.clear()
            icons = []
            for i in range(10, friend_window.width // 3):
                if (
                    pixels[i, title_bar_height // 2]
                    != pixels[i - 1, title_bar_height // 2]
                ):
                    breakPoint.append(i)
                    if len(icons) == 0:
                        icons.append(i)
                    if len(breakPoint) > 1:
                        if breakPoint[-1] - breakPoint[-2] > 30:
                            # self.logger.info(f"间隔 {breakPoint[-1] - breakPoint[-2]}")
                            icons.append(breakPoint[-2])
                            icons.append(breakPoint[-1])
            icons.append(breakPoint[-1])
            # self.logger.info(icons)
            # 两两一组，目前先关心前面两个是聊天和联系人
            all_result = []

            # 这里可能会出现多个菜单，数量不确定，所以要复杂处理
            menu_labels = [
                MenuTypeEnum.FriendNotification.value,
                MenuTypeEnum.FriendSend.value,
                MenuTypeEnum.FrendRefresh.value,
            ]

            for idx, i in enumerate(range(0, len(icons), 2)):
                bbox = [
                    icons[i] + friend_window.left,
                    title_bar_height // 3,
                    icons[i + 1] + friend_window.left,
                    title_bar_height // 3 * 2,
                ]
                # 保存到 ICON_CONFIGS, 这里保存的位置其实已经计算好了，所以下面要重新偏移
                name = menu_labels[idx] if idx < len(menu_labels) else f"菜单{idx}"
                self.ICON_CONFIGS[name] = {
                    "name": name,
                    "color": None,
                    "position": bbox,
                }
                all_result.append(
                    {
                        "pixel_bbox": bbox,
                        "content": name,
                        "label": name,
                        "source": "动态计算",
                    }
                )
            self.image_processor.draw_boxes_on_screen(
                screenshot,
                all_result,
                start=(-friend_window.left, -friend_window.top),
                output_path="runtime_images/friend_window.png",
            )
            return True
        else:
            self.logger.error("朋友圈窗口未找到，请检查微信是否正常运行")
            return None

    def _is_wechat_foreground(self, reposition=True) -> bool:
        """检查微信主窗口是否在前台"""
        # TODO 重构
        windows = pyautogui.getAllWindows()
        for window in windows:
            if window.title == "预览":
                window.close()
        chat_window = pyautogui.getWindowsWithTitle("微信")[0]
        if chat_window:
            self._activate_window("微信")
            if reposition:
                chat_window.topleft = (0, 0)
            # 这里出现的问题，可能就是宽度有最小值，有可能会比最小值大
            chat_window.size = (self.size_config.width, self.size_config.height)
            if (
                chat_window.size.width < self.size_config.width
                or chat_window.size.height < self.size_config.height
            ):
                self.logger.warn("微信窗口大小不匹配，重新调整大小")
                return False
            else:
                self.logger.info("微信窗口大小匹配")
                self.size_config.width = chat_window.size.width
                self.size_config.height = chat_window.size.height
            return True
        else:
            self.logger.error("微信窗口未找到，请检查微信是否正常运行")
            return False

    def _activate_window(self, title: str = "微信"):
        """激活微信窗口"""
        try:
            window = pyautogui.getWindowsWithTitle(title)[0]
            window.activate()
            return True
        except Exception as e:
            if window:
                window.restore()
                return True
            self.logger.error(f"激活窗口时出错: {str(e)}")
            return False

    def get_window_region(self) -> Optional[Tuple[int, int, int, int]]:
        """获取指定窗口的区域"""
        if self.current_window:
            return self.current_window["region"]
        return None

    def get_message_region(self) -> Optional[Tuple[int, int, int, int]]:
        """获取消息区域"""
        if self.current_window:
            return [
                self.current_window.get("MSG_TOP_X"),
                self.current_window.get("MSG_TOP_Y"),
                self.current_window.get("MSG_WIDTH"),
                self.current_window.get("MSG_HEIGHT"),
            ]
        return None

    def switch_session(self, target: str) -> bool:
        """
        切换会话
        这里要区分切换会话和切换窗口，如果是分离的对话，那么直接切换，也可能是切换别的窗口
        """
        now = time.time()
        if self.last_switch_session_time and now - self.last_switch_session_time > 180:
            self.last_switch_session = None
            self.last_switch_session_time = None
        self.logger.info(f"切换会话: {target}")
        if target in self.weixin_windows:
            self.switch_window(target)
            return True
        else:
            # 添加逻辑，如果当前激活的窗口已经是了，就不必再重复激活，直接返回True即可。每次切换，记录最后切换的会话窗口
            # 这个激活窗口感觉有问题
            self.switch_window("微信")
            if self.last_switch_session == target:
                self.logger.info(f"已经切换到: {target}，直接返回True")
                return True
            # 切换对话步骤：1. 使用快捷键 ctrl + f，激活查询输入框 2. 使用复制剪贴操作，输入target 3. 回车确认聊天对象
            self.logger.info(f"使用快捷键切换到: {target}")
            time.sleep(self.action_delay)
            pyautogui.hotkey("ctrl", "f")
            time.sleep(self.action_delay)
            if not set_clipboard_text(target):
                return False
            time.sleep(self.action_delay)
            pyautogui.hotkey("ctrl", "v")
            self.logger.info(f"正在搜索联系人: {target}")
            # contact_info = {"display_name": target}
            time.sleep(self.action_delay)
            pyautogui.press("enter")
            time.sleep(self.switch_contact_delay)
            # 这里直接回车存在风险，不过如果出现网络搜索的情况，应该必须手动点，回车是无效的？
            # 这里通过判断交叉点的颜色
            color = self.image_processor.get_pixel_color(
                self.SIDE_BAR_WIDTH + self.SESSION_LIST_WIDTH + 10,
                self.TITLE_BAR_HEIGHT - 5,
            )
            if color == (255, 255, 255):
                self.logger.warn("回车后，搜索框还在，需要进一步处理")
                search_window = self.get_window(WindowTypeEnum.SearchContactWindow)
                time.sleep(self.window_show_delay)
                if search_window:
                    screenshot = self.image_processor.take_screenshot(
                        region=[
                            search_window.left,
                            search_window.top,
                            search_window.width,
                            search_window.height,
                        ],
                    )
                    # 对搜索框进行OCR，然后查找正确的切换位置，查找规则：
                    # 先查找标签 联系人，群聊，然后对这两个标签的位置进行判断，先取Y小的，然后直接找他附近最近的那个
                    # 标签和群名字相同的情况下，优先匹配的居然是标签？你他妈煞笔吧
                    # 算了简单点，如果找到了联系人或者群聊，直接下方向键选择？万一网络在前面怎么办？你没得
                    # 如果搜索结果在前，采用倒数选择也有问题啊
                    # 直接拦截微信的搜索网络请求可能是最佳选择
                    result = self.ocr_processor.process_image(image=screenshot)
                    self.image_processor.draw_boxes_on_screen(
                        screenshot,
                        result,
                        "runtime_images/search_contact_result.png",
                    )
                    # 对联系人和群聊先找出来，按照Y从小到达排序
                    labels = [r for r in result if r.get("label") in ["联系人", "群聊"]]
                    if labels:
                        labels.sort(key=lambda x: x.get("pixel_bbox")[1])
                        center_point = get_center_point(
                            labels[0].get("pixel_bbox"),
                            offset=(search_window.left, search_window.top),
                        )
                        pyautogui.click(
                            center_point[0] + self.search_contact_offset[0],
                            center_point[1] + self.search_contact_offset[1],
                        )
                        time.sleep(self.action_delay)
                        color = self.image_processor.get_pixel_color(
                            self.SIDE_BAR_WIDTH + self.SESSION_LIST_WIDTH + 10,
                            self.TITLE_BAR_HEIGHT - 5,
                        )
                        if color == (255, 255, 255):
                            self.logger.info("回车后，搜索框还在，需要进一步处理")
                            return False
                        else:
                            self.logger.info("回车后，搜索框消失，切换成功")
                            self.last_switch_session = target
                            self.last_switch_session_time = time.time()
                            return True
                    else:
                        self.logger.error("搜索结果中没有联系人或群聊")
                    try:
                        search_window.close()
                    except Exception as e:
                        self.logger.error(f"关闭搜索窗口时出错: {str(e)}")
                return False
            else:
                self.logger.info("回车消除了，默认切换成功了吧")
            self.last_switch_session = target
            self.last_switch_session_time = time.time()
            return True

    def switch_window(self, target: str) -> bool:
        """
        激活窗口
        这里要区分激活窗口和激活对话，如果是分离的对话，那么直接激活，也可能是激活别的窗口
        """
        self.logger.info("激活窗口")
        if target in self.weixin_windows:
            self.current_window = self.weixin_windows[target]
        else:
            self.current_window = self.weixin_windows["微信"]
        try:
            self.current_window["window"].activate()
            return True
        except Exception as e:
            self.current_window["window"].minimize()
            self.current_window["window"].restore()
            return True

    def long_press_menu(self, target: str, duration: int = 1) -> bool:
        """
        长按菜单
        """
        menu = self.ICON_CONFIGS.get(target)
        if not menu:
            self.logger.error("菜单不存在")
            return False
        self.last_switch_session = None
        self.last_switch_session_time = None
        center_point = get_center_point(menu.get("position"))
        human_like_mouse_move(target_x=center_point[0], target_y=center_point[1])
        pyautogui.mouseDown(button="left")
        time.sleep(duration)
        pyautogui.mouseUp(button="left")
        return True

    def switch_menu(self, target: str) -> bool:
        self.logger.info(f"切换菜单{target}")
        menu = self.ICON_CONFIGS.get(target)
        if not menu:
            self.logger.error("菜单不存在")
            return False

        self.last_switch_session = None
        self.last_switch_session_time = None
        center_point = get_center_point(menu.get("position"))
        human_like_mouse_move(target_x=center_point[0], target_y=center_point[1])
        pyautogui.click()
        return True

    def get_window(
        self, windowType: WindowTypeEnum, all: bool = False
    ) -> Optional[pyautogui.Window]:
        """
        获取不同的窗口，不同的窗口有不同的判断条件
        args:
            all: 是否获取全部窗口，默认False，只获取微信的窗口
        """
        windows = pyautogui.getAllWindows()
        # 这里保留全部符合的窗口
        filter_windows = []
        if all:
            filter_windows = windows
        else:
            for window in windows:
                # 对所有的窗口进行过滤，排除掉不可见的，尺寸为0的
                if window.visible and window.width > 0 and window.height > 0:
                    # 这一步要过滤一下非微信的窗口
                    class_name = win32gui.GetClassName(window._hWnd)
                    if class_name.startswith("Qt5"):
                        filter_windows.append(window)
                    else:
                        pass
                        # self.logger.info(f"窗口类名: {class_name}{window.title}")
        if windowType == WindowTypeEnum.MainWindow:
            for window in filter_windows:
                if window.title == "微信":
                    return window
        elif windowType == WindowTypeEnum.AddFriendWindow:
            # 添加好友的窗口，判断规则：标题是 通过朋友验证，同时窗口的位置，应该在主窗口的内部
            for window in filter_windows:
                if window.title == "通过朋友验证":
                    # 这个位置关系不能确定，是浮动的，可以在屏幕的任意位置，但是肯定是可见的，而且明显不会很小
                    return window
        elif windowType == WindowTypeEnum.InviteMemberWindow:
            for window in filter_windows:
                if window.title == "微信添加群成员":
                    # 这个位置关系不能确定，是浮动的，可以在屏幕的任意位置，但是肯定是可见的，而且明显不会很小
                    return window
        elif windowType == WindowTypeEnum.RemoveMemberWindow:
            for window in filter_windows:
                if window.title == "微信移出群成员":
                    # 这个位置关系不能确定，是浮动的，可以在屏幕的任意位置，但是肯定是可见的，而且明显不会很小
                    return window
        elif windowType == WindowTypeEnum.InviteConfirmWindow:
            for window in filter_windows:
                if window.title == "Weixin":
                    if (
                        window.left + window.width < self.size_config.width
                        and window.top + window.height < self.size_config.height
                    ):
                        return window
        elif windowType == WindowTypeEnum.InviteResonWindow:
            for window in filter_windows:
                if window.title == "Weixin":
                    if (
                        window.left + window.width < self.size_config.width
                        and window.top + window.height < self.size_config.height
                    ):
                        return window
        elif windowType == WindowTypeEnum.SearchHistoryWindow:
            for window in filter_windows:
                if window.title == "搜索聊天记录":
                    return window
        elif windowType == WindowTypeEnum.FriendWindow:
            for window in filter_windows:
                if window.title == "朋友圈":
                    return window
        elif windowType == WindowTypeEnum.PublicAnnouncementWindow:
            for window in filter_windows:
                if window.title.endswith("的群公告"):
                    return window
        elif windowType == WindowTypeEnum.RoomInputConfirmBox:
            for window in filter_windows:
                if window.title == "Weixin":
                    if (
                        window.left + window.width < self.size_config.width
                        and window.top + window.height < self.size_config.height
                    ):
                        return window
        elif windowType == WindowTypeEnum.MenuWindow:
            for window in filter_windows:
                if window.title == "Weixin":
                    if window.width < 300:
                        return window
        elif windowType == WindowTypeEnum.SearchContactWindow:
            for window in filter_windows:
                if window.title == "Weixin":
                    # 这里固定在左上角，所以要判断以下开始位置在左上角
                    if (
                        window.left < self.SIDE_BAR_WIDTH
                        and window.top < self.TITLE_BAR_HEIGHT
                    ):
                        return window
                    else:
                        pass
        return None

    def open_friend_window(self) -> Optional[pyautogui.Window]:
        """
        打开朋友圈窗口
        """
        self.switch_menu(MenuTypeEnum.Friend.value)
        time.sleep(self.scroll_delay)
        # 调用gerwindow方法检查是否存在，如果存在，需要把friend这个窗口移到边上去，防止覆盖
        friend_window = self.get_window(WindowTypeEnum.FriendWindow)
        if friend_window:
            return friend_window
        else:
            self.switch_menu(MenuTypeEnum.Friend.value)
            return None

    def open_friend_send_window(
        self, is_text: bool = False
    ) -> Optional[pyautogui.Window]:
        """
        打开朋友圈发送窗口
        """
        if is_text:
            self.long_press_menu(MenuTypeEnum.FriendSend.value, duration=2)
        else:
            self.switch_menu(MenuTypeEnum.FriendSend.value)
        time.sleep(self.scroll_delay)
        # 这里需要用到OCR了，使用OCR来判断指定的控件是否存在，如果存在就认为是打开了发送的窗口，如果不存在那么就是没打开
        # 稳定性堪忧
        friend_window = self.get_window(WindowTypeEnum.FriendWindow)
        if not friend_window:
            self.logger.error("朋友圈窗口未找到，请检查微信是否正常运行")
            return None
        if not is_text:
            return friend_window
        friend_window.activate()
        time.sleep(self.scroll_delay)
        screenshot = self.image_processor.take_screenshot(
            region=[
                friend_window.left,
                friend_window.top,
                friend_window.width,
                friend_window.height,
            ],
        )
        result = self.ocr_processor.process_image(image=screenshot)
        if result:
            # 这里只要确认打开就可以了，后面发送朋友圈才需要用到识别吧，毕竟
            find_count = 0
            for r in result:
                label = r.get("label")
                if label and label.startswith("这一刻的想法"):
                    find_count += 1
                elif label == "发表":
                    find_count += 1
                elif label == "取消":
                    find_count += 1
                elif label == "提醒谁看":
                    find_count += 1
                elif label == "谁可以看":
                    find_count += 1
                elif label == "公开":
                    find_count += 1
                elif label == "发表":
                    find_count += 1
            if find_count > 4:
                return friend_window
            else:
                self.logger.error("朋友圈发送窗口未找到，请检查微信是否正常运行")
                return None

    def close_all_windows(self):
        """
        关闭所有窗口
        """
        windows = pyautogui.getAllWindows()
        # 这里保留全部符合的窗口
        for window in windows:
            # 对所有的窗口进行过滤，排除掉不可见的，尺寸为0的
            if window.visible and window.width > 0 and window.height > 0:
                # 这一步要过滤一下非微信的窗口
                class_name = win32gui.GetClassName(window._hWnd)
                if class_name.startswith("Qt5"):
                    if window.title != "微信":
                        window.close()

    def open_close_sidebar(self, close: bool = False) -> bool:
        """
        打开或者关闭侧边栏，默认打开
        # 现在这里可以判断了，直接按照像素颜色是否是纯白色来匹配
        args:
            close: 关闭
        """
        color = self.image_processor.get_pixel_color(
            self.size_config.width - 20, self.size_config.height - 20
        )
        if color == (255, 255, 255):
            CLOSED = False
        else:
            CLOSED = True

        if close and CLOSED:
            return True
        elif not close and not CLOSED:
            return True
        else:
            x = self.SIDE_BAR_WIDTH + self.SESSION_LIST_WIDTH + 50
            y = self.ICON_CONFIGS.get("search_icon").get("position")[1]
            human_like_mouse_move(target_x=x, target_y=y)
            pyautogui.click()
            time.sleep(self.rpa_config.get("side_bar_delay", 3))
            return True

    def wait_for_window(
        self, window_type: WindowTypeEnum, all: bool = False, timeout: int = 5
    ) -> Optional[Any]:
        """
        轮询查找指定标题的窗口，直到出现或超时。

        Args:
            title (str): 窗口标题。
            timeout (int): 超时时间（秒）。

        Returns:
            Optional[Any]: 窗口对象或None。
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            window = self.get_window(window_type, all)
            if window:
                return window
            time.sleep(0.2)
        self.logger.warning(f"未在{timeout}秒内找到窗口: {window_type.value}")
        return None
