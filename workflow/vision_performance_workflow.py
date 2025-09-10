"""图片识别性能分析工作流 - 基于豆包/DoubaoLLM的图片识别性能测试系统
提供对多种模型的图片识别性能对比分析，包括耗时统计和Token消耗统计
"""

import json
import asyncio
import base64
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import csv

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.graph import StateGraph
from core.base import BaseNode
from llm.base import LLMFactory
from core.types import LLMConfig, TaskResult, Message, MessageRole

logger = logging.getLogger(__name__)

class VisionPerformanceWorkflow:
    """图片识别性能分析工作流管理器"""
    
    def __init__(self):
        self.graph = None
        self.models = {}

        # 从环境变量获取3种模型配置
        self.model_configs = {
            # 'vision_pro': {
            #     'name': '豆包Vision Pro',
            #     'env_key': 'DOUBAO_MODEL_VISION_PRO',
            #     'default': 'ep-20250704095927-j6t2g'
            # },
            # 'deepseek_r1': {
            #     'name': '豆包1.6',
            #     'env_key': 'DOUBAO_MODEL_1.6', 
            #     'default': 'ep-20250704095927-j6t2g'
            # },
            'deepseek_v3': {
                'name': '豆包1.6 Flash',
                'env_key': 'DOUBAO_MODEL_1.6_FLASH',
                'default': 'ep-20250612122042-t6g56'
            }
        }
        
        self.current_config = {
            'batch_size': 10,  # 每批处理的图片数量
            'test_all_models': True,  # 是否测试所有模型
            'csv_output': {
                'enabled': True,
                'output_dir': 'workspace/vision_performance_output',
                'recognition_filename': 'vision_recognition_results.csv',
                'performance_filename': 'vision_performance_stats.csv',
                'encoding': 'utf-8-sig'
            }
        }
    
    async def initialize_models(self):
        """初始化所有模型"""
        api_key = os.getenv('ARK_API_KEY', "b633a622-b5d0-4f16-a8a9-616239cf15d1")
        api_base = "https://ark.cn-beijing.volces.com/api/v3"
        
        for model_key, config in self.model_configs.items():
            try:
                from llm.doubao import DoubaoLLM
                
                model_name = os.getenv(config['env_key'], config['default'])
                
                llm_config = LLMConfig(
                    provider="doubao",
                    model_name=model_name,
                    api_key=api_key.strip(),
                    api_base=api_base
                )
                
                self.models[model_key] = {
                    'llm': DoubaoLLM(config=llm_config),
                    'name': config['name'],
                    'model_name': model_name
                }
                
                logger.info(f"✅ 初始化模型成功: {config['name']} ({model_name})")
                
            except Exception as e:
                logger.error(f"❌ 初始化模型失败 {config['name']}: {e}")
    
    def update_config(self, config_updates: Dict[str, Any]):
        """更新工作流配置"""
        self.current_config.update(config_updates)
    
    async def create_vision_performance_graph(self) -> StateGraph:
        """创建图片识别性能分析工作流图"""
        self.graph = StateGraph(name="vision_performance_workflow")
        
        # 创建节点
        image_loading_node = ImageLoadingNode()
        performance_test_node = VisionPerformanceTestNode()
        statistics_node = PerformanceStatisticsNode()
        result_save_node = PerformanceResultSaveNode()
        
        # 添加节点到图
        self.graph.add_node("image_loading", image_loading_node)
        self.graph.add_node("performance_test", performance_test_node)
        self.graph.add_node("statistics", statistics_node)
        self.graph.add_node("result_save", result_save_node)
        
        # 定义节点连接关系
        self.graph.add_edge("image_loading", "performance_test")
        self.graph.add_edge("performance_test", "statistics")
        self.graph.add_edge("statistics", "result_save")
        
        # 设置入口点
        self.graph.set_entry_point("image_loading")
        
        return self.graph
    
    async def execute_workflow_stream(self, config: Dict[str, Any], workflow_chat, images=None):
        """流式执行图片识别性能分析工作流"""
        try:
            # 初始化模型
            await self.initialize_models()
            
            # 准备初始输入
            initial_input = {
                'config': config,
                'workflow_chat': workflow_chat,
                'models': self.models,
                'images': images or [],
                'performance_stats': []
            }
            
            # 创建并编译图工作流
            if not self.graph:
                await self.create_vision_performance_graph()
            
            compiled_graph = self.graph.compile()
            
            # 使用图的流式执行
            async for stream_event in compiled_graph.stream(initial_input):
                event_type = stream_event.get('type')
                node_name = stream_event.get('node')
                
                if event_type == 'start':
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        "图片识别性能分析工作流开始执行...",
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
                        # 处理流式更新
                        node_display_name = self._get_node_display_name(node_name)
                        
                        if 'current_model' in intermediate_result.state_update:
                            current_model = intermediate_result.state_update['current_model']
                            await workflow_chat.add_node_message(
                                node_display_name,
                                f"正在测试模型: {current_model}",
                                "streaming"
                            )
                            
                            yield (
                                workflow_chat._create_workflow_progress(),
                                "",
                                f"正在测试模型: {current_model}",
                                False
                            )
                
                elif event_type == 'node_complete':
                    node_display_name = self._get_node_display_name(node_name)
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
                        "图片识别性能分析工作流执行完成",
                        False
                    )
                
                else:
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        "图片识别性能分析工作流执行中...",
                        False
                    )
                
        except Exception as e:
            logger.error(f"图片识别性能分析工作流流式执行失败: {e}")
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
            'performance_test': '性能测试',
            'statistics': '统计分析',
            'result_save': '结果保存'
        }
        return name_mapping.get(node_name, node_name)
    
    def _get_node_id(self, node_name: str) -> str:
        """获取节点ID"""
        id_mapping = {
            'image_loading': 'loading',
            'performance_test': 'testing',
            'statistics': 'stats',
            'result_save': 'save'
        }
        return id_mapping.get(node_name, node_name)


