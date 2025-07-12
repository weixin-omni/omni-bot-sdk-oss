#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Time        : 2025/1/10 2:02
@Author      : SiYuan
@Email       : 863909694@qq.com
@File        : wxManager-link_parser.py
@Description :
"""
import html
import re
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List

import xmltodict

from ..message_classes import *


def parser_link(xml_content):
    result = {
        "title": "",
        "desc": "",
        "url": "",
        "appname": "",
        "appid": "",
        "cover_url": "",
        "sourcedisplayname": "",
        "sourceusername": "",
    }
    xml_content = xml_content.strip()
    try:
        xml_dict = xmltodict.parse(xml_content)
        dic = xml_dict.get("msg", {})
        cover_url = dic.get("appmsg", {}).get("thumburl", "")
        if not cover_url:
            cover_url = dic.get("appmsg", {}).get("songalbumurl", "")

        result = {
            "title": dic.get("appmsg", {}).get("title", ""),
            "desc": dic.get("appmsg", {}).get("des", ""),
            "url": dic.get("appmsg", {}).get("url", ""),
            "cover_url": cover_url,
            "sourcedisplayname": dic.get("appmsg", {}).get("sourcedisplayname", ""),
            "appname": dic.get("appinfo", {}).get("appname", ""),
            "appid": dic.get("appmsg", {}).get("@appid", ""),
            "sourceusername": dic.get("appmsg", {}).get("sourceusername", ""),
        }
    except:
        print(traceback.format_exc())
    finally:
        return result


def parser_voip(xml_content):
    result = {"invite_type": 0, "duration": 0, "display_content": ""}
    if not xml_content:
        return result
    try:
        xml_content = xml_content.strip()
        xml_dict = xmltodict.parse(f"<voipdata>{xml_content}</voipdata>")
        dic = xml_dict.get("voipdata", {})
        type_ = dic.get("voipmsg", {}).get("@type")
        duration = 0
        if type_ == "VoIPBubbleMsg":
            invite_type = -1
            display_content = (
                dic.get("voipmsg", {}).get("VoIPBubbleMsg", {}).get("msg", "")
            )
        else:
            invite_type = dic.get("voipinvitemsg", {}).get("invite_type", "0")
            duration = dic.get("voiplocalinfo", {}).get("duration", "0")
            display_content = dic.get("voiplocalinfo", {}).get("diaplay_content", "")
        result = {
            "invite_type": int(invite_type),
            "duration": duration,
            "display_content": display_content,
        }
    except:
        print(traceback.format_exc())
    finally:
        return result


def parser_applet(xml_content):
    result = {"title": "", "desc": "", "url": "", "app_icon": ""}
    xml_content = xml_content.strip()
    try:
        xml_dict = xmltodict.parse(xml_content)
        dic = xml_dict.get("msg", {})
        weappinfo = dic.get("appmsg", {}).get("weappinfo", {})
        cover_url = weappinfo.get("weapppagethumbrawurl", "")
        if not cover_url:
            cover_url = weappinfo.get("weapppagethumbrawurl", "")
        if not cover_url:
            page_path = weappinfo.get("pagepath", "")
            # 按 '&' 分割字符串
            parts = page_path.split("&")

            # 遍历每个部分，找到以 'cover=' 开头的部分
            for part in parts:
                if part.startswith("cover="):
                    # 提取 cover 后面的连接
                    cover_url = part.split("=")[1]

        result = {
            "title": dic.get("appmsg", {}).get("title", ""),
            "desc": dic.get("appmsg", {}).get("des", ""),
            "url": dic.get("appmsg", {}).get("url", ""),
            "appname": dic.get("appmsg", {}).get("sourcedisplayname", ""),
            "appid": weappinfo.get("@appid", ""),
            "app_icon": weappinfo.get("weappiconurl", ""),
            "cover_url": cover_url,
        }
    except:
        print(traceback.format_exc())
    finally:
        return result


def parser_music(xml_content):
    if not xml_content:
        return {"type": 3, "title": "发生错误", "is_error": True}
    try:
        root = ET.XML(xml_content)
        appmsg = root.find("appmsg")
        msg_type = int(appmsg.find("type").text)
        title = appmsg.find("title").text
        if len(title) >= 39:
            title = title[:38] + "..."
        artist = appmsg.find("des").text
        link_url = appmsg.find("url").text  # 链接地址
        try:
            songalbumurl = appmsg.find("songalbumurl").text  # 封面地址
        except:
            songalbumurl = ""
        try:
            website_name = root.find("appinfo").find("appname").text
        except:
            website_name = "QQ音乐"
        return {
            "type": msg_type,
            "title": title,
            "artist": artist,
            "url": link_url,
            "songalbumurl": songalbumurl,
            "appname": website_name,
            "is_error": False,
        }
    except Exception as e:
        print(f"音乐分享解析失败\n{traceback.format_exc()}")
        print(f"Music Share Error: {e}")
        return {"type": 3, "title": "发生错误", "is_error": True}


def parser_business(xml_content):
    result = {
        "bigheadimgurl": "",  # 头像原图
        "smallheadimgurl": "",  # 小头像
        "username": "",  # wxid
        "nickname": "",  # 昵称
        "alias": "",  # 微信号
        "province": "",  # 省份
        "city": "",  # 城市
        "sex": 1,  # int ：性别 0：未知，1：男，2：女
        "sign": "",  # 签名
        "openimdesc": "",  # 公司名
        "openimdescicon": "",  # 公司名前面的图标
    }
    xml_content = xml_content.strip()
    try:
        data = xmltodict.parse(xml_content.replace("&", "&amp;"))
        if data and data.get("msg"):
            data = data["msg"]
            result["bigheadimgurl"] = data.get("@bigheadimgurl")
            result["smallheadimgurl"] = data.get("@smallheadimgurl")
            result["username"] = data.get("@username")
            result["nickname"] = data.get("@nickname")
            result["alias"] = data.get("@alias")
            result["province"] = data.get("@province")
            result["city"] = data.get("@city")
            result["sign"] = data.get("@sign")
            result["sex"] = int(data.get("@sex", ""))
            result["openimdesc"] = data.get("@openimdesc")
            result["openimdescicon"] = data.get("@openimdescicon")
        return result
    except:
        print(f"名片解析错误\n{traceback.format_exc()}\n{xml_content}")
        result.update({"type": 1, "text": "【名片解析错误】"})
    finally:
        return result


def replace_entity(match):
    # 获取匹配的数字
    return ""


def process_xml(xml_string):
    # 使用正则表达式替换所有十进制转义字符
    processed_xml = re.sub(r"&#(\d+);", replace_entity, xml_string)
    return processed_xml


def parser_record_item(
    user_info: UserInfo, recorditem, output_dir, wxid, msg_time, level=0
):
    from omni_bot_sdk.models import Contact

    xml_string = recorditem
    if isinstance(xml_string, dict):
        recorditem_dic = xml_string
    else:
        try:
            recorditem_dic = xmltodict.parse(xml_string)
        except:
            xml_string = process_xml(xml_string)
            recorditem_dic = xmltodict.parse(xml_string)
    # print(recorditem_dic)
    datalist = recorditem_dic.get("recordinfo", {}).get("datalist", {})
    count = datalist.get("@count", 0)
    dataitem = datalist.get("dataitem", [])
    result = []
    if isinstance(dataitem, dict):
        # 转发单条消息
        dataitem = [dataitem]
    # logger.info(dataitem)
    for item in dataitem:
        # logger.info(item)
        type_ = item.get("@datatype")
        timestamp = item.get("srcMsgCreateTime")
        if timestamp:
            timestamp = int(timestamp)
        else:
            timestamp = 0
        str_time = item.get("sourcetime")
        display_name = item.get("sourcename")
        avatar_src = item.get("sourceheadurl")
        c = Contact(
            id=0,
            username="x",
            local_type=0,
            alias="",
            encrypt_username="",
            flag=0,
            delete_flag=0,
            verify_flag=0,
            remark="",
            remark_quan_pin="",
            remark_pin_yin_initial="",
            nick_name=display_name,
            pin_yin_initial="",
            quan_pin="",
            big_head_url="",
            small_head_url=avatar_src,
            head_img_md5="",
            chat_room_notify=0,
            is_in_chat_room=0,
            description="",
            extra_buffer=b"",
            chat_room_type=0,
            room_remark="",
        )
        if not timestamp:
            try:
                # 将字符串转换为datetime对象
                dt = datetime.strptime(str_time, "%Y-%m-%d %H:%M:%S")
            except:

                if "上午" in str_time:
                    str_time = str_time.replace("上午 ", "上午")
                    time_format = "%Y-%m-%d 上午%H:%M"
                    dt = datetime.strptime(str_time, time_format) + timedelta(hours=12)
                elif "下午" in str_time:
                    str_time = str_time.replace("下午 ", "下午")
                    time_format = "%Y-%m-%d 下午%H:%M"
                    # 解析后需要加12小时来转换成24小时制
                    dt = datetime.strptime(str_time, time_format) + timedelta(hours=12)
                else:
                    try:
                        import dateparser

                        str_time = str_time.replace("&#x20;", " ")
                        dt = dateparser.parse(str_time)
                        if dt is None:
                            raise ValueError("无法解析时间字符串")
                        timestamp = dt.timestamp()
                    except:
                        print(f"未知的时间格式:{str_time}")
                        dt = datetime.strptime(
                            "1970-01-01 00:00:00", "%Y-%m-%d %H:%M:%S"
                        )
            try:
                # 将datetime对象转换为时间戳
                timestamp = int(dt.timestamp())
            except:
                print(f"未知的时间格式:{str_time}")
                dt = datetime.strptime("1970-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")

        if type_ == "1":
            # 纯文本
            content = item.get("datadesc")
            if item.get("refermsgitem"):
                refermsg = item.get("refermsgitem", {}).get("referdesc", "")
                content = f"{content}\n{refermsg}"
            result.append(
                TextMessage(
                    local_id=0,
                    server_id=0,
                    local_type=MessageType.Text,
                    sort_seq=0,
                    real_sender_id=0,
                    create_time=timestamp,
                    status=0,
                    upload_status=0,
                    download_status=0,
                    server_seq=0,
                    origin_source=0,
                    source="",
                    message_content="",
                    compress_content="",
                    packed_info_data=b"",
                    message_db_path="",
                    contact=c,
                    room=None,
                    content=content,
                    user_info=user_info,
                )
            )
        elif type_ == "2":
            """
            合并转发的聊天记录
            """
            # 图片 & 表情包
            md5 = item.get("fullmd5", "")
            msg = ImageMessage(
                local_id=0,
                server_id=0,
                local_type=MessageType.Image,
                sort_seq=0,
                real_sender_id=0,
                create_time=timestamp,
                status=0,
                upload_status=0,
                download_status=0,
                server_seq=0,
                origin_source=0,
                source="",
                message_content="",
                compress_content="",
                packed_info_data=b"",
                message_db_path="",
                contact=c,
                room=None,
                md5=md5,
                path="",
                thumb_path="",
                file_size=0,
                file_name="",
                file_type="png",
                user_info=user_info,
            )
            result.append(msg)
        elif type_ == "37":
            """
            合并转发的聊天记录
            """
            # 表情包
            md5 = item.get("fullmd5", "")
            msg = EmojiMessage(
                local_id=0,
                server_id=0,
                local_type=MessageType.Emoji,
                sort_seq=0,
                real_sender_id=0,
                create_time=timestamp,
                status=0,
                upload_status=0,
                download_status=0,
                server_seq=0,
                origin_source=0,
                source="",
                message_content="",
                compress_content="",
                packed_info_data=b"",
                message_db_path="",
                contact=c,
                room=None,
                md5=md5,
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
            emoji_item = item.get("emojiitem", {})
            msg.url = emoji_item.get("cdnurlstring", "")
            msg.thumb_url = emoji_item.get("cdnurlstring", "")
            result.append(msg)
        elif type_ == "3":
            # 语音
            result.append(
                TextMessage(
                    local_id=0,
                    server_id=0,
                    local_type=MessageType.Audio,
                    sort_seq=0,
                    real_sender_id=0,
                    create_time=timestamp,
                    status=0,
                    upload_status=0,
                    download_status=0,
                    server_seq=0,
                    origin_source=0,
                    source="",
                    message_content="",
                    compress_content="",
                    packed_info_data=b"",
                    message_db_path="",
                    contact=c,
                    room=None,
                    content="【转发语音不可播放】",
                    user_info=user_info,
                )
            )
        elif type_ == "4":
            # 视频
            md5 = item.get("fullmd5", "")
            path = item.get("datasourcepath", "")
            result.append(
                VideoMessage(
                    local_id=0,
                    server_id=0,
                    local_type=MessageType.Video,
                    sort_seq=0,
                    real_sender_id=0,
                    create_time=timestamp,
                    status=0,
                    upload_status=0,
                    download_status=0,
                    server_seq=0,
                    origin_source=0,
                    source="",
                    message_content="",
                    compress_content="",
                    packed_info_data=b"",
                    message_db_path="",
                    contact=c,
                    room=None,
                    path=path,
                    md5=md5,
                    file_type="mp4",
                    file_name="",
                    file_size=0,
                    thumb_path="",
                    duration=0,
                    raw_md5=md5,
                    user_info=user_info,
                )
            )
        elif type_ == "5":
            # 链接
            web_item = item.get("weburlitem", {})
            result.append(
                LinkMessage(
                    local_id=0,
                    server_id=0,
                    local_type=MessageType.LinkMessage,
                    sort_seq=0,
                    real_sender_id=0,
                    create_time=timestamp,
                    status=0,
                    upload_status=0,
                    download_status=0,
                    server_seq=0,
                    origin_source=0,
                    source="",
                    message_content="",
                    compress_content="",
                    packed_info_data=b"",
                    message_db_path="",
                    contact=c,
                    room=None,
                    href=web_item.get("url", ""),
                    title=web_item.get("title", ""),
                    description=web_item.get("desc", ""),
                    cover_path="",
                    cover_url="",
                    app_name=web_item.get("appmsgshareitem", {}).get("srcdisplayname"),
                    app_icon="",
                    app_id="",
                    user_info=user_info,
                )
            )
        elif type_ == "6":
            # 位置分享
            locitem = item.get("locitem", {})
            label = locitem.get("label", "")
            poiname = locitem.get("poiname", "")
            try:
                x = float(locitem.get("lng", "0"))
                y = float(locitem.get("lat", "0"))
                scale = float(locitem.get("scale", "0"))
            except:
                x, y, scale = 0, 0, 0
            result.append(
                PositionMessage(
                    local_id=0,
                    server_id=0,
                    local_type=MessageType.Position,
                    sort_seq=0,
                    real_sender_id=0,
                    create_time=timestamp,
                    status=0,
                    upload_status=0,
                    download_status=0,
                    server_seq=0,
                    origin_source=0,
                    source="",
                    message_content="",
                    compress_content="",
                    packed_info_data=b"",
                    message_db_path="",
                    contact=c,
                    room=None,
                    x=x,
                    y=y,
                    label=label,
                    poiname=poiname,
                    scale=scale,
                    user_info=user_info,
                )
            )

        elif type_ == "8":
            # 文件
            md5 = item.get("fullmd5", "")
            datasize = item.get("datasize")
            if datasize:
                datasize = int(datasize)
            else:
                datasize = 0
            result.append(
                FileMessage(
                    local_id=0,
                    server_id=0,
                    local_type=MessageType.File,
                    sort_seq=0,
                    real_sender_id=0,
                    create_time=timestamp,
                    status=0,
                    upload_status=0,
                    download_status=0,
                    server_seq=0,
                    origin_source=0,
                    source="",
                    message_content="",
                    compress_content="",
                    packed_info_data=b"",
                    message_db_path="",
                    contact=c,
                    room=None,
                    path="",
                    md5=md5,
                    file_type=item.get("datafmt", ""),
                    file_name=item.get("datatitle", ""),
                    file_size=datasize,
                    user_info=user_info,
                )
            )
        elif type_ == "17":
            # 嵌套的消息
            result.append(
                MergedMessage(
                    local_id=0,
                    server_id=0,
                    local_type=MessageType.MergedMessages,
                    sort_seq=0,
                    real_sender_id=0,
                    create_time=timestamp,
                    status=0,
                    upload_status=0,
                    download_status=0,
                    server_seq=0,
                    origin_source=0,
                    source="",
                    message_content="",
                    compress_content="",
                    packed_info_data=b"",
                    message_db_path="",
                    contact=c,
                    room=None,
                    title=item.get("datatitle"),
                    description=item.get("datadesc"),
                    messages=parser_record_item(
                        user_info,
                        item.get("recordxml"),
                        output_dir,
                        wxid,
                        msg_time,
                        level + 1,
                    ),
                    level=level,
                    user_info=user_info,
                )
            )
    return result


def parser_merged_messages(
    user_info: UserInfo, xml: str, output_dir, wxid, msg_time, level=0
):
    try:
        try:
            data_dic = xmltodict.parse(xml).get("msg", {})
        except:
            new_xml1 = html.unescape(xml)
            new_xml2 = new_xml1.replace("&", "&amp;")
            # xml = xml.replace('&#x20;', ' ').replace('&#15;', '').replace('&#x0A;', '\n').replace('\xa0',' ')  # 搞不懂这帮人在干嘛，有些转义，有些不转义
            # html.unescape(xml)
            data_dic = xmltodict.parse(new_xml2).get("msg", {})
        app_msg_dic = data_dic.get("appmsg", {})
        desc = app_msg_dic.get("des", "")
        title = app_msg_dic.get("title", "")
        recorditem = app_msg_dic.get("recorditem", "")
        return {
            "title": title,  # 标题
            "desc": desc,  # 描述
            "messages": parser_record_item(
                user_info, recorditem, output_dir, wxid, msg_time, level
            ),  # List[dict] 消息内容
        }
    except:
        print(xml)
        # print(new_xml1)
        # print(new_xml2)
        print(traceback.format_exc())
        # raise ValueError('合并转发的消息解析失败')
        return {
            "title": "解析失败",  # 标题
            "desc": "合并转发的消息解析失败",  # 描述
            "messages": [],
        }


def parser_wechat_video(xml_content):
    result = {
        "appid": "",  # 暂时不用
        "title": "",  # 标题
        "sourcedisplayname": "",  # 视频号名称
        "weappiconurl": "",  # 视频号logo
        "authIconUrl": "",  # 视频号认证URL，昵称后缀
        "cover": "",  # 封面url
        "duration": 0,
    }
    xml_content = xml_content.strip()
    try:
        dic_data = (
            xmltodict.parse(xml_content)
            .get("msg", {})
            .get("appmsg", {})
            .get("finderFeed", {})
        )
        sourcedisplayname = dic_data.get("nickname", "")
        weappiconurl = dic_data.get("avatar", "")
        authIconUrl = dic_data.get("authIconUrl", "")
        title = dic_data.get("desc", "")
        media_count = dic_data.get("mediaCount", "0")
        if media_count > "1":
            cover = (
                dic_data.get("mediaList", {}).get("media", [])[0].get("thumbUrl", "")
            )
            duration = 0
        else:
            cover = dic_data.get("mediaList", {}).get("media", {}).get("coverUrl", "")
            duration = (
                dic_data.get("mediaList", {})
                .get("media", {})
                .get("videoPlayDuration", 0)
            )
        result = {
            "title": title,
            "url": "",
            "sourcedisplayname": sourcedisplayname,
            "weappiconurl": weappiconurl,
            "cover": cover,
            "authIconUrl": authIconUrl,
            "duration": duration,
        }
    except:
        print(traceback.format_exc())
    finally:
        return result


def parser_position(xml_content):
    result = {
        "x": "0",  # 经度
        "y": "0",  # 维度
        "label": "",  # 详细标签
        "poiname": "",  # 位置点标记名
        "scale": "0",  # 缩放率
    }
    try:
        data = xmltodict.parse(xml_content)
        if data and data.get("msg"):
            data = data["msg"]
            result["x"] = data["location"]["@x"]
            result["y"] = data["location"]["@y"]
            result["label"] = data["location"].get("@label")
            result["poiname"] = data["location"].get("@poiname")
            result["scale"] = data["location"].get("@scale")
    except:
        print(f"位置分享解析错误\n{traceback.format_exc()} \n{xml_content}")
        result.update({"type": 1, "text": "【位置分享解析错误】"})
    finally:
        return result


def parser_reply(xml_content):
    """
    @param data:
    @return: {
            "text": '发生错误', 发送内容
            'svrid': '', 引用消息id
            'refermsg_type': -1, 引用消息类型
            "refer_text": '引用错误', 引用内容
        }
    """
    if not xml_content:
        return {
            # "type": msg_type,
            "text": "发生错误",
            "svrid": "",
            "refermsg_type": -1,
            "refer_text": "引用错误",
        }
    xml_content = xml_content.replace("&#01;", "").replace("&#20;", "")
    try:
        data = xmltodict.parse(xml_content).get("msg", {}).get("appmsg", {})
        refermsg_type = int(data.get("refermsg", {}).get("type", "1"))
        title = data.get("title", "")
        displayname = data.get("refermsg", {}).get("displayname", "")
        svrid = data.get("refermsg", {}).get("svrid", 0)
        return {
            "text": title,
            "svrid": svrid,
            "refermsg_type": refermsg_type,
        }
        # if refermsg_type == 1:
        #     return {
        #         # "type": msg_type,
        #         "text": title,
        #         'svrid': data.get('refermsg', {}).get('svrid', 0),
        #         'refermsg_type': refermsg_type,
        #         "refer_text": f"{refermsg_displayname}：{refermsg_content}",
        #     }
        # elif refermsg_type == 3:
        #     return {
        #         # "type": msg_type,
        #         "text": title,
        #         'svrid': data.get('refermsg', {}).get('svrid', 0),
        #         'refermsg_type': refermsg_type,
        #         "refer_text": f"{displayname}：【图片消息】",
        #     }
        # elif refermsg_type == 34:
        #     return {
        #         # "type": msg_type,
        #         "text": title,
        #         'svrid': data.get('refermsg', {}).get('svrid', 0),
        #         'refermsg_type': refermsg_type,
        #         "refer_text": f"{displayname}：【语音消息】",
        #     }
        # elif refermsg_type == 43:
        #     return {
        #         # "type": msg_type,
        #         "text": title,
        #         'svrid': data.get('refermsg', {}).get('svrid', 0),
        #         'refermsg_type': refermsg_type,
        #         "refer_text": f"{displayname}：【视频消息】",
        #     }
        # elif refermsg_type == 47:
        #     return {
        #         # "type": msg_type,
        #         "text": title,
        #         'svrid': data.get('refermsg', {}).get('svrid', 0),
        #         'refermsg_type': refermsg_type,
        #         "refer_text": f"{displayname}：【表情包】",
        #     }
        # elif refermsg_type == 49:
        #     content = data.get('refermsg', {}).get('content', '')
        #     content = xmltodict.parse(content).get('msg', {}).get('appmsg', {})
        #     refermsg_content = content.get('title', '')
        #     return {
        #         # "type": msg_type,
        #         "text": title,
        #         'svrid': data.get('refermsg', {}).get('svrid', 0),
        #         'refermsg_type': refermsg_type,
        #         "refer_text": f"{displayname}：{refermsg_content}",
        #         "url": content.get('url', ''),
        #     }
        # elif refermsg_type == 0:
        #     return {
        #         # "type": msg_type,
        #         "text": title,
        #         'svrid': data.get('refermsg', {}).get('svrid', 0),
        #         'refermsg_type': refermsg_type,
        #         "refer_text": data.get('refermsg', {}).get('ref_msg_text', ''),
        #     }
        # elif refermsg_type == 66:
        #     return {
        #         # "type": msg_type,
        #         "text": title,
        #         'svrid': data.get('refermsg', {}).get('svrid', 0),
        #         'refermsg_type': refermsg_type,
        #         "refer_text": f"{displayname}：【名片分享】",
        #     }
        # elif refermsg_type == 42:
        #     return {
        #         # "type": msg_type,
        #         "text": title,
        #         'svrid': data.get('refermsg', {}).get('svrid', 0),
        #         'refermsg_type': refermsg_type,
        #         "refer_text": f"{displayname}：【名片分享】",
        #     }
        # elif refermsg_type == 48:
        #     position_dict = xmltodict.parse(data.get('refermsg', {}).get('content', '')).get('msg')
        #     return {
        #         # "type": msg_type,
        #         "text": title,
        #         'svrid': data.get('refermsg', {}).get('svrid', 0),
        #         'refermsg_type': refermsg_type,
        #         "refer_text": f"{displayname}：{position_dict['location'].get('@poiname')}",
        #     }
        # else:
        #     logger.info(f'发现未知的引用消息\n{data}')
        #     return {
        #         # "type": msg_type,
        #         "text": title,
        #         'svrid': data.get('refermsg', {}).get('svrid', 0),
        #         'refermsg_type': refermsg_type,
        #         "refer_text": f"{displayname}：【其他消息】",
        #     }
    except:
        print(f"{xml_content}\n\n引用消息解析错误\n{traceback.format_exc()}")
        return {
            # "type": msg_type,
            "text": "发生错误",
            "svrid": "",
            "refermsg_type": -1,
            "refer_text": "引用错误",
        }


def parser_transfer(xml_content):
    result = {"pay_subtype": 0, "pay_memo": "", "fee_desc": "", "receiver_username": ""}
    try:
        data = xmltodict.parse(xml_content).get("msg", {}).get("appmsg", {})
        result = {
            "pay_subtype": int(data.get("wcpayinfo", {}).get("paysubtype", "-1")),
            "pay_memo": data.get("wcpayinfo", {}).get("pay_memo", ""),
            "fee_desc": data.get("wcpayinfo", {}).get("feedesc", ""),
            "receiver_username": data.get("wcpayinfo", {}).get("receiver_username", ""),
        }
    except:
        print(f"转账解析错误\n{traceback.format_exc()}")
        result.update({"type": 1, "text": "【位置分享解析错误】"})
    finally:
        return result


def parser_red_envelop(xml_content):
    result = {"icon_url": "", "title": "", "inner_type": 0}
    try:
        data = xmltodict.parse(xml_content).get("msg", {}).get("appmsg", {})
        result = {
            "icon_url": data.get("wcpayinfo", {}).get("iconurl", ""),
            "title": data.get("wcpayinfo", {}).get("receivertitle", ""),
            "inner_type": int(data.get("wcpayinfo", {}).get("innertype", "0")),
        }
    except:
        print(f"红包解析错误\n{traceback.format_exc()}")
        result.update({"type": 1, "text": "【位置分享解析错误】"})
    finally:
        return result


def parser_file(xml_content):
    result = {
        "file_name": "",
        "file_size": 0,
        "md5": "",
        "file_type": "",
        "app_name": "",
    }
    try:
        data0 = xmltodict.parse(xml_content).get("msg", {})
        data = data0.get("appmsg", {})
        totallen = data.get("appattach", {}).get("totallen")
        if isinstance(totallen, list):
            totallen = totallen[0]
        if not totallen:
            totallen = "0"
        result = {
            "file_name": data.get("title", ""),
            "file_size": int(totallen),
            "md5": data.get("md5", ""),
            "file_type": data.get("appattach", {}).get("fileext", ""),
            "app_name": data.get("appinfo", {}).get("appname", ""),
        }
    except:
        print(f"文件解析错误\n{traceback.format_exc()}\n{xml_content}")
    finally:
        return result


def parser_favorite_note(xml_content):
    result = {
        "title": "",
        "desc": "",
        "recorditem": "",
    }
    try:
        data = xmltodict.parse(xml_content).get("msg", {}).get("appmsg", {})
        recorditem = data.get("recorditem", "")
        xml_string = recorditem
        if isinstance(xml_string, dict):
            recorditem_dic = xml_string
        else:
            recorditem_dic = xmltodict.parse(xml_string)
        result = {
            "title": data.get("title", ""),
            "desc": data.get("des", ""),
            "recorditem": recorditem_dic,
        }
    except:
        print(f"笔记解析错误\n{traceback.format_exc()}")
    finally:
        return result


def parser_pat(xml_content):
    result = {
        "title": "",
        "from_username": "",
        "patted_username": "",
        "chat_username": "",
        "template": "",
    }
    try:
        data = xmltodict.parse(xml_content).get("msg", {}).get("appmsg", {})
        patinfo = data.get("patinfo", {})
        result = {
            "title": data.get("title", ""),
            "from_username": patinfo.get("fromusername", ""),
            "patted_username": patinfo.get("pattedusername", ""),
            "chat_username": patinfo.get("chatusername", ""),
            "template": patinfo.get("template", ""),
        }
    except:
        print(f"拍一拍解析错误\n{traceback.format_exc()}\n{xml_content}")
    finally:
        return result


if __name__ == "__main__":
    pass


def wx_sport(xml):
    dic_data = {}
    more = ""
    try:
        dic_data = xmltodict.parse(xml).get("msg", {}).get("appmsg", {})
        hardwareinfo = dic_data.get("hardwareinfo", {})
        rankinfo = hardwareinfo.get("messagenodeinfo", {}).get("rankinfo", {})
        rank = rankinfo.get("rank", {}).get("rankdisplay", "")
        score = rankinfo.get("score", {}).get("scoredisplay", "")
        rankinfolist = (
            hardwareinfo.get("rankview", {}).get("rankinfolist", {}).get("rankinfo", [])
        )
        rank_list = []
        for rank_info in rankinfolist:
            username = rank_info.get("username", "")
            rank1 = rank_info.get("rank", {}).get("rankdisplay", "")
            score1 = rank_info.get("score", {}).get("scoredisplay", "")
            rank_list.append({"rank": rank1, "score": score1, "username": username})
        return {
            "rank": rank,
            "score": score,
            "rank_list": rank_list,
            "data": f"{dic_data}",
        }
    except:
        print(traceback.format_exc())
        print(dic_data)
        return []


def wx_EMS_data(bytesExtra, compress_content_):
    dic_data = {}
    send_city = ""
    send_name = ""
    express_id = ""
    send_time = ""
    send_address = ""
    courier = ""
    courier_phone = ""
    expect_handle = ""
    sign_time = ""
    sign_result = ""
    remark = ""
    update_time = ""

    try:
        if isinstance(compress_content_, bytes):
            xml = decompress_CompressContent(compress_content_)
        else:
            xml = compress_content_
        dic_data = xmltodict.parse(xml).get("msg", {}).get("appmsg", {})

        mmreader = dic_data.get("mmreader", {})
        template_header = mmreader.get("template_header", {})
        template_detail = mmreader.get("template_detail", {})
        if not template_header or not template_detail:
            return {}
        title = template_header.get("title", "")
        digest = template_header.get("first_data", "")
        display_name = template_header.get("display_name", "")
        if not title:
            title = dic_data.get("title", "")
        if not display_name:
            display_name = dic_data.get("title")
        line_content = template_detail.get("line_content", {})
        lines = line_content.get("lines", {}).get("line")

        if isinstance(lines, List):
            for line in lines:
                key = line.get("key").get("word")
                value = line.get("value").get("word")
                if key.startswith("寄件城市"):
                    send_city += value
                elif key.startswith("寄件人"):
                    send_name += value
                elif key.startswith("快递单号") or key == "运单号":
                    express_id += value
                elif key.startswith("寄件时间"):
                    send_time += value
                elif key.startswith("派送地址"):
                    send_address += value
                elif key.startswith("快递员"):
                    courier += value
                elif key.startswith("快递员电话"):
                    courier_phone += value
                elif key.startswith("预计派送处理"):
                    expect_handle += value
                elif key.startswith("签收时间"):
                    sign_time += value
                elif key.startswith("签收结果"):
                    sign_result += value
                elif key == "备注：":
                    remark += value
                elif key == "更新时间：":
                    update_time += value
        else:
            return {}
        return {
            "title": title,
            "digest": digest,
            "display_name": display_name,
            "send_city": send_city,
            "send_name": send_name,
            "express_id": express_id,
            "send_time": send_time,
            "send_address": send_address,
            "courier": courier,
            "courier_phone": courier_phone,
            "expect_handle": expect_handle,
            "sign_time": sign_time,
            "sign_result": sign_result,
            "remark": remark,
            "update_time": update_time,
            "data": f"{dic_data}",
        }
    except:
        print(traceback.format_exc())
        print(dic_data)
        return {}


def wx_pdd_data(bytesExtra, compress_content_):
    title = ""
    display_name = ""
    dic_data = {}
    product = ""
    order_id = ""
    express = ""
    express_id = ""
    sign_time = ""
    product_num = ""
    pdd_member = ""
    order_status = ""
    refund_money = ""
    refund_status = ""
    audit_explain = ""
    problem_type = ""
    submit_time = ""
    handle_result = ""
    phone_number = ""
    recharge_money = ""
    refund_method = ""
    user_name = ""
    order_money = ""

    try:
        if isinstance(compress_content_, bytes):
            xml = decompress_CompressContent(compress_content_)
        else:
            xml = compress_content_
        dic_data = xmltodict.parse(xml).get("msg", {}).get("appmsg", {})

        mmreader = dic_data.get("mmreader", {})
        template_header = mmreader.get("template_header", {})
        template_detail = mmreader.get("template_detail", {})
        if not template_header or not template_detail:
            return {}
        title = template_header.get("title", "")
        display_name = template_header.get("display_name", "")
        if not title:
            title = dic_data.get("title", "")
        if not display_name:
            display_name = dic_data.get("title")
        line_content = template_detail.get("line_content", {})
        lines = line_content.get("lines", {}).get("line")
        if isinstance(lines, List):
            for line in lines:
                key = line.get("key").get("word")
                value = line.get("value").get("word")
                if (
                    key == "商品名称："
                    or key == "商品信息："
                    or key == "商品："
                    or key == "商品详情："
                    or key.startswith("商品名")
                ):
                    product += value
                elif key == "订单编号：" or key == "订单号：":
                    order_id += value
                elif key == "物流服务：" or key == "快递公司：":
                    express += value
                elif key == "快递单号：":
                    express_id += value
                elif key == "签收时间：":
                    sign_time += value
                elif key == "商品数量：":
                    product_num += value
                elif key == "拼单成员：":
                    pdd_member += value
                elif key == "订单状态：":
                    order_status += value
                elif key == "退款金额：":
                    refund_money += value
                elif key == "退款状态：":
                    refund_status += value
                elif key == "审核说明：":
                    audit_explain += value
                elif key == "问题类型：":
                    problem_type += value
                elif key == "提交时间：":
                    submit_time += value
                elif key == "处理结果：":
                    handle_result += value
                elif key == "充值号码：":
                    phone_number += value
                elif key == "充值金额：":
                    recharge_money += value
                elif key == "退款方式：":
                    refund_method += value
                elif key == "用户名：":
                    user_name += value
                elif key == "订单金额：":
                    order_money += value
    except:
        print(traceback.format_exc())
        print(dic_data)
    finally:
        return {
            "title": title,
            "display_name": display_name,
            "product": product,
            "order_id": order_id,
            "express": express,
            "express_id": express_id,
            "sign_time": sign_time,
            "product_num": product_num,
            "pdd_member": pdd_member,
            "order_status": order_status,
            "refund_money": refund_money,
            "refund_status": refund_status,
            "audit_explain": audit_explain,
            "problem_type": problem_type,
            "submit_time": submit_time,
            "handle_result": handle_result,
            "phone_number": phone_number,
            "recharge_money": recharge_money,
            "refund_method": refund_method,
            "user_name": user_name,
            "order_money": order_money,
            "data": f"{dic_data}",
        }


def wx_collection_data(xml):
    dic_data = {}
    summary = ""
    more = ""
    try:
        dic_data = xmltodict.parse(xml).get("msg", {}).get("appmsg", {})
        # print(dic_data)
        mmreader = dic_data.get("mmreader", {})
        template_header = mmreader.get("template_header", {})
        template_detail = mmreader.get("template_detail", {})
        title = template_header.get("title", "")
        display_name = template_header.get("display_name", "")
        if not title:
            title = dic_data.get("title", "")
        if not display_name:
            display_name = dic_data.get("title")
        template_id = dic_data.get("template_id", "")
        line_content = template_detail.get("line_content", {})
        money = (
            line_content.get("topline", {}).get("value", {}).get("word", "").strip("￥")
        )
        lines = line_content.get("lines", {}).get("line")
        if isinstance(lines, List):
            for line in lines:
                key = line.get("key").get("word")
                value = line.get("value").get("word")
                if key == "汇总":
                    summary += value
                elif key == "备注":
                    more += value

        return {
            "title": title,
            "display_name": display_name,
            "template_id": template_id,
            "money": money,
            "summary": summary,
            "data": f"{dic_data}",
            "more": more,
        }

    except:
        print(traceback.format_exc())
        print(dic_data)
        return {}


def wx_pay_data(xml):
    dic_data = {}
    more = ""
    try:
        dic_data = xmltodict.parse(xml).get("msg", {}).get("appmsg", {})
        # print(dic_data)
        mmreader = dic_data.get("mmreader", {})
        template_header = mmreader.get("template_header", {})
        template_detail = mmreader.get("template_detail", {})
        title = template_header.get("title", "")
        display_name = template_header.get("display_name", "")
        if not title:
            title = dic_data.get("title", "")
        if not display_name:
            display_name = dic_data.get("title")
        template_id = dic_data.get("template_id", "")
        line_content = template_detail.get("line_content", {})
        money = (
            line_content.get("topline", {}).get("value", {}).get("word", "").strip("￥")
        )
        lines = line_content.get("lines", {}).get("line")
        payment_type = ""
        acquiring_institution = ""
        if isinstance(lines, List):
            for line in lines:
                key = line.get("key").get("word")
                value = line.get("value").get("word")
                if (
                    key == "付款方式"
                    or key == "支付方式"
                    or key == "收款账户"
                    or key == "退款方式"
                ):
                    payment_type = value
                elif key == "收单机构" or key == "收款方":
                    acquiring_institution = value
                elif key == "退款方式":
                    payment_type = value
                elif key == "退款原因":
                    acquiring_institution = value
                elif key == "备注" or key == "退款原因":
                    more += value
        else:
            payment_type = (
                line_content.get("topline", {}).get("key", {}).get("word", "")
            )
            acquiring_institution = "个体商户"
        return {
            "title": title,
            "display_name": display_name,
            "template_id": template_id,
            "money": money,
            "payment_type": payment_type,
            "acquiring_institution": acquiring_institution,
            "data": f"{dic_data}",
            "more": more,
        }
    except:
        print(traceback.format_exc())
        print(dic_data)
        return {}
