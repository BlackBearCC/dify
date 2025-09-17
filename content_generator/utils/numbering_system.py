"""
图片编号系统工具类
基于ImageRecognitionWorkflow的编号逻辑重构
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class NumberingSystem:
    """图片编号系统管理类"""

    # 角色配置字典 - 基于新的资源目录结构
    CHARACTER_CONFIGS = {
        "穆昭": {
            "name": "穆昭",
            "display_name": "穆昭",
            "base_path": "resources/images/穆昭",
            "categories": {
                "交通工具": "101",
                "做手工": "102",
                "娱乐": "103",
                "学习": "104",
                "宠物": "105",
                "工作": "106",
                "植物": "107",
                "生病吃药": "108",
                "美食": "112",
                "美食/下午茶": "109",
                "美食/主食": "110",
                "美食/做饭": "111",
                "节日": "113",
                "购物": "114",
                "运动": "115",
                "风景": "116",
                "通用": "100"
            }
        },
        "方知衡": {
            "name": "方知衡",
            "display_name": "方知衡",
            "base_path": "resources/images/方知衡",
            "categories": {
                "通用": "200",
                "动物修": "203",
                "美食修": "202",
                "风景修": "201",
                "动物": "204",
                "在干嘛": "205",
                "工作": "206",
                "植物": "207",
                "生活": "208",
                "生活2": "209",
                "美食": "210",
                "节日": "211",
                "风景": "212"
            }
        }
    }

    def __init__(self, registry_file: str = "id_registry.json"):
        self.registry_file = registry_file
        self.registry = self._load_id_registry()

    def _load_id_registry(self) -> Dict[str, Any]:
        """加载ID注册表"""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载ID注册表失败: {e}")

        # 返回默认结构
        return {
            "used_ids": [],
            "category_counters": {
                # 通用分类
                "000": 0,  # 通用
                # 方知衡分类 (200系列)
                "200": 0,  # 方知衡-通用
                "201": 0,  # 方知衡-风景修
                "202": 0,  # 方知衡-美食修
                "203": 0,  # 方知衡-动物修
                "204": 0,  # 方知衡-动物
                "205": 0,  # 方知衡-在干嘛
                "206": 0,  # 方知衡-工作
                "207": 0,  # 方知衡-植物
                "208": 0,  # 方知衡-生活
                "209": 0,  # 方知衡-生活2
                "210": 0,  # 方知衡-美食
                "211": 0,  # 方知衡-节日
                "212": 0,  # 方知衡-风景
                # 穆昭分类 (100系列)
                "100": 0,  # 穆昭-通用
                "101": 0,  # 穆昭-交通工具
                "102": 0,  # 穆昭-做手工
                "103": 0,  # 穆昭-娱乐
                "104": 0,  # 穆昭-学习
                "105": 0,  # 穆昭-宠物
                "106": 0,  # 穆昭-工作
                "107": 0,  # 穆昭-植物
                "108": 0,  # 穆昭-生病吃药
                "109": 0,  # 穆昭-美食-下午茶
                "110": 0,  # 穆昭-美食-主食
                "111": 0,  # 穆昭-美食-做饭
                "112": 0,  # 穆昭-美食-其他
                "113": 0,  # 穆昭-节日
                "114": 0,  # 穆昭-购物
                "115": 0,  # 穆昭-运动
                "116": 0   # 穆昭-风景
            },
            "files_processed": [],
            "last_update": datetime.now().isoformat()
        }

    def save_id_registry(self) -> bool:
        """保存ID注册表"""
        self.registry["last_update"] = datetime.now().isoformat()

        try:
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存ID注册表失败: {e}")
            return False

    def classify_image_path(self, image_path: str, character: str = None) -> str:
        """根据图片路径和角色进行分类"""
        image_path_lower = image_path.lower()

        # 如果指定了角色，优先使用指定角色的分类
        if character and character in self.CHARACTER_CONFIGS:
            config = self.CHARACTER_CONFIGS[character]
            if config["base_path"].lower() in image_path_lower:
                return self._classify_by_character(image_path_lower, character)

        # 检查所有角色配置
        for char, config in self.CHARACTER_CONFIGS.items():
            if config["base_path"].lower() in image_path_lower:
                return self._classify_by_character(image_path_lower, char)

        # 默认返回通用分类
        return "000"

    def _classify_by_character(self, image_path_lower: str, character: str) -> str:
        """根据角色进行分类"""
        config = self.CHARACTER_CONFIGS[character]

        # 特殊处理穆昭的美食子分类（按最长匹配原则）
        if character == "穆昭" and "美食" in image_path_lower:
            if "下午茶" in image_path_lower:
                return "109"
            elif "主食" in image_path_lower:
                return "110"
            elif "做饭" in image_path_lower:
                return "111"
            else:
                return "112"  # 美食-其他

        # 遍历分类配置（按长度排序，优先匹配长的分类名）
        sorted_categories = sorted(config["categories"].items(), key=lambda x: len(x[0]), reverse=True)
        for category, code in sorted_categories:
            if category.lower() in image_path_lower:
                return code

        # 返回通用分类
        return config["categories"].get("通用", "000")

    def generate_unique_id(self, category_code: str) -> str:
        """生成分类独立的唯一ID"""
        # 确保分类计数器存在
        if "category_counters" not in self.registry:
            self.registry["category_counters"] = {}

        # 如果当前分类不存在，初始化为0
        if category_code not in self.registry["category_counters"]:
            self.registry["category_counters"][category_code] = 0

        # 递增分类计数器
        self.registry["category_counters"][category_code] += 1
        sequence_num = f"{self.registry['category_counters'][category_code]:04d}"
        unique_id = f"99{category_code}{sequence_num}"

        # 检查是否已存在（保险起见）
        while unique_id in self.registry["used_ids"]:
            self.registry["category_counters"][category_code] += 1
            sequence_num = f"{self.registry['category_counters'][category_code]:04d}"
            unique_id = f"99{category_code}{sequence_num}"

            # 防止无限循环
            if self.registry["category_counters"][category_code] >= 9999:
                raise ValueError(f"类别 {category_code} 序号已达到上限（9999）")

        self.registry["used_ids"].append(unique_id)
        return unique_id

    def get_character_config(self, character: str) -> Dict[str, Any]:
        """获取角色配置"""
        return self.CHARACTER_CONFIGS.get(character, self.CHARACTER_CONFIGS["穆昭"])

    def get_available_characters(self) -> list:
        """获取可用角色列表"""
        return list(self.CHARACTER_CONFIGS.keys())

    def get_category_status(self, character: str = None) -> Dict[str, Any]:
        """获取分类编号状态"""
        if character:
            config = self.get_character_config(character)
            categories = config["categories"]
        else:
            # 返回所有分类状态
            categories = {}
            for char_config in self.CHARACTER_CONFIGS.values():
                categories.update(char_config["categories"])

        status = {}
        for category, code in categories.items():
            current_count = self.registry["category_counters"].get(code, 0)
            next_id = f"99{code}{current_count + 1:04d}"
            status[category] = {
                "code": code,
                "current_count": current_count,
                "next_id": next_id
            }

        return status

    def reset_category_counter(self, category_code: str, new_count: int = 0) -> bool:
        """重置指定分类的计数器"""
        try:
            if "category_counters" not in self.registry:
                self.registry["category_counters"] = {}

            self.registry["category_counters"][category_code] = new_count
            return True
        except Exception as e:
            logger.error(f"重置分类计数器失败: {e}")
            return False