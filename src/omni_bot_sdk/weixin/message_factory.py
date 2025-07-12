"""
微信消息工厂模块。
负责微信消息的解析、构建与分发。
"""

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional, Union

import xmltodict
import zstandard as zstd
from google.protobuf.json_format import MessageToDict
from omni_bot_sdk.models import UserInfo

from .message_classes import *
from .parser.audio_parser import parser_audio
from .parser.emoji_parser import parser_emoji
from .parser.file_parser import parse_video
from .parser.link_parser import (
    parser_applet,
    parser_business,
    parser_favorite_note,
    parser_file,
    parser_link,
    parser_merged_messages,
    parser_pat,
    parser_position,
    parser_red_envelop,
    parser_reply,
    parser_transfer,
    parser_voip,
    parser_wechat_video,
)
from .parser.util.common import decompress, get_md5_from_xml
from .parser.util.protocbuf import (
    packed_info_data_img2_pb2,
    packed_info_data_img_pb2,
    packed_info_data_merged_pb2,
    packed_info_data_pb2,
)


# 定义抽象工厂基类
class MessageFactory(ABC):
    """
    消息工厂抽象基类。
    定义了创建消息实例的接口。
    """

    @abstractmethod
    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        """
        创建消息实例
        :param message: 消息数据
        :param db: 数据库对象
        :param contact: 联系人对象字典
        :param room: 群聊对象字典
        :return: 消息实例
        """
        pass


class UnknownMessageFactory(MessageFactory):
    """
    未知消息工厂。
    处理无法识别的消息类型。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = Message(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            user_info=user_info,
        )
        return msg


class TextMessageFactory(MessageFactory):
    """
    文本消息工厂。
    处理文本消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = TextMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            content=message[12],
            user_info=user_info,
        )
        return msg


class ImageMessageFactory(MessageFactory):
    """
    图片消息工厂。
    处理图片消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        filename = ""
        try:
            # 2025年3月微信4.0.3正式版修改了img命名方式才有了这个东西
            packed_info_data_proto = packed_info_data_img2_pb2.PackedInfoDataImg2()
            packed_info_data_proto.ParseFromString(message[14])
            # 转换为 JSON 格式
            packed_info_data = MessageToDict(packed_info_data_proto)
            image_info = packed_info_data.get("imageInfo", {})
            width = image_info.get("width", 0)
            height = image_info.get("height", 0)
            filename = image_info.get("filename", "").strip().strip('"').strip()
        except:
            pass
        if not filename:
            try:
                # 2025年3月微信测试版修改了img命名方式才有了这个东西
                packed_info_data_proto = packed_info_data_img_pb2.PackedInfoDataImg()
                packed_info_data_proto.ParseFromString(message[14])
                # 转换为 JSON 格式
                packed_info_data = MessageToDict(packed_info_data_proto)
                filename = (
                    packed_info_data.get("filename", "").strip().strip('"').strip()
                )
            except:
                pass
        msg = ImageMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            md5="",
            path="",
            thumb_path="",
            file_size=0,
            file_name=filename,
            file_type="png",
            user_info=user_info,
        )
        path = db.get_image(
            xml_content=msg.parsed_content,
            message=msg,
            up_dir="",
            thumb=False,
            sender_wxid=msg.room.username if msg.is_chatroom else msg.contact.username,
        )
        msg.path = path
        msg.thumb_path = db.get_image(
            xml_content=msg.parsed_content,
            message=msg,
            up_dir="",
            thumb=True,
            sender_wxid=msg.room.username if msg.is_chatroom else msg.contact.username,
        )
        return msg


class AudioMessageFactory(MessageFactory):
    """
    音频消息工厂。
    处理音频消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = AudioMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            md5="",
            path="",
            file_size=0,
            file_name="",
            file_type="mp3",
            audio_text="",
            duration=0,
            user_info=user_info,
        )
        audio_dic = parser_audio(msg.parsed_content)
        audio_length = audio_dic.get("audio_length", 0)
        audio_text = audio_dic.get("audio_text", "")
        if not audio_text:
            packed_info_data_proto = packed_info_data_pb2.PackedInfoData()
            packed_info_data_proto.ParseFromString(message[14])
            # 转换为 JSON 格式
            packed_info_data = MessageToDict(packed_info_data_proto)
            audio_text = packed_info_data.get("info", {}).get("audioTxt", "")
        if not audio_text:
            audio_text = ""
            print(f"音频消息没有音频文字，需要延迟处理一下")
            # TODO 语音转文字的逻辑有点不好处理，这个文字一定是在切换到窗口后再触发的，这里可以先看看语音文件的转换处理？
            # audio_text = db.get_audio_text(message[1])
        msg.audio_text = audio_text
        msg.duration = audio_length
        msg.set_file_name()
        return msg


