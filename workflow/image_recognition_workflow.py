"""图片识别工作流 - 基于豆包/DoubaoLLM的图片识别系统
提供对图片的内容识别、标题生成和详细描述功能
"""

import json
import asyncio
import base64
import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import csv

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.graph import StateGraph
from core.base import BaseNode
from llm.base import LLMFactory
from core.types import LLMConfig, TaskResult, Message, MessageRole
from workflow.story_generator import StoryGenerationNode

logger = logging.getLogger(__name__)

class ImageRecognitionWorkflow:
    """图片识别工作流管理器"""    
    # 角色配置字典
    CHARACTER_CONFIGS = {
        "穆昭": {
            "name": "穆昭",
            "display_name": "穆昭",
            "base_path": "workspace/input/穆昭",
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
            },
            "scan_patterns": [
                "workspace/input/穆昭/交通工具/*.png",
                "workspace/input/穆昭/做手工/*.png",
                "workspace/input/穆昭/娱乐/*.png",
                "workspace/input/穆昭/学习/*.png",
                "workspace/input/穆昭/宠物/*.png",
                "workspace/input/穆昭/工作/*.png",
                "workspace/input/穆昭/植物/*.png",
                "workspace/input/穆昭/生病吃药/*.png",
                "workspace/input/穆昭/美食/*.png",
                "workspace/input/穆昭/美食/下午茶/*.png",
                "workspace/input/穆昭/美食/主食/*.png",
                "workspace/input/穆昭/美食/做饭/*.png",
                "workspace/input/穆昭/节日/*.png",
                "workspace/input/穆昭/购物/*.png",
                "workspace/input/穆昭/运动/*.png",
                "workspace/input/穆昭/风景/*.png"
            ]
        },
        "方知衡": {
            "name": "方知衡",
            "display_name": "方知衡",
            "base_path": "workspace/input/方知衡",
            "categories": {
                "通用": "200",
                "动物修": "203",
                "美食修": "202", 
                "风景修": "201",
                # 原方知衡100类别，现在整合到方知衡中，编码延续
                "动物": "204",
                "在干嘛": "205", 
                "工作": "206",
                "植物": "207",
                "生活": "208",
                "生活2": "209",
                "美食": "210",
                "节日": "211",
                "风景": "212"
            },
            "scan_patterns": [
                "workspace/input/方知衡/通用/*.png",
                "workspace/input/方知衡/动物修/*.png",
                "workspace/input/方知衡/美食修/*.png",
                "workspace/input/方知衡/风景修/*.png",
                # 原方知衡100目录的类别，现在都在方知衡目录下
                "workspace/input/方知衡/动物/*.png",
                "workspace/input/方知衡/在干嘛/*.png",
                "workspace/input/方知衡/工作/*.png",
                "workspace/input/方知衡/植物/*.png",
                "workspace/input/方知衡/生活/*.png",
                "workspace/input/方知衡/生活2/*.png",
                "workspace/input/方知衡/美食/*.png",
                "workspace/input/方知衡/节日/*.png",
                "workspace/input/方知衡/风景/*.png"
            ]
        }
    }
    
    def __init__(self, llm=None, character=None):
        self.llm = llm
        self.graph = None
        self.selected_character = character or "穆昭"  # 默认角色
        self.character_profile = ""  # 存储角色人设
        
        # 加载角色人设
        self._load_character_profile()

        self.current_config = {
            'batch_size': 5,  # 每批处理的图片数量
            'csv_output': {
                'enabled': True,
                'output_dir': 'workspace/image_recognition_output',
                'filename': 'image_recognition_results.csv',
                'encoding': 'utf-8-sig'  # 支持中文的CSV编码
            }
        }
    
    def _load_character_profile(self):
        """加载角色人设文件"""
        try:
            profile_file = f"workspace/input/docs/基础人设_{self.selected_character}.txt"
            if os.path.exists(profile_file):
                with open(profile_file, 'r', encoding='utf-8') as f:
                    self.character_profile = f.read()
                logger.info(f"已加载{self.selected_character}的人设文件")
            else:
                logger.warning(f"未找到{self.selected_character}的人设文件: {profile_file}")
                self.character_profile = ""
        except Exception as e:
            logger.error(f"加载{self.selected_character}人设文件失败: {e}")
            self.character_profile = ""
    
    def get_character_profile(self) -> str:
        """获取当前角色的人设信息"""
        return self.character_profile
    
    def update_config(self, config_updates: Dict[str, Any]):
        """更新工作流配置"""
        self.current_config.update(config_updates)
    
    def set_character(self, character: str):
        """设置当前角色"""
        if character in self.CHARACTER_CONFIGS:
            self.selected_character = character
            # 重新加载角色人设
            self._load_character_profile()
            # 更新输出文件名包含角色标识
            self.current_config['csv_output']['filename'] = f'image_recognition_{character}_results.csv'
            return True
        return False
    
    def get_character_config(self, character: str = None) -> Dict[str, Any]:
        """获取角色配置"""
        char = character or self.selected_character
        return self.CHARACTER_CONFIGS.get(char, self.CHARACTER_CONFIGS["穆昭"])
    
    def get_available_characters(self) -> List[str]:
        """获取可用角色列表"""
        return list(self.CHARACTER_CONFIGS.keys())
    
    def get_character_scan_patterns(self, character: str = None) -> List[str]:
        """获取角色的图片扫描模式"""
        config = self.get_character_config(character)
        return config.get("scan_patterns", [])
    
    def classify_image_path(self, image_path: str, character: str = None) -> str:
        """根据图片路径和角色进行分类"""
        char = character or self.selected_character
        config = self.get_character_config(char)
        image_path_lower = image_path.lower()
        
        # 检查是否在当前角色的目录下
        if config["base_path"].lower() in image_path_lower:
            # 对于穆昭角色，需要特殊处理美食子分类（按最长匹配原则）
            if char == "穆昭" and "美食" in image_path_lower:
                # 优先匹配子分类
                if "下午茶" in image_path_lower:
                    return "109"
                elif "主食" in image_path_lower:
                    return "110"
                elif "做饭" in image_path_lower:
                    return "111"
                else:
                    return "112"  # 美食-其他
            
            # 遍历角色的分类配置（按长度排序，优先匹配长的分类名）
            sorted_categories = sorted(config["categories"].items(), key=lambda x: len(x[0]), reverse=True)
            for category, code in sorted_categories:
                if category.lower() in image_path_lower:
                    return code
            
            # 如果没有匹配到具体分类，返回通用分类
            return config["categories"].get("通用", "000")
        
        # 如果不在当前角色目录下，检查其他角色
        for other_char, other_config in self.CHARACTER_CONFIGS.items():
            if other_config["base_path"].lower() in image_path_lower:
                # 同样需要特殊处理穆昭的美食分类
                if other_char == "穆昭" and "美食" in image_path_lower:
                    if "下午茶" in image_path_lower:
                        return "109"
                    elif "主食" in image_path_lower:
                        return "110"
                    elif "做饭" in image_path_lower:
                        return "111"
                    else:
                        return "112"
                
                sorted_categories = sorted(other_config["categories"].items(), key=lambda x: len(x[0]), reverse=True)
                for category, code in sorted_categories:
                    if category.lower() in image_path_lower:
                        return code
                return other_config["categories"].get("通用", "000")
        
        # 默认返回通用分类
        return "000"
    
    async def create_image_recognition_graph(self) -> StateGraph:
        """创建图片识别工作流图"""
        self.graph = StateGraph(name="image_recognition_workflow")
        
        # 创建节点
        image_loading_node = ImageLoadingNode()  # 图片加载和预处理节点
        recognition_node = ImageRecognitionNode()  # 图片识别节点
        save_result_node = ResultSaveNode()  # 结果保存节点
        story_generation_node = StoryGenerationNode()  # 故事生成节点
        
        # 添加节点到图
        self.graph.add_node("image_loading", image_loading_node)
        self.graph.add_node("image_recognition", recognition_node)
        self.graph.add_node("save_result", save_result_node)
        self.graph.add_node("story_generation", story_generation_node)
        
        # 定义节点连接关系
        self.graph.add_edge("image_loading", "image_recognition")
        self.graph.add_edge("image_recognition", "save_result")
        self.graph.add_edge("save_result", "story_generation")
        
        # 新增条件边：如果尚未完成全部批次，则回到图片加载节点
        def loop_condition(state):
            """当尚未完成全部批次时继续循环，否则结束"""
            # 检查是否已完成所有图片处理
            if state.get('recognition_complete', False):
                print("🔄 循环条件: recognition_complete=True, 结束处理")
                return "__end__"
            
            # 检查是否有图片需要处理
            images = state.get('images', [])
            current_batch_index = state.get('current_batch_index', 0)
            batch_size = state.get('config', {}).get('batch_size', 5)
            
            # 如果没有图片或所有图片已处理完，直接结束
            if not images or current_batch_index * batch_size >= len(images):
                print(f"🔄 循环条件: 图片处理完毕 - 当前批次:{current_batch_index}, 批次大小:{batch_size}, 图片总数:{len(images)}")
                print(f"🔄 循环条件: {current_batch_index} * {batch_size} = {current_batch_index * batch_size} >= {len(images)} = {current_batch_index * batch_size >= len(images)}")
                return "__end__"
            
            print(f"🔄 循环条件: 继续处理 - 当前批次:{current_batch_index}, 批次大小:{batch_size}, 图片总数:{len(images)}")
            return "image_loading"
        
        self.graph.add_conditional_edges("story_generation", loop_condition)
        
        # 设置入口点
        self.graph.set_entry_point("image_loading")
        
        return self.graph
    
    async def execute_workflow_stream(self, config: Dict[str, Any], workflow_chat, images=None):
        """流式执行图片识别工作流"""
        try:
            # 准备初始输入
            initial_input = {
                'config': config,
                'workflow_chat': workflow_chat,
                'llm': self.llm,
                'workflow_instance': self,  # 传递工作流实例
                'images': images or [],  # 图片路径列表
                'current_batch_index': 0,
                'recognition_complete': False
            }
            
            # 创建并编译图工作流
            if not self.graph:
                await self.create_image_recognition_graph()
            
            compiled_graph = self.graph.compile()
            
            # 使用图的流式执行
            async for stream_event in compiled_graph.stream(initial_input):
                event_type = stream_event.get('type')
                node_name = stream_event.get('node')
                
                if event_type == 'start':
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        "图片识别工作流开始执行...",
                        False
                    )
                
                elif event_type == 'node_start':
                    node_display_name = self._get_node_display_name(node_name)
                    workflow_chat.current_node = self._get_node_id(node_name)
                    
                    await workflow_chat.add_node_message(
                        node_display_name,
                        "开始执行...",
                        "progress"
                    )
                    
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        f"{node_display_name}开始执行...",
                        False
                    )
                
                elif event_type == 'node_streaming':
                    intermediate_result = stream_event.get('intermediate_result')
                    if intermediate_result and intermediate_result.state_update:
                        image_count = 0
                        for key in ['loaded_images', 'recognition_results']:
                            if key in intermediate_result.state_update:
                                if isinstance(intermediate_result.state_update[key], list):
                                    image_count = len(intermediate_result.state_update[key])
                                break
                        
                        if image_count > 0:
                            node_display_name = self._get_node_display_name(node_name)
                            await workflow_chat.add_node_message(
                                node_display_name,
                                f"正在处理图片... 当前数量: {image_count}",
                                "streaming"
                            )
                            
                            yield (
                                workflow_chat._create_workflow_progress(),
                                "",
                                f"正在处理图片... 当前数量: {image_count}",
                                False
                            )
                
                elif event_type == 'node_complete':
                    node_display_name = self._get_node_display_name(node_name)
                    
                    if node_name == 'image_recognition':
                        result_content = "✅ 图片识别完成"
                        if 'recognition_results' in stream_event.get('output', {}):
                            results = stream_event['output']['recognition_results']
                            if isinstance(results, list):
                                result_content = f"✅ 已成功识别{len(results)}张图片"
                    else:
                        result_content = "✅ 执行完成"
                        
                    await workflow_chat.add_node_message(
                        node_display_name,
                        result_content,
                        "completed"
                    )
                    
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        f"{node_display_name}执行完成",
                        False
                    )
                
                elif event_type == 'node_error':
                    error_msg = stream_event.get('error', '未知错误')
                    node_display_name = self._get_node_display_name(node_name)
                    
                    await workflow_chat.add_node_message(
                        node_display_name,
                        f"执行失败: {error_msg}",
                        "error"
                    )
                    
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        "",
                        False
                    )
                
                elif event_type == 'final':
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        "图片识别工作流执行完成",
                        False
                    )
                
                else:
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        "图片识别工作流执行中...",
                        False
                    )
                
        except Exception as e:
            logger.error(f"图片识别工作流流式执行失败: {e}")
            await workflow_chat.add_node_message(
                "系统",
                f"工作流执行失败: {str(e)}",
                "error"
            )
            yield (
                workflow_chat._create_workflow_progress(),
                "",
                "",
                False
            )
    
    def _get_node_display_name(self, node_name: str) -> str:
        """获取节点显示名称"""
        name_mapping = {
            'image_loading': '图片加载',
            'image_recognition': '图片识别',
            'save_result': '结果保存',
            'story_generation': '故事生成'
        }
        return name_mapping.get(node_name, node_name)
    
    def _get_node_id(self, node_name: str) -> str:
        """获取节点ID"""
        id_mapping = {
            'image_loading': 'loading',
            'image_recognition': 'recognition',
            'save_result': 'save',
            'story_generation': 'story'
        }
        return id_mapping.get(node_name, node_name)


