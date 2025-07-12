"""
微信消息数据结构模块。
定义各类微信消息的数据模型与辅助方法。
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional, Union

import xmltodict
from omni_bot_sdk.models import UserInfo

from .parser.util.common import decompress


class DownloadStatus:
    Unknown = -1
    Downloaded = 3
    NotDownloaded = 0


class MessageType:
    Unknown = -1
    Text = 1
    Text2 = 2
    Image = 3
    Audio = 34
    BusinessCard = 42
    Video = 43
    Emoji = 47
    Position = 48
    Voip = 50
    OpenIMBCard = 66
    System = 10000
    File = 25769803825
    FileWait = 317827579953
    LinkMessage = 21474836529
    LinkMessage2 = 292057776177
    Music = 12884901937
    LinkMessage4 = 4294967345
    LinkMessage5 = 326417514545
    LinkMessage6 = 17179869233
    RedEnvelope = 8594229559345
    Transfer = 8589934592049
    Quote = 244813135921
    MergedMessages = 81604378673
    Applet = 141733920817
    Applet2 = 154618822705
    WeChatVideo = 219043332145
    FavNote = 103079215153
    Pat = 266287972401
    PublicAnnouncement = 373662154801

    @classmethod
    def name(cls, type_):
        type_name_map = {
            cls.Unknown: "未知类型",
            cls.Text: "文本",
            cls.Image: "图片",
            cls.Video: "视频",
            cls.Audio: "语音",
            cls.Emoji: "表情包",
            cls.Voip: "音视频通话",
            cls.File: "文件",
            cls.FileWait: "文件",
            cls.Position: "位置分享",
            cls.LinkMessage: "分享链接",
            cls.LinkMessage2: "分享链接",
            cls.LinkMessage4: "分享链接",
            cls.LinkMessage5: "分享链接",
            cls.LinkMessage6: "分享链接",
            cls.RedEnvelope: "红包",
            cls.Transfer: "转账",
            cls.Quote: "引用消息",
            cls.MergedMessages: "合并转发的聊天记录",
            cls.Applet: "小程序",
            cls.Applet2: "小程序",
            cls.WeChatVideo: "视频号",
            cls.Music: "音乐分享",
            cls.FavNote: "收藏笔记",
            cls.BusinessCard: "个人/公众号名片",
            cls.OpenIMBCard: "企业微信名片",
            cls.System: "系统消息",
            cls.Pat: "拍一拍",
            cls.PublicAnnouncement: "群公告",
        }
        return type_name_map.get(type_, "未知类型")


@dataclass(slots=True)
class Message:
    # 基础字段 - 数据库映射字段
    local_id: Optional[int]  # 本地消息ID，主键
    server_id: Optional[int]  # 服务器消息ID
    local_type: Optional[int]  # 本地消息类型
    sort_seq: Optional[int]  # 排序序列号
    real_sender_id: Optional[int]  # 实际发送者ID>
    create_time: Optional[int]  # 消息创建时间戳
    status: Optional[int]  # 消息状态
    upload_status: Optional[int]  # 上传状态
    download_status: Optional[int]  # 下载状态
    server_seq: Optional[int]  # 服务器序列号
    origin_source: Optional[int]  # 消息来源
    source: Optional[Union[str, bytes]]  # 消息来源文本
    message_content: Optional[Union[str, bytes]]  # 消息内容
    compress_content: Optional[Union[str, bytes]]  # 压缩后的消息内容
    packed_info_data: Optional[bytes]  # 打包信息数据
    # WCDB_CT_message_content: Optional[int]  # 消息内容类型
    # WCDB_CT_source: Optional[int]  # 来源类型

    # 额外字段 - 运行时字段
    message_db_path: str  # 消息来源的数据库路径，在4.0版本，进行了分库分表设计，后续的name2id查询，都和数据库有关系，所以需要在聊天消息中保留一份
    room: Optional[Any]  # 群聊对象
    contact: Optional[Any]  # 联系人对象
    user_info: UserInfo  # 用户信息

    @property
    def create_datetime(self) -> datetime:
        """获取消息创建时间"""
        return (
            datetime.fromtimestamp(self.create_time)
            if self.create_time
            else datetime.now()
        )

    @property
    def str_time(self) -> str:
        """获取消息创建时间"""
        return datetime.fromtimestamp(self.create_time).strftime("%Y-%m-%d %H:%M:%S")

    @property
    def real_sender_name(self) -> str:
        """获取实际发送者名称"""
        return self.contact.display_name if self.contact else ""

    @property
    def is_self(self) -> bool:
        """判断消息是否来自自己"""
        if self.contact:
            return self.user_info.account == self.contact.username
        else:
            if (
                self.local_type == MessageType.System
                or self.local_type == MessageType.Pat
            ):
                # 这里直接拦截感觉不合适，比如邀请人进群，第三方的邀请会被拦截，是否需要放出来？
                print(f"没有联系人信息，默认是自己的消息: {self.type_name}")
                return True
            else:
                print(f"没有联系人信息，默认不是自己的消息: {self.type_name}")
                return False

    @property
    def is_at(self) -> bool:
        if not self.is_chatroom:
            return False
        try:
            wxid = self.user_info.account
            if not re.findall(
                rf"<atuserlist>[\s|\S]*({wxid})[\s|\S]*</atuserlist>",
                self.parsed_source,
            ):
                return False  # 不在 @ 清单里

            if re.findall(r"@(?:所有人|all|All)", self.parsed_content):
                return False  # 排除 @ 所有人
            return True
        except:
            return False

    @property
    def is_chatroom(self) -> bool:
        """判断是否为群聊消息"""
        return self.room is not None

    @property
    def parsed_source(self):
        """获取解析后的消息来源，使用缓存避免重复处理"""
        if not hasattr(self, "_parsed_source"):
            source = self.source
            if isinstance(source, bytes):
                source = decompress(source)
            self._parsed_source = source
        return self._parsed_source

    @property
    def parsed_content(self) -> Union[str, bytes]:
        """获取解析后的消息内容，使用缓存避免重复处理"""
        if not hasattr(self, "_parsed_content"):
            message_content = self.message_content
            if isinstance(message_content, bytes):
                message_content = decompress(message_content)
            if (
                self.room != None
                and isinstance(message_content, str)
                and not self.is_self
                and self.local_type != MessageType.Pat
                and self.local_type != MessageType.System
            ):
                # TODO 群聊文字消息格式：<wxid>:<content>, 开头必须是发送人的id+'：'+换行
                if message_content and message_content.startswith(
                    self.contact.username
                ):
                    message_content = (
                        message_content.strip(f"{self.contact.username}:")
                        .strip("\u2005")
                        .strip()
                    )
            self._parsed_content = message_content
        return self._parsed_content

    def to_json(self) -> dict:
        """将消息转换为JSON格式"""
        try:
            xml_dict = xmltodict.parse(self.message_content)
        except:
            xml_dict = {}
        return {
            "type": str(self.local_type),
            "status": self.status,
            "server_id": str(self.server_id),
            "real_sender_name": self.real_sender_name,
            "parsed_content": self.parsed_content,
            "is_chatroom": self.is_chatroom,
            "str_time": self.str_time,
            "room_nickname": self.room.display_name if self.room else "",
            "room_username": self.room.username if self.room else "",
            "xml_dict": xml_dict,
            "is_self": self.is_self,
        }

    @property
    def type_name(self) -> str:
        """获取消息类型的文字描述"""
        return MessageType.name(self.local_type)

    @property
    def target(self) -> str:
        if self.room:
            return self.room.display_name
        elif self.contact:
            return self.contact.display_name
        else:
            return ""

    def to_text(self) -> str:
        """将消息转换为文本格式"""
        try:
            return f"{self.local_type}\n{xmltodict.parse(self.message_content)}"
        except:
            print(self.message_content)
            return f"{self.local_type}\n{self.message_content}"

    def __lt__(self, other) -> bool:
        """用于消息排序"""
        return self.sort_seq < other.sort_seq

    @property
    def is_uploaded(self) -> bool:
        """检查消息是否已上传"""
        return self.upload_status is not None and self.upload_status > 0

    @property
    def is_downloaded(self) -> bool:
        """检查消息是否已下载"""
        return self.download_status is not None and self.download_status > 0


@dataclass(slots=True)
class FakeMessage:
    """
    自定义的消息类型，这个是双向的，和外部交互用这个类型
    用于在消息处理过程中，将消息转换为自定义的消息类型
    用户的消息，初步设计为 文本，图片，视频，文件，其他，表情等归属于文本
    其他消息类型，如语音，视频，文件，位置，名片，转账，红包，系统消息，撤回消息等，归属于其他
    不同的操作，感觉RPA也是可以操作的
    发送成功之后，会有一条真实的消息生成，可以作为客户端的反馈
    这里是一条简化的消息，只需要能够被RPA处理就可以了，微信不能批量操作，因此每条消息的附件是唯一的
    生成字段注释
    local_id: 本地消息ID
    local_type: 本地消息类型
    message_content: 消息内容
    username: 用户名, 如果是群聊，这个就是群
    nickname: 昵称
    at_list: 被@的人列表
    is_chatroom: 是否为群聊
    create_time: 消息创建时间
    quote_msg: 引用消息
    thumb: 缩略图
    image: 图片
    video: 视频
    file: 文件
    """

    local_id: int
    local_type: int
    message_content: str
    username: str
    nickname: str
    at_list: List[str]
    is_chatroom: bool
    create_time: int
    quote_msg: Optional[str] = None
    thumb: Optional[bytes] = None
    image: Optional[bytes] = None
    video: Optional[bytes] = None
    file: Optional[bytes] = None

    def from_message(self, message: Message) -> dict:
        return {
            "local_id": message.local_id,
            "local_type": message.local_type,
            "message_content": message.message_content,
            "username": message.username,
        }


@dataclass
class TextMessage(Message):
    # 文本消息
    content: str  # 文本内容，没有默认值，必须放在前面

    def to_text(self):
        return self.content

    def to_json(self) -> dict:
        data = super().to_json()
        data["text"] = self.content
        return data


@dataclass
class QuoteMessage(TextMessage):
    # 引用消息
    quote_message: Message

    def to_json(self) -> dict:
        data = super().to_json()
        if self.quote_message:
            data.update(
                {
                    "text": self.content,
                    "quote_server_id": f"{self.quote_message.server_id}",
                    "quote_type": self.quote_message.local_type,
                }
            )
            if self.quote_message.local_type == MessageType.Quote:
                # 防止递归引用
                data["quote_text"] = (
                    f"{self.quote_message.contact.display_name}: {self.quote_message.content}"
                )
            else:
                data["quote_text"] = (
                    f"{self.quote_message.contact.display_name}: {self.quote_message.to_text()}"
                )
        else:
            data.update({"text": self.content})
        return data

    def to_text(self):
        if self.quote_message.local_type == MessageType.Quote:
            # 防止递归引用
            return f"{self.content}\n引用：{self.quote_message.contact.display_name}: {self.quote_message.content}"
        else:
            return f"{self.content}\n引用：{self.quote_message.contact.display_name}: {self.quote_message.to_text()}"


@dataclass
class FileMessage(Message):
    # 文件消息
    path: str
    md5: str
    file_size: int
    file_name: str
    file_type: str

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "path": self.path,
                "file_name": self.file_name,
                "file_size": self.file_size,
                "file_type": self.file_type,
            }
        )
        return data

    def get_file_size(self, format_="MB"):
        # 定义转换因子
        units = {
            "B": 1,
            "KB": 1024,
            "MB": 1024**2,
            "GB": 1024**3,
        }

        # 将文件大小转换为指定格式
        if format_ in units:
            size_in_format = self.file_size / units[format_]
            return f"{size_in_format:.2f} {format_}"
        else:
            raise ValueError(f"Unsupported format: {format_}")

    def set_file_name(self, file_name=""):
        if file_name:
            self.file_name = file_name
            return True
        # 把时间戳转换为格式化时间
        time_struct = datetime.fromtimestamp(
            self.create_time
        )  # 首先把时间戳转换为结构化时间
        str_time = time_struct.strftime("%Y%m%d_%H%M%S")  # 把结构化时间转换为格式化时间
        str_time = f"{str_time}_{str(self.server_id)[:6]}"
        if self.is_self:
            str_time += "_1"
        else:
            str_time += "_0"
        self.file_name = str_time
        return True

    def to_text(self):
        return f"【文件】{self.file_name} {self.get_file_size()} {self.path} {self.file_type} {self.md5}"


@dataclass
class ImageMessage(FileMessage):
    # 图片消息
    thumb_path: str
    path: str

    def to_json(self) -> dict:
        data = super().to_json()
        data["path"] = self.path
        data["thumb_path"] = self.thumb_path
        return data

    def to_text(self):
        return f"【图片】"


@dataclass
class EmojiMessage(ImageMessage):
    # 表情包
    url: str
    thumb_url: str
    description: str

    def to_json(self) -> dict:
        data = super().to_json()
        data.update({"path": self.url, "desc": self.description})
        return data

    def to_text(self):
        return f"【表情包】 {self.description}"


@dataclass
class VideoMessage(FileMessage):
    # 视频消息
    thumb_path: str
    duration: int
    raw_md5: str

    def to_text(self):
        return "【视频】"

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "path": self.path,
                "thumb_path": self.thumb_path,
                "duration": self.duration,
            }
        )
        return data


@dataclass
class AudioMessage(FileMessage):
    # 语音消息
    duration: int
    audio_text: str

    def set_file_name(self):
        # 把时间戳转换为格式化时间
        time_struct = datetime.fromtimestamp(
            self.create_time
        )  # 首先把时间戳转换为结构化时间
        str_time = time_struct.strftime("%Y%m%d_%H%M%S")  # 把结构化时间转换为格式化时间
        str_time = f"{str_time}_{str(self.server_id)[:6]}"
        if self.is_self:
            str_time += "_1"
        else:
            str_time += "_0"
        self.file_name = str_time

    def get_file_name(self):
        return self.file_name

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "path": self.path,
                "voice_to_text": self.audio_text,
                "duration": self.duration,
            }
        )
        return data

    def to_text(self):
        # return f'{self.server_id}\n{self.type}\n{xmltodict.parse(self.message_content)}'
        return f"【语音】{self.audio_text}"


@dataclass
class LinkMessage(Message):
    # 链接消息
    href: str  # 跳转链接
    title: str  # 标题
    description: str  # 描述/音乐作者
    cover_path: str  # 本地封面路径
    cover_url: str  # 封面地址
    app_name: str  # 应用名
    app_icon: str  # 应用logo
    app_id: str  # app ip

    def to_text(self):
        return f"""【分享链接】