class VideoMessageFactory(MessageFactory):
    """
    视频消息工厂。
    处理视频消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):

        filename = ""
        try:
            # 2025年3月微信4.0.3正式版修改了img命名方式才有了这个东西
            packed_info_data_proto = packed_info_data_img2_pb2.PackedInfoDataImg2()
            packed_info_data_proto.ParseFromString(message[14])
            # 转换为 JSON 格式
            packed_info_data = MessageToDict(packed_info_data_proto)
            image_info = packed_info_data.get("videoInfo", {})
            width = image_info.get("width", 0)
            height = image_info.get("height", 0)
            filename = image_info.get("filename", "").strip().strip('"').strip()
        except:
            pass
        msg = VideoMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            md5="",
            path="",
            file_size=0,
            file_name=filename,
            file_type="mp4",
            thumb_path="",
            duration=0,
            raw_md5="",
            user_info=user_info,
        )
        video_dic = parse_video(msg.parsed_content)
        msg.duration = video_dic.get("length", 0)
        msg.file_size = video_dic.get("size", 0)
        msg.md5 = video_dic.get("md5", "")
        msg.raw_md5 = video_dic.get("rawmd5", "")
        month = msg.str_time[:7]  # 2025-01
        if filename:
            # 微信4.0.3正式版增加
            video_dir = os.path.join(db.user_info.data_dir, "msg", "video", month)
            video_path = os.path.join(video_dir, f"{filename}_raw.mp4")
            if os.path.exists(video_path):
                msg.path = video_path
                msg.thumb_path = os.path.join(video_dir, f"{filename}.jpg")
            else:
                msg.path = os.path.join(video_dir, f"{filename}.mp4")
                msg.thumb_path = os.path.join(video_dir, f"{filename}.jpg")
        else:
            msg.path = db.get_video(msg.raw_md5, False)
            msg.thumb_path = db.get_video(msg.raw_md5, True)
            if not msg.path:
                msg.path = db.get_video(msg.md5, False)
                msg.thumb_path = db.get_video(msg.md5, True)
            # logger.error(f'{msg.path} {msg.thumb_path}')
        return msg


class EmojiMessageFactory(MessageFactory):
    """
    表情消息工厂。
    处理表情消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = EmojiMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            md5="",
            path="",
            thumb_path="",
            file_size=0,
            file_name="",
            file_type="png",
            url="",
            thumb_url="",
            description="",
            user_info=user_info,
        )
        emoji_info = parser_emoji(msg.parsed_content)
        if not emoji_info.get("url"):
            msg.url = db.get_emoji_url(emoji_info.get("md5"))
        else:
            msg.url = emoji_info.get("url")
        msg.md5 = emoji_info.get("md5", "")
        msg.description = emoji_info.get("desc")
        return msg