class ImageLoadingNode(BaseNode):
    """图片加载和预处理节点 - 加载图片并进行预处理"""
    
    def __init__(self):
        super().__init__(name="image_loading", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行图片加载节点"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行图片加载节点"""
        print("📷 开始加载和预处理图片...")
        
        workflow_chat = input_data.get('workflow_chat')
        images = input_data.get('images', [])
        current_batch_index = input_data.get('current_batch_index', 0)
        batch_size = input_data.get('config', {}).get('batch_size', 5)
        
        if not images or current_batch_index * batch_size >= len(images):
            # 所有图片已处理完毕
            output_data = input_data.copy()
            output_data['recognition_complete'] = True
            output_data['loaded_images'] = []
            
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "图片加载",
                    "✅ 所有图片已处理完成",
                    "success"
                )
            
            yield output_data
            return
        
        # 计算当前批次的图片索引范围
        start_idx = current_batch_index * batch_size
        end_idx = min(start_idx + batch_size, len(images))
        current_batch_images = images[start_idx:end_idx]
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "图片加载",
                f"正在加载第 {current_batch_index + 1} 批次，共 {len(current_batch_images)} 张图片...",
                "progress"
            )
        
        # 加载和预处理图片
        loaded_images = []
        for img_idx, img_path in enumerate(current_batch_images):
            try:
                # 处理特殊文件名（以@开头的文件名）
                actual_path = img_path
                if img_path.startswith('@'):
                    # 检查当前目录是否有该文件
                    if os.path.exists(img_path):
                        actual_path = img_path
                    else:
                        # 尝试在各个可能的目录下查找
                        possible_paths = [
                            # 当前目录
                            img_path,
                            # 去掉@的文件名
                            img_path[1:],
                            # workspace/input目录
                            os.path.join('workspace', 'input', img_path),
                            os.path.join('workspace', 'input', img_path[1:]),
                            # workspace/input/穆昭/各类目录
                            os.path.join('workspace', 'input', '穆昭', '交通工具', img_path),
                            os.path.join('workspace', 'input', '穆昭', '交通工具', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '做手工', img_path),
                            os.path.join('workspace', 'input', '穆昭', '做手工', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '娱乐', img_path),
                            os.path.join('workspace', 'input', '穆昭', '娱乐', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '学习', img_path),
                            os.path.join('workspace', 'input', '穆昭', '学习', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '宠物', img_path),
                            os.path.join('workspace', 'input', '穆昭', '宠物', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '工作', img_path),
                            os.path.join('workspace', 'input', '穆昭', '工作', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '植物', img_path),
                            os.path.join('workspace', 'input', '穆昭', '植物', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '生病吃药', img_path),
                            os.path.join('workspace', 'input', '穆昭', '生病吃药', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '美食', img_path),
                            os.path.join('workspace', 'input', '穆昭', '美食', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '美食', '下午茶', img_path),
                            os.path.join('workspace', 'input', '穆昭', '美食', '下午茶', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '美食', '主食', img_path),
                            os.path.join('workspace', 'input', '穆昭', '美食', '主食', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '美食', '做饭', img_path),
                            os.path.join('workspace', 'input', '穆昭', '美食', '做饭', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '节日', img_path),
                            os.path.join('workspace', 'input', '穆昭', '节日', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '购物', img_path),
                            os.path.join('workspace', 'input', '穆昭', '购物', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '运动', img_path),
                            os.path.join('workspace', 'input', '穆昭', '运动', img_path[1:]),
                            os.path.join('workspace', 'input', '穆昭', '风景', img_path),
                            os.path.join('workspace', 'input', '穆昭', '风景', img_path[1:]),
                            # 其他可能的目录
                            os.path.join('.', img_path),
                            os.path.join('.', img_path[1:])
                        ]
                        
                        # 寻找第一个存在的文件路径
                        for path in possible_paths:
                            if os.path.exists(path):
                                actual_path = path
                                logger.info(f"找到图片文件: {path}")
                                break
                
                # 检查文件是否存在
                if not os.path.exists(actual_path):
                    logger.warning(f"图片文件不存在: {img_path}，跳过处理")
                    continue
                
                # 读取图片文件并进行Base64编码
                with open(actual_path, "rb") as img_file:
                    img_data = img_file.read()
                    base64_img = base64.b64encode(img_data).decode("utf-8")
                
                # 获取文件信息
                img_name = os.path.basename(img_path)
                img_size = len(img_data)  # 使用文件内容大小而不是文件大小
                img_ext = os.path.splitext(img_path)[1].lower()
                if not img_ext:  # 如果没有扩展名，根据文件头推断
                    if img_data.startswith(b'\x89PNG'):
                        img_ext = '.png'
                    elif img_data.startswith(b'\xff\xd8'):
                        img_ext = '.jpg'
                    else:
                        img_ext = '.png'  # 默认为PNG
                
                # 确定MIME类型
                mime_type = "image/jpeg"  # 默认值
                if img_ext == ".png":
                    mime_type = "image/png"
                elif img_ext == ".gif":
                    mime_type = "image/gif"
                elif img_ext in [".jpg", ".jpeg"]:
                    mime_type = "image/jpeg"
                elif img_ext in [".webp"]:
                    mime_type = "image/webp"
                
                loaded_images.append({
                    "image_path": actual_path,  # 直接使用完整路径
                    "image_name": img_name,
                    "base64_data": base64_img,
                    "mime_type": mime_type,
                    "file_size": img_size,
                    "batch_index": current_batch_index,
                    "image_index": img_idx
                })
                
                logger.info(f"成功加载图片: {img_name} ({img_size} 字节)")
                
            except Exception as e:
                logger.error(f"加载图片失败 ({img_path}): {e}")
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "图片加载",
                f"✅ 已成功加载 {len(loaded_images)} 张图片",
                "success"
            )
        
        # 构建输出数据
        output_data = input_data.copy()
        output_data['loaded_images'] = loaded_images
        output_data['current_batch_index'] = current_batch_index + 1
        
        # 添加调试信息
        total_images = len(images)
        processed_count = (current_batch_index + 1) * batch_size
        logger.info(f"✅ 第 {current_batch_index + 1} 批次图片加载完成，共 {len(loaded_images)} 张")
        logger.info(f"📊 进度: {min(processed_count, total_images)}/{total_images} 张图片")
        
        yield output_data