标题：{self.title}
描述：{self.description}
链接: {self.href}
应用：{self.app_name}
"""

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "url": self.href,
                "title": self.title,
                "description": self.description,
                "cover_url": self.cover_url,
                "app_logo": self.app_icon,
                "app_name": self.app_name,
            }
        )
        return data


@dataclass
class WeChatVideoMessage(Message):
    # 视频号消息
    url: str  # 下载地址
    publisher_nickname: str  # 视频发布者昵称
    publisher_avatar: str  # 视频发布者头像
    description: str  # 视频描述
    media_count: int  # 视频个数
    cover_path: str  # 封面本地路径
    cover_url: str  # 封面网址
    thumb_url: str  # 缩略图
    duration: int  # 视频时长，单位（秒）
    width: int  # 视频宽度
    height: int  # 视频高度

    def to_text(self):
        return f"""【视频号】
描述: {self.description}
发布者: {self.publisher_nickname}
"""

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "url": self.url,
                "title": self.description,
                "cover_url": self.cover_url,
                "duration": self.duration,
                "publisher_nickname": self.publisher_nickname,
                "publisher_avatar": self.publisher_avatar,
            }
        )
        return data


@dataclass
class MergedMessage(Message):
    # 合并转发的聊天记录
    title: str
    description: str
    messages: List[Message]  # 嵌套子消息
    level: int  # 嵌套层数

    def to_text(self):
        res = f"【合并转发的聊天记录】\n\n"
        for message in self.messages:
            res += f"{' ' * self.level * 4}- {message.parsed_content}\n"
        return res

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "title": self.title,
                "description": self.description,
                "messages": [msg.to_json() for msg in self.messages],
            }
        )
        return data


@dataclass
class VoipMessage(Message):
    # 音视频通话
    invite_type: int  # -1，1:语音通话，0:视频通话
    display_content: str  # 界面显示内容
    duration: int

    def to_text(self):
        return f"【音视频通话】\n{self.display_content}"

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "invite_type": self.invite_type,
                "display_content": self.display_content,
                "duration": self.duration,
            }
        )
        return data


@dataclass
class PositionMessage(Message):
    # 位置分享
    x: float  # 经度
    y: float  # 维度
    label: str  # 详细标签
    poiname: str  # 位置点标记名
    scale: float  # 缩放率

    def to_text(self):
        return f"""【位置分享】
                坐标: ({self.x},{self.y})
                名称: {self.poiname}
                标签: {self.label}
                """

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "x": self.x,  # 经度
                "y": self.y,  # 维度
                "label": self.label,  # 详细标签
                "poiname": self.poiname,  # 位置点标记名
                "scale": self.scale,  # 缩放率
            }
        )
        return data


@dataclass
class BusinessCardMessage(Message):
    # 名片消息
    is_open_im: bool  # 是否是企业微信
    username: str  # 名片的wxid
    nickname: str  # 名片昵称
    alias: str  # 名片微信号
    province: str  # 省份
    city: str  # 城市
    sign: str  # 签名
    sex: int  # 性别 0：未知，1：男，2：女
    small_head_url: str  # 头像
    big_head_url: str  # 头像原图
    open_im_desc: str  # 公司名
    open_im_desc_icon: str  # 公司logo

    def _sex_name(self):
        if self.sex == 0:
            return "未知"
        elif self.sex == 1:
            return "男"
        else:
            return "女"

    def to_text(self):
        if self.is_open_im:
            return f"""【名片】
