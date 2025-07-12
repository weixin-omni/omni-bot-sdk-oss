#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@Time        : 2024/12/12 16:55
@Author      : SiYuan
@Email       : 863909694@qq.com
@File        : MemoTrace-audio_parser.py
@Description :
"""
import xmltodict


def parser_audio(xml_content):
    result = {"audio_length": 0, "audio_text": ""}
    xml_content = xml_content.strip()
    try:
        xml_dict = xmltodict.parse(xml_content)
        voice_length = (
            xml_dict.get("msg", {}).get("voicemsg", {}).get("@voicelength", 0)
        )
        audio_text = xml_dict.get("msg", {}).get("voicetrans", {}).get("@transtext", "")
        result = {"audio_length": voice_length, "audio_text": audio_text}
    except:
        if xml_content and ":" in xml_content:
            voice_length = int(xml_content.split(":")[1])
            result = {"audio_length": voice_length}
    finally:
        return result


if __name__ == "__main__":
    pass