class LinkMessageFactory(MessageFactory):
    """
    链接消息工厂。
    处理链接消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = LinkMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            href="",
            title="",
            description="",
            cover_path="",
            cover_url="",
            app_name="",
            app_icon="",
            app_id="",
            user_info=user_info,
        )
        if message[2] in {
            MessageType.LinkMessage,
            MessageType.LinkMessage2,
            MessageType.Music,
            MessageType.LinkMessage4,
            MessageType.LinkMessage5,
            MessageType.LinkMessage6,
        }:
            info = parser_link(msg.parsed_content)
            msg.title = info.get("title", "")
            msg.href = info.get("url", "")
            msg.app_name = info.get("appname", "")
            msg.app_id = info.get("appid", "")
            msg.description = info.get("desc", "")
            msg.cover_url = info.get("cover_url", "")
            if message[2] in {MessageType.Music}:
                msg.type = MessageType.Music
            if not msg.app_name:
                source_username = info.get("sourceusername")
                if source_username:
                    contact = db.get_contact_by_username(source_username)
                    if contact:
                        msg.app_name = contact.display_name
                        msg.app_icon = contact.small_head_url
                    msg.app_id = source_username

        elif message[2] == MessageType.Applet or message[2] == MessageType.Applet2:
            info = parser_applet(msg.parsed_content)
            msg.type = MessageType.Applet
            msg.title = info.get("title", "")
            msg.href = info.get("url", "")
            msg.app_name = info.get("appname", "")
            msg.app_id = info.get("appid", "")
            msg.description = info.get("desc", "")
            msg.app_icon = info.get("app_icon", "")
            msg.cover_url = info.get("cover_url", "")
        return msg


class BusinessCardMessageFactory(MessageFactory):
    """
    名片消息工厂。
    处理名片消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = BusinessCardMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            is_open_im=message[2] == MessageType.OpenIMBCard,
            username="",
            nickname="",
            alias="",
            province="",
            city="",
            sign="",
            sex=0,
            small_head_url="",
            big_head_url="",
            open_im_desc="",
            open_im_desc_icon="",
            user_info=user_info,
        )
        info = parser_business(msg.parsed_content)
        msg.username = info.get("username", "")
        msg.nickname = info.get("nickname", "")
        msg.alias = info.get("alias", "")
        msg.small_head_url = info.get("smallheadimgurl", "")
        msg.big_head_url = info.get("bigheadimgurl", "")
        msg.sex = info.get("sex", 0)
        msg.sign = info.get("sign", "")
        msg.province = info.get("province", "")
        msg.city = info.get("city", "")
        msg.is_open_im = msg.local_type == MessageType.OpenIMBCard
        msg.open_im_desc = info.get("openimdescicon", "")
        msg.open_im_desc_icon = info.get("openimdesc", "")
        return msg