公司: {self.open_im_desc}
昵称: {self.nickname}
性别: {self._sex_name()}
"""
        else:
            return f"""【名片】
微信号:{self.alias}
昵称: {self.nickname}
签名: {self.sign}
性别: {self._sex_name()}
地区: {self.province} {self.city}
"""

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "is_open_im": self.is_open_im,
                "big_head_url": self.big_head_url,  # 头像原图
                "small_head_url": self.small_head_url,  # 小头像
                "username": self.username,  # wxid
                "nickname": self.nickname,  # 昵称
                "alias": self.alias,  # 微信号
                "province": self.province,  # 省份
                "city": self.city,  # 城市
                "sex": self._sex_name(),  # int ：性别 0：未知，1：男，2：女
                "open_im_desc": self.open_im_desc,  # 公司名
                "open_im_desc_icon": self.open_im_desc_icon,  # 公司名前面的图标
            }
        )
        return data


@dataclass
class TransferMessage(Message):
    # 转账
    fee_desc: str  # 金额
    pay_memo: str  # 备注
    receiver_username: str  # 收款人
    pay_subtype: int  # 状态

    def display_content(self):
        text_info_map = {
            1: "发起转账",
            3: "已收款",
            4: "已退还",
            5: "非实时转账收款",
            7: "发起非实时转账",
            8: "未知",
            9: "未知",
        }
        return text_info_map.get(self.pay_subtype, "未知")

    def to_text(self):
        return f"""【{self.display_content()}】:{self.fee_desc}
