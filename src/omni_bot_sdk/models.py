import hashlib
import json
from dataclasses import dataclass
from typing import Dict, List

from omni_bot_sdk.weixin.parser.util.protocbuf.roomdata_pb2 import ChatRoomData


@dataclass
class UserInfo:
    """
    微信用户信息模型。
    用于存储和传递与微信用户相关的所有关键信息。
    """

    pid: str  # 进程ID
    version: str  # 微信版本
    alias: str  # 微信别名
    account: str  # 微信账号
    nickname: str  # 昵称
    phone: str  # 手机号
    data_dir: str  # 数据目录
    dbkey: str  # 数据库密钥
    raw_keys: Dict[str, str]  # 原始密钥集合
    dat_key: str  # dat文件密钥
    dat_xor_key: int  # dat文件异或密钥
    avatar_url: str  # 头像URL

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "UserInfo":
        """
        从字典数据创建UserInfo对象。
        """
        return cls(
            pid=data["pid"],
            version=data["version"],
            alias=data["alias"],
            account=data["account"],
            nickname=data["nickname"],
            phone=data["phone"],
            data_dir=data["data_dir"],
            dbkey=data.get("dbkey", ""),
            raw_keys=data.get("raw_keys", {}),
            dat_key=data.get("dat_key", ""),
            dat_xor_key=data.get("dat_xor_key", -1),
            avatar_url=data.get("avatar_url", ""),
        )

    def to_dict(self) -> Dict[str, str]:
        """
        转换为字典格式，便于序列化或存储。
        """
        return {
            "pid": self.pid,
            "version": self.version,
            "alias": self.alias,
            "account": self.account,
            "nickname": self.nickname,
            "phone": self.phone,
            "data_dir": self.data_dir,
            "dbkey": self.dbkey,
            "raw_keys": self.raw_keys,
            "dat_key": self.dat_key,
            "dat_xor_key": self.dat_xor_key,
            "avatar_url": self.avatar_url,
        }


@dataclass
class Contact:
    """
    联系人信息模型。
    用于描述微信联系人（包括好友和群成员）的详细属性。
    """

    id: int  # 数据库主键
    username: str  # 微信唯一标识
    local_type: int  # 本地类型
    alias: str  # 别名
    encrypt_username: str  # 加密用户名
    flag: int  # 标志位
    delete_flag: int  # 删除标志
    verify_flag: int  # 验证标志
    room_remark: str  # 群备注
    remark: str  # 备注
    remark_quan_pin: str  # 备注全拼
    remark_pin_yin_initial: str  # 备注拼音首字母
    nick_name: str  # 昵称
    pin_yin_initial: str  # 昵称拼音首字母
    quan_pin: str  # 昵称全拼
    big_head_url: str  # 大头像URL
    small_head_url: str  # 小头像URL
    head_img_md5: str  # 头像MD5
    chat_room_notify: int  # 群通知
    is_in_chat_room: int  # 是否在群聊中
    description: str  # 描述
    extra_buffer: bytes  # 额外缓冲区
    chat_room_type: int  # 群类型

    @classmethod
    def from_db_row(cls, row: tuple) -> "Contact":
        """
        从数据库行数据创建Contact对象。
        """
        return cls(
            id=row[0],
            username=row[1],
            local_type=row[2],
            alias=row[3],
            encrypt_username=row[4],
            flag=row[5],
            delete_flag=row[6],
            verify_flag=row[7],
            remark=row[8],
            remark_quan_pin=row[9],
            remark_pin_yin_initial=row[10],
            nick_name=row[11],
            pin_yin_initial=row[12],
            quan_pin=row[13],
            big_head_url=row[14],
            small_head_url=row[15],
            head_img_md5=row[16],
            chat_room_notify=row[17],
            is_in_chat_room=row[18],
            description=row[19],
            extra_buffer=row[20],
            chat_room_type=row[21],
            room_remark="",
        )

    @property
    def display_name(self) -> str:
        """
        获取联系人显示名称。
        优先级：备注 > 群备注 > 昵称 > 用户名。
        """
        if self.remark:
            return self.remark
        elif self.room_remark:
            return self.room_remark
        elif self.nick_name:
            return self.nick_name
        return self.username

    @property
    def is_chatroom(self) -> bool:
        """
        判断该联系人是否为群聊。
        """
        return self.username.endswith("@chatroom")

    def to_json(self) -> str:
        """
        转换为JSON字符串，自动过滤不可序列化的bytes属性。
        """
        return json.dumps(
            self,
            default=lambda o: {
                k: v for k, v in o.__dict__.items() if not isinstance(v, bytes)
            },
            ensure_ascii=False,
        )


@dataclass
class ChatRoom:
    """
    群聊信息模型。
    用于描述微信群聊的基本属性和成员解析。
    """

    id: int  # 数据库主键
    username: str  # 群聊唯一标识
    owner: str  # 群主用户名
    ext_buffer: bytes  # 扩展缓冲区（含成员信息）
    username_md5: str  # 群聊用户名MD5

    @classmethod
    def from_db_row(cls, row: tuple) -> "ChatRoom":
        """
        从数据库行数据创建ChatRoom对象。
        """
        username = row[1]
        username_md5 = hashlib.md5(username.encode()).hexdigest()
        return cls(
            id=row[0],
            username=username,
            owner=row[2],
            ext_buffer=row[3],
            username_md5=username_md5,
        )

    @property
    def parsed_member_list(self) -> List[str]:
        """
        解析群聊成员列表。
        通过解析ext_buffer中的protobuf数据，提取所有成员的wxID。
        结果缓存至实例属性，避免重复解析。
        """
        if not hasattr(self, "_parsed_member_list"):
            ext_buffer = self.ext_buffer
            if isinstance(ext_buffer, bytes):
                parsechatroom = ChatRoomData()
                parsechatroom.ParseFromString(ext_buffer)
                self._parsed_member_list = [
                    member.wxID for member in parsechatroom.members
                ]

        return self._parsed_member_list


@dataclass
class FMessage:
    """
    好友请求消息模型（FMessageTable）。
    用于描述微信好友请求相关的所有字段。
    """

    user_name: str  # 用户名
    type: int  # 消息类型
    timestamp: int  # 时间戳
    encrypt_user_name: str  # 加密用户名
    content: str  # 消息内容
    is_sender: int  # 是否为发送方
    ticket: str  # 验证票据
    scene: int  # 场景值
    # fmessage_detail_buf: str  # 预留字段

    @classmethod
    def from_db_row(cls, row: tuple) -> "FMessage":
        """
        从数据库行数据创建FMessage对象。
        """
        return cls(
            user_name=row[0],
            type=row[1],
            timestamp=row[2],
            encrypt_user_name=row[3],
            content=row[4],
            is_sender=row[5],
            ticket=row[6],
            scene=row[7],
            # fmessage_detail_buf=row[8],
        )

    def to_dict(self) -> Dict[str, str]:
        """
        转换为字典格式，便于序列化或存储。
        """
        return {
            "user_name": self.user_name,
            "type": self.type,
            "timestamp": self.timestamp,
            "encrypt_user_name": self.encrypt_user_name,
            "content": self.content,
            "is_sender": self.is_sender,
            "ticket": self.ticket,
            "scene": self.scene,
            # "fmessage_detail_buf": self.fmessage_detail_buf,
        }