class VoipMessageFactory(MessageFactory):
    """
    语音消息工厂。
    处理语音消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = VoipMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            invite_type=0,
            display_content="",
            duration=0,
            user_info=user_info,
        )
        info = parser_voip(msg.parsed_content)
        msg.invite_type = info.get("invite_type", 0)
        msg.display_content = info.get("display_content", "")
        msg.duration = info.get("duration", 0)
        return msg


class MergedMessageFactory(MessageFactory):
    """
    合并转发消息工厂。
    处理合并转发消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        # TODO 目前实现比较混乱
        """
        合并转发的聊天记录
        - 文件路径：
          - msg/attach/9e20f478899dc29eb19741386f9343c8/2025-03/Rec/409af365664e0c0d/F/5/xxx.pdf
        - 图片路径：
          - msg/attach/9e20f478899dc29eb19741386f9343c8/2025-03/Rec/409af365664e0c0d/Img/5
        - 视频路径：
          - msg/attach/9e20f478899dc29eb19741386f9343c8/2025-03/Rec/409af365664e0c0d/V/5.mp4
        9e20f478899dc29eb19741386f9343c8是wxid的md5加密，409af365664e0c0d是packed_info_data_proto字段里的dir3
        文件夹最后的5代表的该文件是合并转发的聊天记录第5条消息，如果存在嵌套的合并转发的聊天记录，则依次递归的添加上一层的文件名后缀，例如：合并转发的聊天记录有两层
        0：文件（文件夹名为0）
        1：图片 （文件名为1）
        2：合并转发的聊天记录
            0：文件（文件夹名为2_0）
            1：图片（文件名为2_1）
            2：视频（文件名为2_2.mp4）
        :param message:
        :param username:
        :param manager:
        :return:
        """
        msg = MergedMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            title="",
            description="",
            messages=[],
            level=0,
            user_info=user_info,
        )
        info = parser_merged_messages(
            user_info, msg.parsed_content, "", msg.contact.username, message[5]
        )
        packed_info_data_proto = packed_info_data_merged_pb2.PackedInfoData()
        packed_info_data_proto.ParseFromString(message[14])
        # 转换为 JSON 格式
        packed_info_data = MessageToDict(packed_info_data_proto)
        dir0 = packed_info_data.get("info", {}).get("dir", "")
        month = msg.str_time[:7]  # 2025-03
        rec_dir = os.path.join(
            user_info.data_dir,
            "msg",
            "attach",
            hashlib.md5(msg.contact.username.encode("utf-8")).hexdigest(),
            month,
            "Rec",
        )
        if not dir0 and os.path.exists(rec_dir):
            for file in os.listdir(rec_dir):
                if file.startswith(f"{msg.local_id}_"):
                    dir0 = file
        msg.title = info.get("title", "")
        msg.description = info.get("desc", "")
        msg.messages = info.get("messages", [])

        def parser_merged(merged_messages, level):
            for index, inner_msg in enumerate(merged_messages):
                wxid_md5 = hashlib.md5(msg.contact.username.encode("utf-8")).hexdigest()
                inner_msg.room = msg.room
                if inner_msg.local_type == MessageType.Image:
                    if dir0:
                        inner_msg.path = os.path.join(
                            "msg",
                            "attach",
                            wxid_md5,
                            month,
                            "Rec",
                            dir0,
                            "Img",
                            f"{level}{'_' if level else ''}{index}",
                        )
                        inner_msg.thumb_path = os.path.join(
                            "msg",
                            "attach",
                            wxid_md5,
                            month,
                            "Rec",
                            dir0,
                            "Img",
                            f"{level}{'_' if level else ''}{index}_t",
                        )
                    else:
                        path = db.get_image(
                            xml_content="",
                            md5=inner_msg.md5,
                            message=inner_msg,
                            up_dir="",
                            thumb=False,
                            sender_wxid=msg.contact.username,
                        )
                        inner_msg.path = path
                        inner_msg.thumb_path = db.get_image(
                            xml_content="",
                            md5=inner_msg.md5,
                            message=inner_msg,
                            up_dir="",
                            thumb=True,
                            sender_wxid=msg.contact.username,
                        )
                elif inner_msg.local_type == MessageType.Video:
                    if dir0:
                        inner_msg.path = os.path.join(
                            "msg",
                            "attach",
                            wxid_md5,
                            month,
                            "Rec",
                            dir0,
                            "V",
                            f"{level}{'_' if level else ''}{index}.mp4",
                        )
                        inner_msg.thumb_path = os.path.join(
                            "msg",
                            "attach",
                            wxid_md5,
                            month,
                            "Rec",
                            dir0,
                            "Img",
                            f"{level}{'_' if level else ''}{index}_t",
                        )
                    else:
                        inner_msg.path = db.get_video(md5=inner_msg.md5, thumb=False)
                        inner_msg.thumb_path = db.get_video(
                            md5=inner_msg.md5, thumb=True
                        )
                elif inner_msg.local_type == MessageType.File:
                    if dir0:
                        inner_msg.path = os.path.join(
                            "msg",
                            "attach",
                            wxid_md5,
                            month,
                            "Rec",
                            dir0,
                            "F",
                            f"{level}{'_' if level else ''}{index}",
                            inner_msg.file_name,
                        )
                    else:
                        inner_msg.path = db.get_file(inner_msg.md5)
                elif inner_msg.local_type == MessageType.MergedMessages:
                    parser_merged(
                        inner_msg.messages,
                        f"{index}" if not level else f"{level}_{index}",
                    )

        parser_merged(msg.messages, "")
        return msg


class WeChatVideoMessageFactory(MessageFactory):
    """
    微信视频消息工厂。
    处理微信视频消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = WeChatVideoMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            url="",
            publisher_nickname="",
            publisher_avatar="",
            description="",
            media_count=1,
            cover_url="",
            thumb_url="",
            cover_path="",
            width=0,
            height=0,
            duration=0,
            user_info=user_info,
        )
        info = parser_wechat_video(msg.parsed_content)
        msg.publisher_nickname = info.get("sourcedisplayname", "")
        msg.publisher_avatar = info.get("weappiconurl", "")
        msg.description = info.get("title", "")
        msg.cover_url = info.get("cover", "")
        return msg


class PositionMessageFactory(MessageFactory):
    """
    位置消息工厂。
    处理位置消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = PositionMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            x=0,
            y=0,
            poiname="",
            label="",
            scale=0,
            user_info=user_info,
        )
        info = parser_position(msg.parsed_content)
        msg.x = eval(info.get("x", ""))
        msg.y = eval(info.get("y", ""))
        msg.poiname = info.get("poiname", "")
        msg.label = info.get("label", "")
        msg.scale = eval(info.get("scale", ""))
        return msg


