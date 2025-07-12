"""
OCR 处理模块。
支持本地与远程 OCR 识别、文本块合并、相似度查找等功能。
"""

import base64
import logging
import time
from io import BytesIO
from typing import Dict, List, Union

import cv2
import numpy as np
import requests
from PIL import Image
from rapidocr import RapidOCR


class OCRProcessor:
    """
    OCR 处理器。
    支持本地和远程两种识别模式，支持文本块合并与相似度查找。
    """

    def __init__(self, ocr_config: dict = None):
        """
        初始化 OCR 处理器。
        Args:
            ocr_config (dict): OCR 配置。
        """
        ocr_config = ocr_config or {}
        self.use_remote = ocr_config.get("use_remote", False)
        self.remote_url = ocr_config.get("remote_url", "http://192.168.2.192:9003/ocr")
        self.min_confidence = ocr_config.get("min_confidence", 0.5)
        self.merge_threshold = ocr_config.get("merge_threshold", 5.0)
        self.local_ocr = None
        self.logger = logging.getLogger(__name__)

    def setup(self):
        """
        初始化 OCR 识别模型。
        """
        if self.use_remote:
            self.local_ocr = None
        else:
            self.local_ocr = RapidOCR()

    def process_image(
        self, image_path: str = None, image: Image.Image = None
    ) -> List[Dict]:
        """
        处理图片，返回 OCR 结果。
        Args:
            image_path (str): 图片路径。
            image (Image.Image): 图片对象。
        Returns:
            List[Dict]: OCR 结果列表。
        """
        start_time = time.time()
        try:
            if self.use_remote:
                result = self._process_remote(image_path, image)
            else:
                result = self._process_local(image_path, image)
            result = self._merge_text_blocks(result)
            result = [r for r in result if r["confidence"] >= self.min_confidence]
            end_time = time.time()
            self.logger.info(f"OCR 处理耗时: {end_time - start_time:.3f}秒")
            self.logger.info(result)
            return result
        except Exception as e:
            self.logger.error(f"OCR 处理出错: {str(e)}")
            return []

    def _process_local(self, image_path: str, image: Image.Image = None) -> List[Dict]:
        """
        使用本地 OCR 模型处理图片。
        Args:
            image_path (str): 图片路径。
            image (Image.Image): 图片对象。
        Returns:
            List[Dict]: OCR 结果列表。
        """
        try:
            if image_path:
                ocr_result = self.local_ocr(image_path)
            else:
                ocr_result = self.local_ocr(image)
            return self._format_local_result(ocr_result)
        except Exception as e:
            self.logger.error(f"本地 OCR 处理出错: {str(e)}")
            return []

    def _process_remote(
        self, image_path: str = None, image: Image.Image = None
    ) -> List[Dict]:
        """
        使用远程 OCR 服务处理图片。
        Args:
            image_path (str): 图片路径。
            image (Image.Image): 图片对象。
        Returns:
            List[Dict]: OCR 结果列表。
        """
        try:
            if image_path:
                with open(image_path, "rb") as f:
                    file_dict = {"image_file": (image_path, f, "image/png")}
                data = {"use_cls": False}
                response = requests.post(
                    self.remote_url, files=file_dict, data=data, timeout=60
                )
                result = response.json()
                return self._format_remote_result(result)
            elif image:
                img_byte_arr = BytesIO()
                image.save(img_byte_arr, format="PNG")
                img_byte_arr = img_byte_arr.getvalue()
                img_str = base64.b64encode(img_byte_arr).decode("utf-8")
                payload = {"image_data": img_str, "use_cls": False}
                response = requests.post(self.remote_url, data=payload, timeout=60)
                result = response.json()
                return self._format_remote_result(result)
        except Exception as e:
            self.logger.error(f"远程 OCR 处理出错: {str(e)}")
            return []

    def _format_local_result(self, ocr_result) -> List[Dict]:
        """
        格式化本地 OCR 结果。
        Args:
            ocr_result: 本地 OCR 原始结果。
        Returns:
            List[Dict]: 标准化结果。
        """
        formatted_result = []
        try:
            if not all(
                hasattr(ocr_result, attr) for attr in ["boxes", "txts", "scores"]
            ):
                self.logger.error("本地 OCR 结果缺少必要字段")
                return formatted_result
            for i in range(len(ocr_result.boxes)):
                box = ocr_result.boxes[i]
                x_coords = [point[0] for point in box]
                y_coords = [point[1] for point in box]
                bbox = [
                    float(min(x_coords)),
                    float(min(y_coords)),
                    float(max(x_coords)),
                    float(max(y_coords)),
                ]
                text = ocr_result.txts[i]
                score = ocr_result.scores[i]
                formatted_result.append(
                    {"pixel_bbox": bbox, "label": text, "confidence": float(score)}
                )
        except Exception as e:
            self.logger.error(f"格式化本地 OCR 结果时出错: {str(e)}")
        return formatted_result

    def _format_remote_result(self, result: Dict) -> List[Dict]:
        """
        格式化远程 OCR 结果。
        Args:
            result (Dict): 远程 OCR 原始结果。
        Returns:
            List[Dict]: 标准化结果。
        """
        formatted_result = []
        try:
            for key, item in result.items():
                text = item.get("rec_txt", "")
                score = float(item.get("score", 0))
                dt_boxes = item.get("dt_boxes", [])
                if len(dt_boxes) == 4:
                    x_coords = [point[0] for point in dt_boxes]
                    y_coords = [point[1] for point in dt_boxes]
                    bbox = [
                        float(min(x_coords)),
                        float(min(y_coords)),
                        float(max(x_coords)),
                        float(max(y_coords)),
                    ]
                    formatted_result.append(
                        {"pixel_bbox": bbox, "label": text, "confidence": score}
                    )
        except Exception as e:
            self.logger.error(f"格式化远程 OCR 结果时出错: {str(e)}")
        return formatted_result

    def _merge_text_blocks(self, ocr_results: List[Dict]) -> List[Dict]:
        """
        合并相邻的文本块。
        Args:
            ocr_results (List[Dict]): OCR 结果列表。
        Returns:
            List[Dict]: 合并后的 OCR 结果列表。
        """
        if not ocr_results:
            return []
        sorted_results = sorted(
            ocr_results, key=lambda x: (x["pixel_bbox"][1], x["pixel_bbox"][0])
        )
        merged_results = []
        while sorted_results:
            current = sorted_results.pop(0)
            merged = True
            while merged and sorted_results:
                merged = False
                for i, next_block in enumerate(sorted_results):
                    current_bottom_y = current["pixel_bbox"][3]
                    next_top_y = next_block["pixel_bbox"][1]
                    current_left_x = current["pixel_bbox"][0]
                    next_left_x = next_block["pixel_bbox"][0]
                    if (
                        abs(current_left_x - next_left_x) <= 2
                        and abs(current_bottom_y - next_top_y) <= self.merge_threshold
                    ):
                        current["label"] += " " + next_block["label"]
                        current["pixel_bbox"] = [
                            min(current["pixel_bbox"][0], next_block["pixel_bbox"][0]),
                            min(current["pixel_bbox"][1], next_block["pixel_bbox"][1]),
                            max(current["pixel_bbox"][2], next_block["pixel_bbox"][2]),
                            max(current["pixel_bbox"][3], next_block["pixel_bbox"][3]),
                        ]
                        current_len = len(current["label"])
                        next_len = len(next_block["label"])
                        current["confidence"] = (
                            current["confidence"] * current_len
                            + next_block["confidence"] * next_len
                        ) / (current_len + next_len)
                        sorted_results.pop(i)
                        merged = True
                        break
            merged_results.append(current)
        return merged_results

    def _preprocess_image(
        self, image: Union[str, Image.Image, np.ndarray]
    ) -> np.ndarray:
        """
        预处理图片以提高 OCR 准确率。
        Args:
            image (str | Image.Image | np.ndarray): 输入图片。
        Returns:
            np.ndarray: 预处理后的图片。
        """
        try:
            if isinstance(image, str):
                img = cv2.imread(image)
            elif isinstance(image, Image.Image):
                img = np.array(image)
                if len(img.shape) == 3 and img.shape[2] == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            else:
                img = image.copy()
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            denoised = cv2.fastNlMeansDenoising(binary)
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(denoised, -1, kernel)
            return sharpened
        except Exception as e:
            self.logger.error(f"图片预处理出错: {str(e)}")
            return image if isinstance(image, np.ndarray) else np.array(image)

    def find_text(
        self,
        image: Union[str, Image.Image, np.ndarray],
        target_text: str,
        similarity_threshold: float = 0.8,
    ) -> List[Dict]:
        """
        在图片中查找指定文本。
        Args:
            image (str | Image.Image | np.ndarray): 输入图片。
            target_text (str): 目标文本。
            similarity_threshold (float): 相似度阈值。
        Returns:
            List[Dict]: 匹配的文本块列表。
        """
        try:
            processed_image = self._preprocess_image(image)
            if isinstance(processed_image, np.ndarray):
                pil_image = Image.fromarray(processed_image)
                results = self.process_image(image=pil_image)
            else:
                results = self.process_image(image_path=processed_image)
            matches = []
            for result in results:
                similarity = self._calculate_text_similarity(
                    result["label"], target_text
                )
                if similarity >= similarity_threshold:
                    result["similarity"] = similarity
                    matches.append(result)
            return matches
        except Exception as e:
            self.logger.error(f"查找文本出错: {str(e)}")
            return []

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度。
        Args:
            text1 (str): 文本1。
            text2 (str): 文本2。
        Returns:
            float: 相似度分数（0-1）。
        """
        try:
            text1 = text1.lower().strip()
            text2 = text2.lower().strip()
            if text1 == text2:
                return 1.0

            def lcs_length(s1: str, s2: str) -> int:
                m, n = len(s1), len(s2)
                dp = [[0] * (n + 1) for _ in range(m + 1)]
                for i in range(1, m + 1):
                    for j in range(1, n + 1):
                        if s1[i - 1] == s2[j - 1]:
                            dp[i][j] = dp[i - 1][j - 1] + 1
                        else:
                            dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
                return dp[m][n]

            lcs = lcs_length(text1, text2)
            max_len = max(len(text1), len(text2))
            return lcs / max_len if max_len > 0 else 0.0
        except Exception as e:
            self.logger.error(f"计算文本相似度出错: {str(e)}")
            return 0.0
