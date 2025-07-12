#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Time        : 2024/12/12 22:52
@Author      : SiYuan
@Email       : 863909694@qq.com
@File        : MemoTrace-file_parser.py
@Description :
"""

import xmltodict


def get_image_type(header):
    # 根据文件头判断图片类型
    if header.startswith(b"\xff\xd8"):
        return "jpeg"
    elif header.startswith(b"\x89PNG"):
        return "png"
    elif header[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    elif header.startswith(b"BM"):
        return "bmp"
    elif header.startswith(b"\x00\x00\x01\x00"):
        return "ico"
    elif header.startswith(b"\x49\x49\x2a\x00") or header.startswith(
        b"\x4d\x4d\x00\x2a"
    ):
        return "tiff"
    elif header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "webp"
    else:
        return "png"


def parse_video(xml_content):
    result = {"md5": 0}
    xml_content = xml_content.strip()
    try:
        xml_dict = xmltodict.parse(xml_content)
        # logger.error(json.dumps(xml_dict))
        video_dic = xml_dict.get("msg", {}).get("videomsg", {})
        md5 = video_dic.get("@md5", "")  # 下载后压缩视频的md5
        rawmd5 = video_dic.get("@rawmd5", "")  # 原视频md5
        result = {
            "md5": md5,
            "rawmd5": rawmd5,
            "length": video_dic.get("@playlength", 0),
            "size": video_dic.get("@length", 0),
        }
    except:
        print(f"视频解析失败\n{xml_content}")
    finally:
        return result


if __name__ == "__main__":
    pass