class QuoteMessageFactory(MessageFactory):
    """
    引用消息工厂。
    处理引用消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = QuoteMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            content="",
            quote_message=None,
            user_info=user_info,
        )
        info = parser_reply(msg.parsed_content)
        # 引用的消息，肯定在同一个db
        quote_message = db.get_message_by_server_id(
            info.get("svrid", ""),
            msg.message_db_path,
            room.username if room else contact.username,
        )
        if quote_message:
            contact2 = db.get_contact_by_sender_id(
                quote_message[4], msg.message_db_path
            )
            msg.quote_message = FACTORY_REGISTRY[quote_message[2]].create(
                quote_message, user_info, db, contact2, room
            )
        else:
            print(f"quote_message is None, {msg.parsed_content}")
            msg.quote_message = None
        msg.content = info.get("text", "")
        return msg


class SystemMessageFactory(MessageFactory):
    """
    系统消息工厂。
    处理系统消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = TextMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            content="",
            user_info=user_info,
        )
        # TODO 解析更多系统消息，可能是来自群的消息，要去掉群的开头再进行解析xml
        if isinstance(message[12], bytes):
            message_content = decompress(message[12])
            try:
                message_content = message_content.split("@chatroom:")[1].strip()
                dic = xmltodict.parse(message_content)
                # 序列化成字符串
                message_content = json.dumps(dic, ensure_ascii=False)
            except:
                pass
        else:
            message_content = message[12]
        msg.content = message_content
        return msg


class TransferMessageFactory(MessageFactory):
    """
    转账消息工厂。
    处理转账消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = TransferMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            pay_subtype=0,
            fee_desc="",
            receiver_username="",
            pay_memo="",
            user_info=user_info,
        )
        info = parser_transfer(msg.parsed_content)
        msg.pay_subtype = info.get("pay_subtype", 0)
        msg.fee_desc = info.get("fee_desc", "")
        msg.receiver_username = info.get("receiver_username", "")
        msg.pay_memo = info.get("pay_memo", "")
        return msg


class RedEnvelopeMessageFactory(MessageFactory):
    """
    红包消息工厂。
    处理红包消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = RedEnvelopeMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            title="",
            icon_url="",
            inner_type=0,
            user_info=user_info,
        )
        info = parser_red_envelop(msg.parsed_content)
        msg.title = info.get("title", "")
        msg.icon_url = info.get("icon_url", "")
        msg.inner_type = info.get("inner_type", 0)
        return msg


class FileMessageFactory(MessageFactory):
    """
    文件消息工厂。
    处理文件消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = FileMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            path="",
            md5="",
            file_type="",
            file_name="",
            file_size="",
            user_info=user_info,
        )
        info = parser_file(msg.parsed_content)
        md5 = info.get("md5", "")
        filename = info.get("file_name", "")
        if not filename:
            try:
                packed_info_data_proto = packed_info_data_img2_pb2.PackedInfoDataImg2()
                packed_info_data_proto.ParseFromString(message[14])
                packed_info_data = MessageToDict(packed_info_data_proto)
                image_info = packed_info_data.get("fileInfo", {})
                file_info = image_info.get("fileInfo", {})
                filename = file_info.get("filename", "").strip()
            except:
                pass

        if filename:
            month = msg.str_time[:7]  # 2025-01
            file_dir = os.path.join("msg", "file", month)
            file_path = os.path.join(file_dir, f"{filename}")
        else:
            file_path = db.get_file(md5)
        msg.path = os.path.join(db.user_info.data_dir, file_path)
        msg.file_name = filename
        msg.file_size = info.get("file_size", 0)
        msg.file_type = info.get("file_type", "")
        msg.md5 = md5
        return msg


class FavNoteMessageFactory(MessageFactory):
    """
    收藏笔记消息工厂。
    处理收藏笔记消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = FavNoteMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            title="",
            description="",
            record_item="",
            user_info=user_info,
        )
        info = parser_favorite_note(msg.parsed_content)
        msg.title = info.get("title", "")
        msg.description = info.get("desc", "")
        msg.record_item = info.get("recorditem", "")
        return msg