备注: {self.pay_memo}
"""

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "text": self.display_content(),  # 显示文本
                "pay_subtype": self.pay_subtype,  # 当前状态
                "pay_memo": self.pay_memo,  # 备注
                "fee_desc": self.fee_desc,  # 金额
            }
        )
        return data


@dataclass
class RedEnvelopeMessage(Message):
    # 红包
    icon_url: str  # 红包logo
    title: str
    inner_type: int

    def to_text(self):
        return f"""【红包】: {self.title}"""

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "text": self.title,  # 显示文本
                "inner_type": self.inner_type,  # 当前状态
            }
        )
        return data


@dataclass
class FavNoteMessage(Message):
    # 收藏笔记
    title: str
    description: str
    record_item: str

    def to_text(self):
        return f"""【笔记】
{self.description}
{self.record_item}
"""

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "text": self.title,  # 显示文本
                "description": self.description,  # 内容
                "record_item": self.record_item,
            }
        )
        return data


@dataclass
class PatMessage(Message):
    # 拍一拍
    title: str
    from_username: str
    chat_username: str
    patted_username: str
    template: str

    def to_text(self):
        return self.title

    def to_json(self) -> dict:
        data = super().to_json()
        data.update(
            {
                "type": MessageType.System,
                "text": self.title,  # 显示文本
            }
        )
        return data