class ImageRecognitionNode(BaseNode):
    """图片识别节点 - 使用DoubaoLLM分析图片内容"""
    
    def __init__(self):
        super().__init__(name="image_recognition", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行图片识别节点"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行图片识别节点"""
        print("🔍 开始图片识别...")
        
        workflow_chat = input_data.get('workflow_chat')
        llm = input_data.get('llm')
        loaded_images = input_data.get('loaded_images', [])
        
        if not loaded_images:
            # 没有图片需要处理，直接返回
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "图片识别",
                    "⚠️ 没有图片需要处理",
                    "warning"
                )
            
            output_data = input_data.copy()
            output_data['recognition_results'] = []
            yield output_data
            return
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "图片识别",
                f"正在识别 {len(loaded_images)} 张图片...",
                "progress"
            )
        
        # 处理每张图片
        recognition_results = []
        for img_idx, img_data in enumerate(loaded_images):
            try:
                # 检查是否有LLM
                if not llm:
                    raise Exception("LLM未初始化")
                
                # 构建图片识别提示词
                system_prompt = """
你是一个专业的图片识别助手，擅长分析图片内容并生成准确的标题和详细描述。
请根据提供的图片内容，完成以下任务：
1. 生成一个简短而精确的标题（5-10个字）
2. 提供详细的图片内容描述（100-150字）

输出格式要求：JSON格式，包含以下字段：
- title: 图片标题
- description: 详细描述

请确保输出为严格的JSON格式，禁止输出任何其他内容。
示例：
{
  "title": "公园灰猫",
  "description": "在秋日公园拍摄的照片，画面中一只银灰色短毛猫正蹲坐在人行道上，好奇地用爪子触碰一片枯黄的落叶。背景是公园入口处的绿色拱门和标识牌，周围环绕着多棵落叶树木，树叶呈现金黄色调。阳光透过树叶形成柔和的光影效果，整个场景充满宁静祥和的秋日氛围。猫咪的绿色眼睛和警觉的姿态与周围环境形成了鲜明对比。"
}


"""
                # 构建用户消息 - 这里我们需要扩展消息类来支持图片
                # 因为当前Message类不支持直接包含图片，我们将base64图片数据放在元数据中
                
                user_message = Message(
                    role=MessageRole.USER,
                    content="请分析这张图片，提供标题和详细描述。",
                    metadata={
                        "has_image": True,
                        "image_data": img_data["base64_data"],
                        "image_mime": img_data["mime_type"]
                    }
                )
                
                # 构建消息列表
                messages = [
                    Message(role=MessageRole.SYSTEM, content=system_prompt),
                    user_message
                ]
                
                # 修改doubao_llm的_convert_messages方法以支持图片
                # 这是一个monkey patch，实际应该在LLM类中实现
                original_convert_messages = llm._convert_messages
                
                def patched_convert_messages(messages_list):
                    """添加对图片的支持"""
                    converted = []
                    for msg in messages_list:
                        role = "user" if msg.role == MessageRole.USER else "assistant"
                        if msg.role == MessageRole.SYSTEM:
                            role = "system"
                        
                        # 检查是否有图片
                        if msg.metadata and msg.metadata.get("has_image"):
                            # 添加图片内容
                            converted.append({
                                "role": role,
                                "content": [
                                    {"type": "text", "text": msg.content},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:{msg.metadata.get('image_mime', 'image/jpeg')};base64,{msg.metadata.get('image_data')}",
                                        }
                                    }
                                ]
                            })
                        else:
                            # 普通文本消息
                            converted.append({
                                "role": role,
                                "content": msg.content
                            })
                    
                    return converted
                
                # 应用monkey patch
                llm._convert_messages = patched_convert_messages
                
                # 调用LLM进行图片识别
                logger.info(f"开始识别图片: {img_data['image_name']}")
                
                try:
                    # 更新模型名称为支持多模态的模型
                    original_model = llm.config.model_name
                    # 使用环境变量中的多模态模型名称，如果不存在则使用默认值
                    vision_model = os.getenv('DOUBAO_MODEL_VISION_PRO', 'ep-20250704095927-j6t2g')
                    llm.config.model_name = vision_model
                    
                    logger.info(f"使用多模态模型: {vision_model}")
                    
                    # 调用LLM
                    response = await llm.generate(
                        messages,
                        temperature=0.7,
                        max_tokens=4096,
                        mode="normal"
                    )

                    print(f"图片识别结果: {response.content}")
                    # 恢复原始模型名称
                    llm.config.model_name = original_model
                    
                    # 恢复原始方法
                    llm._convert_messages = original_convert_messages
                    
                    # 解析结果
                    content = response.content
                    
                    # 从回复中提取JSON
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                    
                    if json_match:
                        json_str = json_match.group(1)
                    else:
                        # 尝试找到大括号包围的JSON
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            json_str = json_match.group(0)
                        else:
                            json_str = content
                    
                    # 解析JSON
                    try:
                        result_data = json.loads(json_str.strip())
                    except json.JSONDecodeError:
                        logger.warning(f"JSON解析失败，使用原始回复")
                        result_data = {
                            "title": "无法解析结果",
                            "description": content
                        }
                    
                    # 添加图片信息
                    result_data["image_name"] = img_data["image_name"]
                    result_data["image_path"] = img_data["image_path"]  # 统一使用完整路径
                    
                    recognition_results.append(result_data)
                    logger.info(f"图片识别成功: {img_data['image_name']}")
                    
                except Exception as e:
                    logger.error(f"LLM调用失败: {e}")
                    # 添加错误结果
                    recognition_results.append({
                        "image_name": img_data["image_name"],
                        "image_path": img_data["image_path"],  # 统一使用完整路径
                        "title": "识别失败",
                        "description": f"图片识别过程中出错: {str(e)}",
                        "error": str(e)
                    })
                
            except Exception as e:
                logger.error(f"图片识别失败: {e}")
                recognition_results.append({
                    "image_name": img_data["image_name"] if "image_name" in img_data else "未知图片",
                    "image_path": img_data.get("image_path", "未知路径"),  # 统一使用完整路径
                    "title": "处理错误",
                    "description": f"图片处理过程中出错: {str(e)}",
                    "error": str(e)
                })
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "图片识别",
                f"✅ 已成功识别 {len(recognition_results)} 张图片",
                "success"
            )
        
        # 输出结果
        output_data = input_data.copy()
        output_data['recognition_results'] = recognition_results
        
        logger.info(f"✅ 图片识别完成，共 {len(recognition_results)} 张")
        yield output_data


