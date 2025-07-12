#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Time        : 2024/12/12 18:10
@Author      : SiYuan
@Email       : 863909694@qq.com
@File        : MemoTrace-emoji_parser.py
@Description :
"""
import base64
import html
import re
import traceback

import xmltodict
from google.protobuf.json_format import MessageToDict

from .util.protocbuf import emoji_desc_pb2


def parser_emoji(xml_content):
    result = {"md5": 0, "url": "", "width": 0, "height": 0, "desc": ""}

    def extract_msg(text):
        # 使用正则表达式匹配第一个 <msg> 标签及其内容
        pattern = r"(<msg>.*?</msg>)"
        match = re.search(pattern, text)
        return f"<msg>{match.group(0)}</msg>" if match else ""

    # xml_content = xml_content.strip().replace('&', '&amp;')
    try:
        xml_dict = xmltodict.parse(xml_content)
    except:
        try:
            xml_content = extract_msg(xml_content)
            xml_dict = xmltodict.parse(xml_content)
        except:
            pass
    try:
        emoji_dic = xml_dict.get("msg", {}).get("emoji", {})
        if "@androidmd5" in emoji_dic:
            md5 = emoji_dic.get("@androidmd5", "")
        else:
            md5 = emoji_dic.get("@md5", "")
        # logger.error(xml_dict)
        desc_bs64 = emoji_dic.get("@desc", "")
        desc = ""
        if desc_bs64:
            # 逆天微信，竟然把protobuf数据用base64编码后放入xml里
            desc_bytes_proto = base64.b64decode(desc_bs64)
            message = emoji_desc_pb2.EmojiDescData()
            # 解析二进制数据
            message.ParseFromString(desc_bytes_proto)
            dict_output = MessageToDict(message)
            for item in dict_output.get("descItem", []):
                desc = item.get("desc", "")
                if desc:
                    break
        # url 需要 urldecode
        url = emoji_dic.get("@cdnurl", "")
        if url:
            url = html.unescape(url)
        result = {
            "md5": md5,
            "url": url,
            "width": emoji_dic.get("@width", 0),
            "height": emoji_dic.get("@height", 0),
            "desc": desc,
        }
    except:
        print(traceback.format_exc())
        print(xml_content)
    finally:
        return result


if __name__ == "__main__":
    pass