class PatMessageFactory(MessageFactory):
    """
    拍一拍消息工厂。
    处理拍一拍消息的解析与构建。
    """

    def create(self, message, user_info: UserInfo, db, contact: dict, room: dict):
        msg = PatMessage(
            local_id=message[0],
            server_id=message[1],
            local_type=message[2],
            sort_seq=message[3],
            real_sender_id=message[4],
            create_time=message[5],
            status=message[6],
            upload_status=message[7],
            download_status=message[8],
            server_seq=message[9],
            origin_source=message[10],
            source=message[11],
            message_content=message[12],
            compress_content=message[13],
            packed_info_data=message[14],
            message_db_path=message[17],  # 添加数据库路径信息
            contact=contact,
            room=room,
            title="",
            from_username="",
            patted_username="",
            chat_username="",
            template="",
            user_info=user_info,
        )
        info = parser_pat(msg.parsed_content)
        msg.title = info.get("title", "")
        msg.from_username = info.get("from_username", "")
        msg.patted_username = info.get("patted_username", "")
        msg.chat_username = info.get("chat_username", "")
        msg.template = info.get("template", "")
        # contact 是不对的，需要重新查询的，因为拍一拍消息显示是系统消息，需要根据from重新查询
        contact = db.get_contact_by_username(msg.from_username)
        if contact:
            msg.contact = contact
        return msg


# 工厂注册表
FACTORY_REGISTRY = {
    -1: UnknownMessageFactory(),
    MessageType.Text: TextMessageFactory(),
    MessageType.Image: ImageMessageFactory(),
    MessageType.Audio: AudioMessageFactory(),
    MessageType.Video: VideoMessageFactory(),
    MessageType.Emoji: EmojiMessageFactory(),
    MessageType.System: SystemMessageFactory(),
    MessageType.LinkMessage: LinkMessageFactory(),
    MessageType.LinkMessage2: LinkMessageFactory(),
    MessageType.Music: LinkMessageFactory(),
    MessageType.LinkMessage4: LinkMessageFactory(),
    MessageType.LinkMessage5: LinkMessageFactory(),
    MessageType.LinkMessage6: LinkMessageFactory(),
    MessageType.Applet: LinkMessageFactory(),
    MessageType.Applet2: LinkMessageFactory(),
    MessageType.File: FileMessageFactory(),
    MessageType.FileWait: FileMessageFactory(),
    MessageType.Position: PositionMessageFactory(),
    MessageType.Quote: QuoteMessageFactory(),
    MessageType.Pat: PatMessageFactory(),
    MessageType.RedEnvelope: RedEnvelopeMessageFactory(),
    MessageType.Transfer: TransferMessageFactory(),
    MessageType.Voip: VoipMessageFactory(),
    MessageType.FavNote: FavNoteMessageFactory(),
    MessageType.WeChatVideo: WeChatVideoMessageFactory(),
    MessageType.BusinessCard: BusinessCardMessageFactory(),
    MessageType.OpenIMBCard: BusinessCardMessageFactory(),
    MessageType.MergedMessages: MergedMessageFactory(),
    MessageType.PublicAnnouncement: SystemMessageFactory(),
}

if __name__ == "__main__":
    # 创建 TextMessage 实例
    msg = TextMessage(
        local_id=107,
        server_id=7733522398990171519,
        local_type=MessageType.Text,
        sort_seq=1740373617000,
        real_sender_id=1235,
        create_time=1740373617,
        status=3,
        upload_status=0,
        download_status=0,
        server_seq=842928924,
        origin_source=2,
        source="",
        message_content="wxid_4431474314712:\n我不在",
        compress_content="",
        packed_info_data=None,
        content="我不在",
        message_db_path="message/message_0.db",
        room=None,
        contact=None,
    )
    print(msg.to_json())