class ImageLoadingNode(BaseNode):
    """图片加载节点"""
    
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
        print("📷 开始加载图片...")
        
        workflow_chat = input_data.get('workflow_chat')
        images = input_data.get('images', [])
        
        if not images:
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "图片加载",
                    "⚠️ 没有图片需要处理",
                    "warning"
                )
            yield input_data
            return
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "图片加载",
                f"正在加载 {len(images)} 张图片...",
                "progress"
            )
        
        # 加载和预处理图片
        loaded_images = []
        for img_idx, img_path in enumerate(images):
            try:
                # 处理特殊文件名（以@开头的文件名）
                actual_path = img_path
                if img_path.startswith('@'):
                    # 尝试在各个可能的目录下查找
                    possible_paths = [
                        img_path,
                        img_path[1:],
                        os.path.join('workspace', 'input', img_path),
                        os.path.join('workspace', 'input', img_path[1:]),
                        os.path.join('workspace', 'input', '方知衡100', '宠物', img_path[1:]),
                        os.path.join('workspace', 'input', '方知衡100', '风景', img_path[1:]),
                        os.path.join('workspace', 'input', '方知衡100', '工作', img_path[1:]),
                        os.path.join('workspace', 'input', '方知衡100', '风景修', img_path[1:])
                    ]
                    
                    for path in possible_paths:
                        if os.path.exists(path):
                            actual_path = path
                            break
                
                if not os.path.exists(actual_path):
                    logger.warning(f"图片文件不存在: {img_path}，跳过处理")
                    continue
                
                # 读取图片文件并进行Base64编码
                with open(actual_path, "rb") as img_file:
                    img_data = img_file.read()
                    base64_img = base64.b64encode(img_data).decode("utf-8")
                
                # 获取文件信息
                img_name = os.path.basename(img_path)
                img_size = len(img_data)
                img_ext = os.path.splitext(img_path)[1].lower()
                
                if not img_ext:
                    if img_data.startswith(b'\x89PNG'):
                        img_ext = '.png'
                    elif img_data.startswith(b'\xff\xd8'):
                        img_ext = '.jpg'
                    else:
                        img_ext = '.png'
                
                # 确定MIME类型
                mime_type = "image/jpeg"
                if img_ext == ".png":
                    mime_type = "image/png"
                elif img_ext == ".gif":
                    mime_type = "image/gif"
                elif img_ext in [".jpg", ".jpeg"]:
                    mime_type = "image/jpeg"
                elif img_ext in [".webp"]:
                    mime_type = "image/webp"
                
                loaded_images.append({
                    "image_path": img_path,
                    "actual_path": actual_path,
                    "image_name": img_name,
                    "base64_data": base64_img,
                    "mime_type": mime_type,
                    "file_size": img_size,
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
        
        logger.info(f"✅ 图片加载完成，共 {len(loaded_images)} 张")
        yield output_data


class VisionPerformanceTestNode(BaseNode):
    """图片识别性能测试节点"""
    
    def __init__(self):
        super().__init__(name="performance_test", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行性能测试节点"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行性能测试节点"""
        print("🔍 开始图片识别性能测试...")
        
        workflow_chat = input_data.get('workflow_chat')
        models = input_data.get('models', {})
        loaded_images = input_data.get('loaded_images', [])
        config = input_data.get('config', {})
        
        if not loaded_images:
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "性能测试",
                    "⚠️ 没有图片需要测试",
                    "warning"
                )
            yield input_data
            return
        
        if not models:
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "性能测试",
                    "❌ 没有可用的模型",
                    "error"
                )
            yield input_data
            return
        
        # 性能测试结果
        all_test_results = []
        
        # 测试每个模型
        for model_key, model_info in models.items():
            model_name = model_info['name']
            llm = model_info['llm']
            
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "性能测试",
                    f"开始测试模型: {model_name}",
                    "progress"
                )
            
            # 为当前模型测试所有图片
            model_results = []
            for img_data in loaded_images:
                try:
                    # 记录开始时间
                    start_time = time.time()
                    
                    # 执行图片识别
                    result = await self._recognize_image_with_stats(llm, img_data, model_info)
                    
                    # 记录结束时间
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    # 添加性能统计信息
                    result.update({
                        'model_key': model_key,
                        'model_name': model_name,
                        'model_id': model_info['model_name'],
                        'duration_seconds': round(duration, 3),
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    model_results.append(result)
                    
                    logger.info(f"模型 {model_name} 识别图片 {img_data['image_name']} 完成，耗时: {duration:.3f}秒")
                    
                except Exception as e:
                    logger.error(f"模型 {model_name} 识别图片 {img_data['image_name']} 失败: {e}")
                    model_results.append({
                        'model_key': model_key,
                        'model_name': model_name,
                        'model_id': model_info['model_name'],
                        'image_name': img_data['image_name'],
                        'image_path': img_data['image_path'],
                        'title': '识别失败',
                        'description': f'错误: {str(e)}',
                        'duration_seconds': 0,
                        'input_tokens': 0,
                        'output_tokens': 0,
                        'total_tokens': 0,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
            
            all_test_results.extend(model_results)
            
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "性能测试",
                    f"✅ 模型 {model_name} 测试完成，处理了 {len(model_results)} 张图片",
                    "success"
                )
        
        # 构建输出数据
        output_data = input_data.copy()
        output_data['test_results'] = all_test_results
        
        logger.info(f"✅ 性能测试完成，共测试了 {len(models)} 个模型，{len(loaded_images)} 张图片")
        yield output_data
    
    async def _recognize_image_with_stats(self, llm, img_data: Dict, model_info: Dict) -> Dict:
        """执行图片识别并收集统计信息"""
        system_prompt = """你是一个专业的图片识别助手，擅长分析图片内容并生成准确的详细描述。
请根据提供的图片内容，提供精确的图片内容描述（100-150字）

输出直接为文本，不输出任何其他内容。
示例：
在秋日公园的照片，画面中一只银灰色短毛猫正蹲坐在人行道上，好奇地用爪子触碰一片枯黄的落叶。背景是公园入口处的绿色拱门和标识牌，周围环绕着多棵落叶树木，树叶呈现金黄色调。阳光透过树叶形成柔和的光影效果，整个场景充满宁静祥和的秋日氛围。
"""
        
        user_message = Message(
            role=MessageRole.USER,
            content="请分析这张图片，提供标题和详细描述。",
            metadata={
                "has_image": True,
                "image_data": img_data["base64_data"],
                "image_mime": img_data["mime_type"]
            }
        )
        
        messages = [
            Message(role=MessageRole.SYSTEM, content=system_prompt),
            user_message
        ]
        
        # Monkey patch支持图片
        original_convert_messages = llm._convert_messages
        
        def patched_convert_messages(messages_list):
            """添加对图片的支持"""
            converted = []
            for msg in messages_list:
                role = "user" if msg.role == MessageRole.USER else "assistant"
                if msg.role == MessageRole.SYSTEM:
                    role = "system"
                
                if msg.metadata and msg.metadata.get("has_image"):
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
                    converted.append({
                        "role": role,
                        "content": msg.content
                    })
            
            return converted
        
        # 应用monkey patch
        llm._convert_messages = patched_convert_messages
        
        try:
            # 调用LLM
            response = await llm.generate(
                messages,
                temperature=0.7,
                max_tokens=4096,
                mode="normal"
            )
            
            # 恢复原始方法
            llm._convert_messages = original_convert_messages
            
            # 解析结果
            content = response.content
            
            # 提取JSON
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = content
            
            try:
                result_data = json.loads(json_str.strip())
            except json.JSONDecodeError:
                result_data = {
                    "title": "解析失败",
                    "description": content
                }
            
            # 从metadata中提取token统计信息
            usage_info = response.metadata.get('usage', {})
            input_tokens = usage_info.get('prompt_tokens', 0)
            output_tokens = usage_info.get('completion_tokens', 0)
            total_tokens = usage_info.get('total_tokens', input_tokens + output_tokens)
            
            # 添加基本信息和Token统计
            result_data.update({
                'image_name': img_data['image_name'],
                'image_path': img_data['image_path'],
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'usage_raw': usage_info  # 保留原始usage信息用于调试
            })
            
            return result_data
            
        except Exception as e:
            # 恢复原始方法
            llm._convert_messages = original_convert_messages
            raise e


class PerformanceStatisticsNode(BaseNode):
    """性能统计分析节点"""
    
    def __init__(self):
        super().__init__(name="statistics", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行统计分析节点"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行统计分析节点"""
        print("📊 开始统计分析...")
        
        workflow_chat = input_data.get('workflow_chat')
        test_results = input_data.get('test_results', [])
        
        if not test_results:
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "统计分析",
                    "⚠️ 没有测试结果需要分析",
                    "warning"
                )
            yield input_data
            return
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "统计分析",
                "正在生成性能统计报告...",
                "progress"
            )
        
        # 按模型分组统计
        model_stats = {}
        for result in test_results:
            model_key = result.get('model_key', 'unknown')
            model_name = result.get('model_name', 'Unknown Model')
            
            if model_key not in model_stats:
                model_stats[model_key] = {
                    'model_name': model_name,
                    'model_id': result.get('model_id', ''),
                    'total_images': 0,
                    'success_count': 0,
                    'error_count': 0,
                    'total_duration': 0,
                    'total_input_tokens': 0,
                    'total_output_tokens': 0,
                    'total_tokens': 0,
                    'durations': [],
                    'token_counts': []
                }
            
            stats = model_stats[model_key]
            stats['total_images'] += 1
            
            if 'error' not in result:
                stats['success_count'] += 1
                stats['total_duration'] += result.get('duration_seconds', 0)
                stats['total_input_tokens'] += result.get('input_tokens', 0)
                stats['total_output_tokens'] += result.get('output_tokens', 0)
                stats['total_tokens'] += result.get('total_tokens', 0)
                stats['durations'].append(result.get('duration_seconds', 0))
                stats['token_counts'].append(result.get('total_tokens', 0))
            else:
                stats['error_count'] += 1
        
        # 计算统计指标
        performance_summary = []
        for model_key, stats in model_stats.items():
            if stats['success_count'] > 0:
                avg_duration = stats['total_duration'] / stats['success_count']
                avg_tokens = stats['total_tokens'] / stats['success_count']
                avg_input_tokens = stats['total_input_tokens'] / stats['success_count']
                avg_output_tokens = stats['total_output_tokens'] / stats['success_count']
                
                # 计算中位数和标准差
                import statistics
                durations = stats['durations']
                tokens = stats['token_counts']
                
                median_duration = statistics.median(durations) if durations else 0
                duration_stdev = statistics.stdev(durations) if len(durations) > 1 else 0
                median_tokens = statistics.median(tokens) if tokens else 0
                token_stdev = statistics.stdev(tokens) if len(tokens) > 1 else 0
            else:
                avg_duration = 0
                avg_tokens = 0
                avg_input_tokens = 0
                avg_output_tokens = 0
                median_duration = 0
                duration_stdev = 0
                median_tokens = 0
                token_stdev = 0
            
            summary = {
                'model_key': model_key,
                'model_name': stats['model_name'],
                'model_id': stats['model_id'],
                'total_images': stats['total_images'],
                'success_count': stats['success_count'],
                'error_count': stats['error_count'],
                'success_rate': round(stats['success_count'] / stats['total_images'] * 100, 2) if stats['total_images'] > 0 else 0,
                'avg_duration_seconds': round(avg_duration, 3),
                'median_duration_seconds': round(median_duration, 3),
                'duration_stdev': round(duration_stdev, 3),
                'total_duration_seconds': round(stats['total_duration'], 3),
                'avg_input_tokens': round(avg_input_tokens, 1),
                'avg_output_tokens': round(avg_output_tokens, 1),
                'avg_total_tokens': round(avg_tokens, 1),
                'median_tokens': round(median_tokens, 1),
                'token_stdev': round(token_stdev, 1),
                'total_input_tokens': stats['total_input_tokens'],
                'total_output_tokens': stats['total_output_tokens'],
                'total_tokens': stats['total_tokens']
            }
            
            performance_summary.append(summary)
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "统计分析",
                f"✅ 已生成 {len(performance_summary)} 个模型的性能统计报告",
                "success"
            )
        
        # 构建输出数据
        output_data = input_data.copy()
        output_data['performance_summary'] = performance_summary
        
        logger.info(f"✅ 统计分析完成，生成了 {len(performance_summary)} 个模型的性能报告")
        yield output_data


class PerformanceResultSaveNode(BaseNode):
    """性能结果保存节点"""
    
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
        print("💾 开始保存结果...")
        
        workflow_chat = input_data.get('workflow_chat')
        test_results = input_data.get('test_results', [])
        performance_summary = input_data.get('performance_summary', [])
        config = input_data.get('config', {})
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "结果保存",
                "正在保存识别结果和性能统计...",
                "progress"
            )
        
        # 保存详细识别结果
        recognition_save_result = await self._save_recognition_results(test_results, config)
        
        # 保存性能统计
        performance_save_result = await self._save_performance_stats(performance_summary, config)
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "结果保存",
                "✅ 所有结果已保存完成",
                "success"
            )
        
        # 构建输出数据
        output_data = input_data.copy()
        output_data.update({
            'recognition_save_result': recognition_save_result,
            'performance_save_result': performance_save_result,
            'save_success': recognition_save_result.get('success', False) and performance_save_result.get('success', False)
        })
        
        yield output_data
    
    async def _save_recognition_results(self, test_results: List[Dict], config: Dict) -> Dict:
        """保存详细识别结果"""
        try:
            csv_config = config.get('csv_output', {})
            output_dir = csv_config.get('output_dir', 'workspace/vision_performance_output')
            filename = csv_config.get('recognition_filename', 'vision_recognition_results.csv')
            encoding = csv_config.get('encoding', 'utf-8-sig')
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(filename)[0]
            ext = os.path.splitext(filename)[1]
            timestamped_filename = f"{base_name}_{timestamp}{ext}"
            
            csv_file = os.path.join(output_dir, timestamped_filename)
            
            # 写入CSV文件
            with open(csv_file, 'w', newline='', encoding=encoding) as f:
                fieldnames = [
                    '模型名称', '模型ID', '图片名称', '图片路径', '图片标题', '图片描述',
                    '耗时(秒)', '输入Token', '输出Token', '总Token', '时间戳', '错误信息'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in test_results:
                    writer.writerow({
                        '模型名称': result.get('model_name', ''),
                        '模型ID': result.get('model_id', ''),
                        '图片名称': result.get('image_name', ''),
                        '图片路径': result.get('image_path', ''),
                        '图片标题': result.get('title', ''),
                        '图片描述': result.get('description', ''),
                        '耗时(秒)': result.get('duration_seconds', 0),
                        '输入Token': result.get('input_tokens', 0),
                        '输出Token': result.get('output_tokens', 0),
                        '总Token': result.get('total_tokens', 0),
                        '时间戳': result.get('timestamp', ''),
                        '错误信息': result.get('error', '')
                    })
            
            logger.info(f"✅ 识别结果保存完成：{len(test_results)}条记录保存到 {csv_file}")
            
            return {
                'success': True,
                'message': f"成功保存{len(test_results)}条识别结果",
                'count': len(test_results),
                'file_path': csv_file
            }
            
        except Exception as e:
            logger.error(f"识别结果保存失败: {e}")
            return {
                'success': False,
                'message': f"保存失败: {str(e)}",
                'error': str(e)
            }
    
    async def _save_performance_stats(self, performance_summary: List[Dict], config: Dict) -> Dict:
        """保存性能统计"""
        try:
            csv_config = config.get('csv_output', {})
            output_dir = csv_config.get('output_dir', 'workspace/vision_performance_output')
            filename = csv_config.get('performance_filename', 'vision_performance_stats.csv')
            encoding = csv_config.get('encoding', 'utf-8-sig')
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(filename)[0]
            ext = os.path.splitext(filename)[1]
            timestamped_filename = f"{base_name}_{timestamp}{ext}"
            
            csv_file = os.path.join(output_dir, timestamped_filename)
            
            # 写入CSV文件
            with open(csv_file, 'w', newline='', encoding=encoding) as f:
                fieldnames = [
                    '模型名称', '模型ID', '测试图片数', '成功数量', '失败数量', '成功率(%)',
                    '平均耗时(秒)', '中位耗时(秒)', '耗时标准差', '总耗时(秒)',
                    '平均输入Token', '平均输出Token', '平均总Token', 'Token中位数', 'Token标准差',
                    '总输入Token', '总输出Token', '总Token数'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for summary in performance_summary:
                    writer.writerow({
                        '模型名称': summary.get('model_name', ''),
                        '模型ID': summary.get('model_id', ''),
                        '测试图片数': summary.get('total_images', 0),
                        '成功数量': summary.get('success_count', 0),
                        '失败数量': summary.get('error_count', 0),
                        '成功率(%)': summary.get('success_rate', 0),
                        '平均耗时(秒)': summary.get('avg_duration_seconds', 0),
                        '中位耗时(秒)': summary.get('median_duration_seconds', 0),
                        '耗时标准差': summary.get('duration_stdev', 0),
                        '总耗时(秒)': summary.get('total_duration_seconds', 0),
                        '平均输入Token': summary.get('avg_input_tokens', 0),
                        '平均输出Token': summary.get('avg_output_tokens', 0),
                        '平均总Token': summary.get('avg_total_tokens', 0),
                        'Token中位数': summary.get('median_tokens', 0),
                        'Token标准差': summary.get('token_stdev', 0),
                        '总输入Token': summary.get('total_input_tokens', 0),
                        '总输出Token': summary.get('total_output_tokens', 0),
                        '总Token数': summary.get('total_tokens', 0)
                    })
            
            logger.info(f"✅ 性能统计保存完成：{len(performance_summary)}个模型的统计保存到 {csv_file}")
            
            return {
                'success': True,
                'message': f"成功保存{len(performance_summary)}个模型的性能统计",
                'count': len(performance_summary),
                'file_path': csv_file
            }
            
        except Exception as e:
            logger.error(f"性能统计保存失败: {e}")
            return {
                'success': False,
                'message': f"保存失败: {str(e)}",
                'error': str(e)
            }


if __name__ == "__main__":
    """直接运行此文件进行图片识别性能测试"""
    import asyncio
    import glob
    
    print("🖼️ 图片识别性能分析工作流")
    print("=" * 60)
    
    class MockWorkflowChat:
        def __init__(self):
            self.current_node = ""
        
        async def add_node_message(self, node_name: str, message: str, status: str):
            print(f"[{node_name}] {status}: {message}")
        
        def _create_workflow_progress(self):
            return "<div>工作流进度</div>"
    
    async def main():
        try:
            # 初始化工作流
            workflow = VisionPerformanceWorkflow()
            print("✅ 图片识别性能分析工作流初始化完成")
            
            # 自动扫描图片
            image_paths = []
            image_dirs = [
                "workspace/input/对话日常图片/通用/*.png",
                "workspace/input/对话日常图片/动物修/*.png",
                "workspace/input/对话日常图片/美食修/*.png", 
                "workspace/input/对话日常图片/风景修/*.png"
            ]
            
            for pattern in image_dirs:
                image_paths.extend(glob.glob(pattern))
            
            # 限制测试图片数量（演示用）
            image_paths = image_paths[:3] if len(image_paths) > 3 else image_paths
            
            print(f"🖼️ 发现图片数量: {len(image_paths)}")
            
            # 配置
            config = {
                'batch_size': 10,
                'test_all_models': True,
                'csv_output': {
                    'enabled': True,
                    'output_dir': 'workspace/vision_performance_output',
                    'recognition_filename': 'vision_recognition_results.csv',
                    'performance_filename': 'vision_performance_stats.csv',
                    'encoding': 'utf-8-sig'
                }
            }
            
            # 创建模拟聊天界面
            mock_chat = MockWorkflowChat()
            
            # 创建工作流图
            graph = await workflow.create_vision_performance_graph()
            compiled_graph = graph.compile()
            print("✅ 工作流图创建完成")
            
            # 准备输入数据
            input_data = {
                'config': config,
                'workflow_chat': mock_chat,
                'images': image_paths
            }
            
            print(f"\n🚀 开始性能测试，处理{len(image_paths)}张图片...")
            
            # 执行工作流
            final_result = None
            async for result in compiled_graph.stream(input_data):
                if result:
                    final_result = result
            
            print("\n✅ 图片识别性能分析工作流执行完成!")
            
            # 打印简要统计
            if final_result and 'performance_summary' in final_result:
                print("\n📊 性能统计摘要:")
                print("-" * 60)
                for summary in final_result['performance_summary']:
                    print(f"模型: {summary['model_name']}")
                    print(f"  成功率: {summary['success_rate']}%")
                    print(f"  平均耗时: {summary['avg_duration_seconds']}秒")
                    print(f"  平均Token: {summary['avg_total_tokens']}")
                    print(f"  总Token: {summary['total_tokens']}")
                    print()
            
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 运行主函数
    asyncio.run(main())