class ResultSaveNode(BaseNode):
    """结果保存节点 - 将识别结果保存到CSV"""
    
    def __init__(self):
        super().__init__(name="result_save", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行结果保存节点"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行结果保存节点"""
        print("💾 开始保存识别结果...")
        
        workflow_chat = input_data.get('workflow_chat')
        recognition_results = input_data.get('recognition_results', [])
        config = input_data.get('config', {})
        
        if not recognition_results:
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "结果保存",
                    "⚠️ 没有结果需要保存",
                    "warning"
                )
            yield input_data
            return
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "结果保存",
                f"正在保存{len(recognition_results)}条识别结果...",
                "progress"
            )
        
        # 保存到CSV文件
        csv_save_result = await self._save_to_csv(recognition_results, config, workflow_chat, input_data)
        
        # 构建最终输出
        output_data = input_data.copy()
        output_data.update({
            'csv_save_result': csv_save_result,
            'save_success': csv_save_result.get('success', False),
            'save_message': csv_save_result.get('message', '保存完成')
        })
        
        yield output_data
    
    async def _save_to_csv(self, recognition_results: List[Dict], config: Dict, workflow_chat=None, input_data=None) -> Dict:
        """保存识别结果到CSV文件"""
        try:
            import csv
            from datetime import datetime
            
            # 获取CSV配置
            csv_config = config.get('csv_output', {})
            output_dir = csv_config.get('output_dir', 'workspace/image_recognition_output')
            filename = csv_config.get('filename', 'image_recognition_results.csv')
            encoding = csv_config.get('encoding', 'utf-8-sig')
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # CSV文件路径
            csv_file = os.path.join(output_dir, filename)
            
            # 检查文件是否存在，决定是否写入表头
            file_exists = os.path.exists(csv_file)
            
            # 加载ID注册表
            registry = self._load_id_registry()
            
            # 写入CSV文件（追加模式）
            with open(csv_file, 'a', newline='', encoding=encoding) as f:
                # 使用新的字段格式
                fieldnames = ['序号ID', '图片名称', '图片路径', '图片标题', '图片描述', '关键词', '故事内容']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # 如果文件不存在，先写入表头
                if not file_exists:
                    writer.writeheader()
                
                # 写入当前批次的识别结果
                for result in recognition_results:
                    # 从输入数据获取工作流实例
                    workflow_instance = input_data.get('workflow_instance')
                    if workflow_instance:
                        # 使用工作流实例的分类方法，使用完整路径进行分类
                        image_path = result.get('image_path', '')
                        category_code = workflow_instance.classify_image_path(image_path)
                        print(f"🔍 分类调试: {result.get('image_name', '')} -> 完整路径: {image_path} -> 分类代码: {category_code}")
                        logger.info(f"分类调试: {result.get('image_name', '')} -> 完整路径: {image_path} -> 分类代码: {category_code}")
                    else:
                        # 降级到本地分类方法
                        image_path = result.get('image_path', '')
                        category_code = self._classify_image_path(image_path)
                        print(f"🔍 分类调试(本地): {result.get('image_name', '')} -> 完整路径: {image_path} -> 分类代码: {category_code}")
                        logger.info(f"分类调试(本地): {result.get('image_name', '')} -> 完整路径: {image_path} -> 分类代码: {category_code}")
                    
                    unique_id = self._generate_unique_id(category_code, registry)
                    print(f"🏷️ 编号生成: {result.get('image_name', '')} -> 分类代码: {category_code} -> 唯一ID: {unique_id}")
                    logger.info(f"编号生成: {result.get('image_name', '')} -> 分类代码: {category_code} -> 唯一ID: {unique_id}")
                    
                    writer.writerow({
                        '序号ID': unique_id,
                        '图片名称': result.get('image_name', ''),
                        '图片路径': result.get('image_path', ''),  # 直接使用完整路径
                        '图片标题': result.get('title', ''),
                        '图片描述': result.get('description', ''),
                        '关键词': '',  # 暂时留空，由故事生成节点填充
                        '故事内容': ''  # 留空，后续由故事生成节点填充
                    })
            
            # 保存更新后的ID注册表（根据配置决定是否保存）
            config = input_data.get('config', {})
            save_ids = config.get('save_ids', True)
            if save_ids:
                self._save_id_registry(registry)
                logger.info("✅ ID注册表已更新并保存")
            else:
                logger.info("⚠️ 根据用户配置，跳过ID注册表保存")
            
            if workflow_chat:
                save_message = "✅ 已保存编号状态" if save_ids else "⚠️ 未保存编号状态（用户选择）"
                await workflow_chat.add_node_message(
                    "结果保存",
                    f"✅ {len(recognition_results)}条识别结果已保存到CSV文件，{save_message}",
                    "success"
                )
            
            logger.info(f"✅ CSV保存完成：{len(recognition_results)}条识别结果保存到 {csv_file}")
            
            return {
                'success': True,
                'message': f"成功保存{len(recognition_results)}条识别结果",
                'count': len(recognition_results),
                'file_path': csv_file
            }
            
        except Exception as e:
            logger.error(f"CSV保存失败: {e}")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "结果保存",
                    f"❌ CSV保存失败: {str(e)}",
                    "error"
                )
            
            return {
                'success': False,
                'message': f"保存失败: {str(e)}",
                'error': str(e)
            }

    def _load_id_registry(self):
        """加载ID注册表"""
        registry_file = "id_registry.json"
        
        if os.path.exists(registry_file):
            try:
                import json
                with open(registry_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载ID注册表失败: {e}")
        
        # 返回默认结构
        from datetime import datetime
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
                # 方知衡100新增分类，延续200系列
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

    def _save_id_registry(self, registry):
        """保存ID注册表"""
        registry_file = "id_registry.json"
        from datetime import datetime
        registry["last_update"] = datetime.now().isoformat()
        
        try:
            import json
            with open(registry_file, 'w', encoding='utf-8') as f:
                json.dump(registry, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存ID注册表失败: {e}")
            return False

    def _classify_image_path(self, image_path):
        """根据图片路径进行分类"""
        image_path_lower = image_path.lower()
        
        # 方知衡相关分类映射
        if "方知衡" in image_path_lower:
            if "动物修" in image_path_lower:
                return "203"  # 方知衡-动物修
            elif "美食修" in image_path_lower:
                return "202"  # 方知衡-美食修
            elif "风景修" in image_path_lower:
                return "201"  # 方知衡-风景修
            # 新增的方知衡类别
            elif "动物" in image_path_lower:
                return "204"  # 方知衡-动物
            elif "在干嘛" in image_path_lower:
                return "205"  # 方知衡-在干嘛
            elif "工作" in image_path_lower:
                return "206"  # 方知衡-工作
            elif "植物" in image_path_lower:
                return "207"  # 方知衡-植物
            elif "生活2" in image_path_lower:
                return "209"  # 方知衡-生活2
            elif "生活" in image_path_lower:
                return "208"  # 方知衡-生活
            elif "美食" in image_path_lower:
                return "210"  # 方知衡-美食
            elif "节日" in image_path_lower:
                return "211"  # 方知衡-节日
            elif "风景" in image_path_lower:
                return "212"  # 方知衡-风景
            elif "通用" in image_path_lower:
                return "200"  # 方知衡-通用
            else:
                return "200"  # 方知衡-默认通用
        
        # 穆昭相关分类映射
        elif "穆昭" in image_path_lower:
            if "交通工具" in image_path_lower:
                return "101"  # 穆昭-交通工具
            elif "做手工" in image_path_lower:
                return "102"  # 穆昭-做手工
            elif "娱乐" in image_path_lower:
                return "103"  # 穆昭-娱乐
            elif "学习" in image_path_lower:
                return "104"  # 穆昭-学习
            elif "宠物" in image_path_lower:
                return "105"  # 穆昭-宠物
            elif "工作" in image_path_lower:
                return "106"  # 穆昭-工作
            elif "植物" in image_path_lower:
                return "107"  # 穆昭-植物
            elif "生病吃药" in image_path_lower:
                return "108"  # 穆昭-生病吃药
            elif "美食" in image_path_lower:
                if "下午茶" in image_path_lower:
                    return "109"  # 穆昭-美食-下午茶
                elif "主食" in image_path_lower:
                    return "110"  # 穆昭-美食-主食
                elif "做饭" in image_path_lower:
                    return "111"  # 穆昭-美食-做饭
                else:
                    return "112"  # 穆昭-美食-其他
            elif "节日" in image_path_lower:
                return "113"  # 穆昭-节日
            elif "购物" in image_path_lower:
                return "114"  # 穆昭-购物
            elif "运动" in image_path_lower:
                return "115"  # 穆昭-运动
            elif "风景" in image_path_lower:
                return "116"  # 穆昭-风景
            else:
                return "100"  # 穆昭-通用
        
        # 原有的对话日常图片分类映射
        elif "风景修" in image_path_lower:
            return "001"
        elif "美食修" in image_path_lower:
            return "002"
        elif "动物修" in image_path_lower:
            return "003"
        elif "通用" in image_path_lower:
            return "000"
        else:
            # 默认分类为通用
            return "000"

    def _generate_unique_id(self, category_code, registry):
        """生成分类独立的唯一ID"""
        # 确保分类计数器存在
        if "category_counters" not in registry:
            registry["category_counters"] = {
                # 通用分类
                "000": 0,  # 通用
                # 方知衡分类 (200系列)
                "200": 0,  # 方知衡-通用  
                "201": 0,  # 方知衡-风景修
                "202": 0,  # 方知衡-美食修
                "203": 0,  # 方知衡-动物修
                # 方知衡100新增分类，延续200系列
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
            }
        
        # 如果当前分类不存在，初始化为0
        if category_code not in registry["category_counters"]:
            registry["category_counters"][category_code] = 0
        
        # 递增分类计数器
        registry["category_counters"][category_code] += 1
        sequence_num = f"{registry['category_counters'][category_code]:04d}"
        unique_id = f"99{category_code}{sequence_num}"
        
        # 检查是否已存在（保险起见）
        while unique_id in registry["used_ids"]:
            registry["category_counters"][category_code] += 1
            sequence_num = f"{registry['category_counters'][category_code]:04d}"
            unique_id = f"99{category_code}{sequence_num}"
            
            # 防止无限循环
            if registry["category_counters"][category_code] >= 9999:
                raise ValueError(f"类别 {category_code} 序号已达到上限（9999）")
        
        registry["used_ids"].append(unique_id)
        return unique_id


if __name__ == "__main__":
    """直接运行此文件处理图片"""
    import asyncio
    import sys
    import glob
    
    print("🖼️ 图片识别工作流")
    print("=" * 60)
    
    # 简单的模拟聊天界面
    class MockWorkflowChat:
        def __init__(self):
            self.current_node = ""
        
        async def add_node_message(self, node_name: str, message: str, status: str):
            print(f"[{node_name}] {status}: {message}")
        
        def _create_workflow_progress(self):
            return "<div>工作流进度</div>"
    
    async def main():
        try:
            # 显示欢迎信息
            print("🖼️ 图片识别工作流")
            print("=" * 60)
            
            # 创建工作流实例来获取可用角色
            temp_workflow = ImageRecognitionWorkflow()
            available_characters = temp_workflow.get_available_characters()
            
            # 让用户选择角色
            print("📋 请选择要处理的角色:")
            for i, char in enumerate(available_characters, 1):
                char_config = temp_workflow.get_character_config(char)
                print(f"  {i}. {char_config['display_name']} ({char_config['base_path']})")
            
            while True:
                try:
                    choice = input(f"\n请输入选择 (1-{len(available_characters)}): ").strip()
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(available_characters):
                        selected_character = available_characters[choice_idx]
                        break
                    else:
                        print(f"❌ 请输入1到{len(available_characters)}之间的数字")
                except ValueError:
                    print("❌ 请输入有效的数字")
                except KeyboardInterrupt:
                    print("\n👋 已取消操作")
                    return
            
            print(f"\n✅ 已选择角色: {selected_character}")
            char_config = temp_workflow.get_character_config(selected_character)
            print(f"📁 图片目录: {char_config['base_path']}")
            print(f"🏷️ 分类数量: {len(char_config['categories'])}")
            
            # 配置LLM
            from llm.doubao import DoubaoLLM
            from core.types import LLMConfig
            
            # 使用环境变量获取模型名称和API密钥
            vision_model = os.getenv('DOUBAO_MODEL_VISION_PRO_', 'ep-20250704095927-j6t2g')
            api_key = os.getenv('ARK_API_KEY', "b633a622-b5d0-4f16-a8a9-616239cf15d1")
            
            # 创建LLM配置
            llm_config = LLMConfig(
                provider="doubao",
                model_name=vision_model,
                api_key=api_key.strip(),
                api_base="https://ark.cn-beijing.volces.com/api/v3"
            )
            llm = DoubaoLLM(config=llm_config)
            print(f"✅ LLM配置成功，使用模型: {vision_model}")
            
            # 初始化工作流并设置角色
            workflow = ImageRecognitionWorkflow(llm=llm, character=selected_character)
            print(f"✅ 图片识别工作流初始化完成，当前角色: {selected_character}")
            
            # 自动扫描图片
            image_paths = []
            scan_patterns = workflow.get_character_scan_patterns()
            
            print(f"\n🔍 扫描 {selected_character} 的图片文件...")
            for pattern in scan_patterns:
                images = glob.glob(pattern)
                image_paths.extend(images)
            
            if not image_paths:
                print(f"⚠️ 在 {char_config['base_path']} 中未找到图片文件")
                return
            
            print(f"🖼️ 发现图片数量: {len(image_paths)}")
            
            # 显示当前编号状态
            print(f"\n📊 编号状态预览:")
            # 创建一个临时的ResultSaveNode来获取ID注册表
            temp_save_node = ResultSaveNode()
            registry = temp_save_node._load_id_registry()
            category_counters = registry.get('category_counters', {})
            char_config = workflow.get_character_config(selected_character)
            
            for category, code in sorted(char_config['categories'].items(), key=lambda x: x[1]):
                current_count = category_counters.get(code, 0)
                next_id = f"99{code}{current_count + 1:04d}"
                print(f"  📝 {category} ({code}): 下一个编号 {next_id}")
            
            print(f"💡 提示: 工作流完成后会自动保存编号状态，下次运行时会从这些编号继续")
            
            # 询问是否要重设编号
            reset_choice = input("\n是否要重新设置某个分类的起始编号? (y/N): ").strip().lower()
            if reset_choice in ['y', 'yes', '是']:
                # 显示分类选择菜单
                print("\n📋 请选择要重设编号的分类:")
                categories_list = list(char_config['categories'].items())
                for i, (category, code) in enumerate(categories_list, 1):
                    current_count = category_counters.get(code, 0)
                    print(f"  {i}. {category} ({code}) - 当前计数: {current_count}")
                
                while True:
                    try:
                        category_choice = input(f"\n请选择分类 (1-{len(categories_list)}) 或按回车跳过: ").strip()
                        if not category_choice:
                            break
                        
                        choice_idx = int(category_choice) - 1
                        if 0 <= choice_idx < len(categories_list):
                            selected_category, selected_code = categories_list[choice_idx]
                            current_count = category_counters.get(selected_code, 0)
                            
                            print(f"\n已选择: {selected_category} ({selected_code})")
                            print(f"当前计数: {current_count}")
                            
                            # 输入新的起始编号
                            while True:
                                try:
                                    new_count = input(f"请输入新的起始计数 (当前: {current_count}): ").strip()
                                    if not new_count:
                                        break
                                    
                                    new_count = int(new_count)
                                    if new_count >= 0:
                                        # 更新ID注册表
                                        category_counters[selected_code] = new_count
                                        temp_save_node._save_id_registry(registry)
                                        
                                        next_id = f"99{selected_code}{new_count + 1:04d}"
                                        print(f"✅ 已更新 {selected_category} 的计数为 {new_count}")
                                        print(f"📝 下一个分配的编号将是: {next_id}")
                                        break
                                    else:
                                        print("❌ 请输入非负整数")
                                except ValueError:
                                    print("❌ 请输入有效的数字")
                            break
                        else:
                            print(f"❌ 请输入1到{len(categories_list)}之间的数字")
                    except ValueError:
                        print("❌ 请输入有效的数字")
                    except KeyboardInterrupt:
                        print("\n👋 已取消重设编号")
                        break
            
            # 询问是否保存编号
            save_ids = True  # 默认保存编号
            save_choice = input("\n是否保存编号到ID注册表? (Y/n): ").strip().lower()
            if save_choice in ['n', 'no', '否']:
                save_ids = False
                print("⚠️ 已禁用编号保存，本次运行不会更新ID注册表")
            else:
                print("✅ 已启用编号保存，将更新ID注册表")
            
            # 询问是否继续
            confirm = input("\n是否继续处理这些图片? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes', '是']:
                print("👋 已取消处理")
                return
            
            # 配置
            config = {
                'batch_size': 5,  # 每批处理5张图片，减少循环次数
                'save_ids': save_ids,  # 是否保存编号
                'csv_output': {
                    'enabled': True,
                    'output_dir': 'workspace/image_recognition_output',
                    'filename': f'image_recognition_{selected_character}_results_0815.csv',  # 包含角色标识
                    'encoding': 'utf-8-sig'
                }
            }
            
            # 创建模拟聊天界面
            mock_chat = MockWorkflowChat()
            
            # 创建工作流图
            graph = await workflow.create_image_recognition_graph()
            compiled_graph = graph.compile()
            print("✅ 工作流图创建完成")
            
            # 准备输入数据
            input_data = {
                'config': config,
                'workflow_chat': mock_chat,
                'llm': llm,
                'images': image_paths,
                'current_batch_index': 0
            }
            
            print(f"\n🚀 开始处理{len(image_paths)}张图片...")
            
            # 执行工作流
            final_result = None
            async for result in compiled_graph.stream(input_data):
                if result:
                    final_result = result
            
            print("\n✅ 图片识别工作流执行完成!")
            
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 运行主函数
    asyncio.run(main())

