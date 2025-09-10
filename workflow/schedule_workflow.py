"""日程生成工作流 - 基于Graph+Node的日程创作系统
集成角色库、地点库、剧情库等功能，为主角生成每周和每天的详细日程安排
"""

import json
import asyncio
import csv
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import calendar

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.graph import StateGraph
from core.base import BaseNode
from llm.base import LLMFactory
from core.types import LLMConfig, TaskResult, Message, MessageRole

logger = logging.getLogger(__name__)

class ScheduleWorkflow:
    """日程生成工作流管理器"""
    
    def __init__(self, llm=None):
        self.llm = llm
        self.graph = None
        self.characters_data = {}
        self.locations_data = {}
        self.stories_data = {}  # 剧情库数据
        self.protagonist_data = ""  # 主角穆昭的详细人设
        self.holidays_data = {}  # 节假日数据
        self.current_config = {
            'protagonist': '穆昭',  # 固定主角
            'schedule_type': 'weekly',  # weekly, daily, monthly
            'start_date': '',
            'end_date': '',
            'total_days': 7,
            'selected_characters': [],
            'selected_locations': [],
            'selected_stories': [],  # 选择的剧情
            'time_slots_config': {
                '夜间': {'start': '23:00', 'end': '06:00'},
                '上午': {'start': '06:00', 'end': '11:00'},
                '中午': {'start': '11:00', 'end': '14:00'},
                '下午': {'start': '14:00', 'end': '18:00'},
                '晚上': {'start': '18:00', 'end': '23:00'}
            },
            'character_distribution': 'balanced',  # balanced, random, weighted
            'story_integration': 'moderate',  # minimal, moderate, intensive
            'include_holidays': True,
            'include_lunar': True,
            'mood_variety': True,
            'location_variety': True,
            'enable_cycle_summary': False,  # 是否启用周期总结功能，默认关闭
            'cycle_summary': ''  # 当前周期总结内容
        }
        
        # 预先初始化数据库表结构，防止执行时才创建导致错误
        try:
            from database.managers import schedule_manager
            schedule_manager.ScheduleManager()  # 初始化会自动创建表结构
            logger.info("数据库表结构初始化完成")
        except Exception as e:
            logger.warning(f"预初始化数据库表结构失败，稍后将重试: {e}")
        
        # 加载各种数据
        self._load_game_data()
        self._load_protagonist_data()
        self._load_stories_data()
        self._load_holidays_data()
    
    def _load_game_data(self):
        """加载游戏角色和地点数据"""
        try:
            # 加载角色数据
            char_path = os.path.join(os.path.dirname(__file__), '../../config/yunhub_characters.json')
            if os.path.exists(char_path):
                with open(char_path, 'r', encoding='utf-8') as f:
                    self.characters_data = json.load(f)
                    logger.info(f"成功加载角色数据，包含 {len(self.characters_data.get('角色列表', {}))} 个角色")
            
            # 加载地点数据
            loc_path = os.path.join(os.path.dirname(__file__), '../../config/yunhub_locations.json')
            if os.path.exists(loc_path):
                with open(loc_path, 'r', encoding='utf-8') as f:
                    self.locations_data = json.load(f)
                    district_count = len(self.locations_data.get("districts", {}))
                    logger.info(f"成功加载地点数据，包含 {district_count} 个区域")
                    
        except Exception as e:
            logger.error(f"加载游戏数据失败: {e}")
    
    def _load_protagonist_data(self):
        """加载主角穆昭的详细人设"""
        try:
            protagonist_path = os.path.join(os.path.dirname(__file__), '../../config/基础人设_穆昭.txt')
            if os.path.exists(protagonist_path):
                with open(protagonist_path, 'r', encoding='utf-8') as f:
                    self.protagonist_data = f.read()
                    logger.info(f"成功加载主角人设，内容长度: {len(self.protagonist_data)} 字符")
            else:
                logger.warning("主角人设文件不存在")
                
        except Exception as e:
            logger.error(f"加载主角人设失败: {e}")
    
    def _load_stories_data(self):
        """加载已有剧情数据作为参考"""
        try:
            from database import story_manager
            
            # 获取所有剧情作为参考
            all_stories = story_manager.get_stories_by_filter({}, limit=100)
            
            # 按角色分组剧情
            self.stories_data = {
                'all_stories': all_stories,
                'by_character': {},
                'by_location': {},
                'by_type': {}
            }
            
            for story in all_stories:
                # 按角色分组
                characters = json.loads(story.get('selected_characters', '[]'))
                for char in characters:
                    if char not in self.stories_data['by_character']:
                        self.stories_data['by_character'][char] = []
                    self.stories_data['by_character'][char].append(story)
                
                # 按地点分组
                locations = json.loads(story.get('selected_locations', '[]'))
                for loc in locations:
                    if loc not in self.stories_data['by_location']:
                        self.stories_data['by_location'][loc] = []
                    self.stories_data['by_location'][loc].append(story)
                
                # 按类型分组
                story_type = story.get('story_type', 'daily_life')
                if story_type not in self.stories_data['by_type']:
                    self.stories_data['by_type'][story_type] = []
                self.stories_data['by_type'][story_type].append(story)
            
            logger.info(f"成功加载剧情数据，包含 {len(all_stories)} 个剧情")
            
        except Exception as e:
            logger.error(f"加载剧情数据失败: {e}")
            self.stories_data = {'all_stories': [], 'by_character': {}, 'by_location': {}, 'by_type': {}}
    
    def _load_holidays_data(self):
        """加载节假日数据"""
        try:
            # 从CSV文件加载节假日数据
            holidays_csv_path = os.path.join(os.path.dirname(__file__), '../../config/holidays.csv')
            
            if os.path.exists(holidays_csv_path):
                with open(holidays_csv_path, 'r', encoding='utf-8') as f:
                    csv_reader = csv.DictReader(f)
                    for row in csv_reader:
                        date_str = row['date']
                        self.holidays_data[date_str] = {
                            'name': row['name'],
                            'type': row['type'],
                            'lunar': row['lunar'].lower() == 'true',
                            'description': row.get('description', '')
                        }
                
                logger.info(f"从CSV文件加载节假日数据，包含 {len(self.holidays_data)} 个节假日")

            
        except Exception as e:
            logger.error(f"加载节假日数据失败: {e}")
            # 使用空字典作为最后的后备
            self.holidays_data = {}
    
    def get_protagonist_info(self) -> Dict[str, Any]:
        """获取主角信息"""
        protagonist_name = self.current_config.get('protagonist', '穆昭')
        return {
            'name': protagonist_name,
            'type': 'protagonist',
            'description': self.protagonist_data.split('\n')[0] if self.protagonist_data else '主角信息',
            'full_profile': self.protagonist_data
        }
    
    def get_characters_list(self) -> List[Dict[str, Any]]:
        """获取角色列表（不包含主角）"""
        characters = []
        char_list = self.characters_data.get("角色列表", {})
        
        for name, info in char_list.items():
            # 跳过主角，主角单独处理
            if name == '穆昭':
                continue
                
            characters.append({
                'name': name,
                'age': info.get('年龄', '未知'),
                'personality': info.get('性格', ''),
                'description': info.get('简介', ''),
                'locations': info.get('活动地点', []),
                'plots': info.get('可触发剧情', []),
                'backstory': info.get('背景故事', ''),
                'relationships': info.get('人际关系', {}),
                'habits': info.get('生活习惯', []),
                'appearance': info.get('外貌特征', ''),
                'skills': info.get('特长技能', [])
            })
        
        return characters
    
    def get_locations_list(self) -> List[Dict[str, Any]]:
        """获取地点列表"""
        locations = []
        districts = self.locations_data.get("districts", {})
        
        for district_name, district_info in districts.items():
            district_locations = district_info.get("locations", {})
            for loc_name, loc_info in district_locations.items():
                locations.append({
                    'name': loc_info.get('name', loc_name),
                    'type': loc_info.get('type', ''),
                    'district': district_info.get('name', district_name),
                    'description': loc_info.get('description', ''),
                    'atmosphere': loc_info.get('atmosphere', ''),
                    'keywords': loc_info.get('keywords', [])
                })
        
        return locations
    
    def get_stories_list(self) -> List[Dict[str, Any]]:
        """获取剧情列表"""
        stories = []
        for story in self.stories_data.get('all_stories', []):
            stories.append({
                'story_id': story.get('story_id', ''),
                'story_name': story.get('story_name', ''),
                'story_overview': story.get('story_overview', ''),
                'story_type': story.get('story_type', ''),
                'characters': json.loads(story.get('selected_characters', '[]')),
                'locations': json.loads(story.get('selected_locations', '[]')),
                'main_conflict': story.get('main_conflict', ''),
                'emotional_development': story.get('emotional_development', '')
            })
        
        return stories
    
    def get_holidays_in_range(self, start_date: str, end_date: str) -> Dict[str, Dict[str, Any]]:
        """获取指定日期范围内的节假日"""
        holidays = {}
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        for date_str, holiday_info in self.holidays_data.items():
            holiday_date = datetime.strptime(date_str, '%Y-%m-%d')
            if start <= holiday_date <= end:
                holidays[date_str] = holiday_info
        
        return holidays
    
    def update_config(self, config_updates: Dict[str, Any]):
        """更新工作流配置"""
        self.current_config.update(config_updates)
    
    async def prepare_cycle_summary(self, config: Dict[str, Any]) -> str:
        """准备周期总结，获取历史数据"""
        try:
            # 检查是否启用周期总结
            if not config.get('enable_cycle_summary', False):
                logger.info("周期总结功能未启用")
                return ""
            
            # 等待1秒，确保数据库写入完成
            import time
            time.sleep(1)
            
            # 从数据库获取最新的周期总结
            from database.managers.schedule_manager import ScheduleManager
            schedule_manager = ScheduleManager()
            
            # 传递开始日期，确保获取早于开始日期且时间不超过三天的总结
            start_date = config.get('start_date', '')
            previous_summary = schedule_manager.get_latest_cycle_summary(before_date=start_date)
            
            if previous_summary:
                logger.info(f"获取到适当的历史周期总结，长度: {len(previous_summary)} 字符")
                return previous_summary
            else:
                logger.info(f"未找到{start_date}前三天内的周期总结，这可能是第一个周期或时间间隔较长")
                return ""
                
        except Exception as e:
            logger.error(f"准备周期总结失败: {e}")
            return ""
    
    async def create_schedule_graph(self) -> StateGraph:
        """创建日程生成图工作流 - 多周期循环版本"""
        self.graph = StateGraph(name="schedule_generation_workflow")
        
        # 创建节点
        cycle_planning_node = CyclePlanningNode()  # 周期规划节点
        schedule_generate_node = ScheduleGenerateNode()  # 周期生成节点
        
        # 添加节点到图
        self.graph.add_node("cycle_planning", cycle_planning_node)
        self.graph.add_node("schedule_generate", schedule_generate_node)
        
        # 定义条件路由函数
        def should_continue_generation(state):
            """判断是否继续生成下一个周期"""
            current_cycle_index = state.get('current_cycle_index', 0)
            cycles = state.get('cycles', [])
            generation_complete = state.get('generation_complete', False)
            
            logger.info(f"🔄 路由决策:")
            logger.info(f"  current_cycle_index: {current_cycle_index}")
            logger.info(f"  len(cycles): {len(cycles) if cycles else 0}")
            logger.info(f"  generation_complete: {generation_complete}")
            
            if generation_complete or current_cycle_index >= len(cycles):
                logger.info(f"🏁 路由决策：END")
                return "END"  # 结束工作流
            else:
                logger.info(f"🔄 路由决策：继续 schedule_generate")
                return "schedule_generate"  # 继续生成下一个周期
        
        # 定义节点连接关系
        self.graph.add_edge("cycle_planning", "schedule_generate")
        self.graph.add_conditional_edges(
            "schedule_generate",
            should_continue_generation,
            {
                "schedule_generate": "schedule_generate",  # 循环生成
                "END": "__end__"  # 结束
            }
        )
        
        # 设置入口点
        self.graph.set_entry_point("cycle_planning")
        
        return self.graph
    
    async def execute_workflow_stream(self, config: Dict[str, Any], workflow):
        """流式执行工作流 - 使用StateGraph自动编排"""
        try:
            # 准备初始输入
            initial_input = {
                'characters_data': self.characters_data,
                'locations_data': self.locations_data,
                'stories_data': self.stories_data,
                'protagonist_data': self.protagonist_data,
                'holidays_data': self.holidays_data,
                'config': config,
                'protagonist': config.get('protagonist', '穆昭'),
                'schedule_type': config.get('schedule_type', 'weekly'),
                'start_date': config.get('start_date', ''),
                'end_date': config.get('end_date', ''),
                'total_days': config.get('total_days', 7),
                'selected_characters': config.get('selected_characters', []),
                'selected_locations': config.get('selected_locations', []),
                'selected_stories': config.get('selected_stories', []),
                'time_slots_config': config.get('time_slots_config', self.current_config['time_slots_config']),
                'character_distribution': config.get('character_distribution', 'balanced'),
                'story_integration': config.get('story_integration', 'moderate'),
                'include_holidays': config.get('include_holidays', True),
                'include_lunar': config.get('include_lunar', True),
                'workflow_chat': workflow,  # 传递UI更新器
                'llm': self.llm  # 传递LLM实例
            }
            
            # 创建并编译图工作流
            if not self.graph:
                await self.create_schedule_graph()
            
            compiled_graph = self.graph.compile()
            
            # 使用图的流式执行 - 使用async for正确处理异步生成器
            async for stream_event in compiled_graph.stream(initial_input):
                event_type = stream_event.get('type')
                node_name = stream_event.get('node')
                
                if event_type == 'start':
                    # 工作流开始
                    yield (
                        workflow._create_workflow_progress(),
                        "",
                        "日程生成工作流开始执行...",
                        False
                    )
                
                elif event_type == 'node_start':
                    # 节点开始执行
                    node_display_name = self._get_node_display_name(node_name)
                    workflow.current_node = self._get_node_id(node_name)
                    
                    # 更新UI - 节点开始状态
                    await workflow.add_node_message(
                        node_display_name,
                        "开始执行...",
                        "progress"
                    )
                    
                    yield (
                        workflow._create_workflow_progress(),
                        "",
                        f"{node_display_name}开始执行...",
                        False
                    )
                
                elif event_type == 'node_streaming':
                    # 节点流式执行中
                    intermediate_result = stream_event.get('intermediate_result')
                    if intermediate_result and intermediate_result.state_update:
                        # 获取当前生成的内容长度
                        content_length = 0
                        for key in ['schedule_content', 'daily_schedules', 'schedule_result']:
                            if key in intermediate_result.state_update:
                                if isinstance(intermediate_result.state_update[key], str):
                                    content_length = len(intermediate_result.state_update[key])
                                elif isinstance(intermediate_result.state_update[key], (list, dict)):
                                    content_length = len(str(intermediate_result.state_update[key]))
                                break
                        
                        # 实时更新进度信息 - 获取最新的进度HTML，与story_workflow保持一致
                        if content_length > 0:
                            node_display_name = self._get_node_display_name(node_name)
                            await workflow.add_node_message(
                                node_display_name,
                                f"正在生成日程内容... 当前生成{content_length}字符",
                                "streaming"
                            )
                            
                            yield (
                                workflow._create_workflow_progress(),
                                "",
                                f"正在生成日程内容... 当前长度: {content_length} 字符",
                                False
                            )
                
                elif event_type == 'node_complete':
                    # 节点执行完成
                    node_display_name = self._get_node_display_name(node_name)
                    node_id = self._get_node_id(node_name)
                    
                    # 为节点添加完成消息，确保UI正确更新
                    if node_name == 'schedule_generate':
                        result_content = "✅ 日程生成完成"
                        if 'schedule_result' in stream_event.get('output', {}):
                            schedule_data = stream_event['output']['schedule_result']
                            if isinstance(schedule_data, (dict, list)):
                                result_content = f"✅ 已成功生成{config['total_days']}天的日程安排"
                    else:
                        result_content = "✅ 执行完成"
                        
                    # 更新节点消息
                    await workflow.add_node_message(
                        node_display_name,
                        result_content,
                        "completed"
                    )
                    
                    yield (
                        workflow._create_workflow_progress(),
                        "",
                        f"{node_display_name}执行完成",
                        False
                    )
                
                elif event_type == 'node_error':
                    # 节点执行错误
                    error_msg = stream_event.get('error', '未知错误')
                    node_display_name = self._get_node_display_name(node_name)
                    
                    await workflow.add_node_message(
                        node_display_name,
                        f"执行失败: {error_msg}",
                        "error"
                    )
                    
                    yield (
                        workflow._create_workflow_progress(),
                        "",
                        "",
                        False
                    )
                
                elif event_type == 'final':
                    # 工作流完成
                    yield (
                        workflow._create_workflow_progress(),
                        "",
                        "日程生成工作流执行完成",
                        False
                    )
                
                # 其他事件类型可以忽略或记录日志
                else:
                    # 持续更新UI以保持流畅性
                    yield (
                        workflow._create_workflow_progress(),
                        "",
                        "日程生成工作流执行中...",
                        False
                    )
                
        except Exception as e:
            logger.error(f"日程生成工作流流式执行失败: {e}")
            await workflow.add_node_message(
                "系统",
                f"工作流执行失败: {str(e)}",
                "error"
            )
            yield (
                workflow._create_workflow_progress(),
                "",
                "",
                False
            )
    
    def _get_node_display_name(self, node_name: str) -> str:
        """获取节点显示名称"""
        name_mapping = {
            'cycle_planning': '周期规划',
            'schedule_generate': '日程生成'
        }
        return name_mapping.get(node_name, node_name)
    
    def _get_node_id(self, node_name: str) -> str:
        """获取节点ID"""
        id_mapping = {
            'cycle_planning': 'planning',
            'schedule_generate': 'generate'
        }
        return id_mapping.get(node_name, node_name)


class CyclePlanningNode(BaseNode):
    """周期规划节点 - 预先规划所有批次的周期计划"""
    
    def __init__(self):
        super().__init__(name="cycle_planning", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行周期规划节点 - 非流式版本"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行周期规划节点"""
        print("📋 开始周期规划...")
        
        workflow_chat = input_data.get('workflow_chat')
        llm = input_data.get('llm')
        
        # 获取配置参数
        start_date = input_data.get('start_date', '')
        end_date = input_data.get('end_date', '')
        total_days = input_data.get('total_days', 7)
        protagonist = input_data.get('protagonist', '穆昭')
        selected_characters = input_data.get('selected_characters', [])
        selected_locations = input_data.get('selected_locations', [])
        config = input_data.get('config', {})
        
        # 更新UI
        if workflow_chat:
            await workflow_chat.add_node_message(
                "周期规划",
                f"正在为{total_days}天时间范围制定周期规划...",
                "progress"
            )
        
        try:
            from datetime import datetime, timedelta
            import math
            
            # 新设计：支持大批次生成，每次规划生成较少周期但可以多次调用
            min_cycle_days = 7
            max_cycle_days = 15
            cycles_per_batch = 8  # 每批次最多生成8个周期
            
            # 智能分配周期长度
            cycles = []
            remaining_days = total_days
            current_date = datetime.strptime(start_date, '%Y-%m-%d')
            
            cycle_num = 1
            cycles_generated = 0
            
            while remaining_days > 0 and cycles_generated < cycles_per_batch:
                # 根据剩余天数智能决定周期长度
                if remaining_days <= max_cycle_days:
                    cycle_days = remaining_days
                else:
                    # 优先选择较长的周期，但保证最后一个周期不会太短
                    if remaining_days <= max_cycle_days + min_cycle_days:
                        cycle_days = remaining_days // 2
                    else:
                        cycle_days = random.randint(min_cycle_days, max_cycle_days)
                
                cycle_end_date = current_date + timedelta(days=cycle_days - 1)
                
                cycles.append({
                    'cycle_number': cycle_num,
                    'start_date': current_date.strftime('%Y-%m-%d'),
                    'end_date': cycle_end_date.strftime('%Y-%m-%d'),
                    'total_days': cycle_days,
                    'status': 'planned'
                })
                
                current_date = cycle_end_date + timedelta(days=1)
                remaining_days -= cycle_days
                cycle_num += 1
                cycles_generated += 1
            
            logger.info(f"本批次分配了 {len(cycles)} 个周期，剩余 {remaining_days} 天")
            
            # 为下次规划准备信息
            next_start_date = current_date.strftime('%Y-%m-%d') if remaining_days > 0 else None
            
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "周期规划",
                    f"已智能分配 {len(cycles)} 个周期，每个周期 {min_cycle_days}-{max_cycle_days} 天",
                    "progress"
                )
            
            # 准备历史上下文
            protagonist_data = input_data.get('protagonist_data', '')
            
            # 指定的重要角色列表
            important_characters = ['瑟琳娜', '郝聪明', '林安予', '元逸', '元南', '罗恒', '易奶奶', '金喜']
            
            # 获取重要角色的详细信息
            important_characters_info = []
            char_list = input_data.get('characters_data', {}).get("角色列表", {})
            for char_name in important_characters:
                if char_name in char_list:
                    char_info = char_list[char_name]
                    char_desc = f"{char_name}（重要角色）：{char_info.get('简介', '')}"
                    if char_info.get('性格'):
                        char_desc += f"，性格{char_info.get('性格')}"
                    if char_info.get('年龄'):
                        char_desc += f"，年龄{char_info.get('年龄')}"
                    if char_info.get('活动地点'):
                        char_desc += f"，主要活动地点：{', '.join(char_info.get('活动地点', []))}"
                    important_characters_info.append(char_desc)
                else:
                    important_characters_info.append(f"{char_name}（重要角色，待配置）")
            
            # 获取上一批次总结信息（如果有）
            previous_summary = config.get('previous_batch_summary', '')
            
            # 获取整个时间段内的节假日信息
            holidays_data = input_data.get('holidays_data', {})
            cycle_holidays = []
            if holidays_data:
                from datetime import datetime
                period_start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                period_end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                
                for date_str, holiday_info in holidays_data.items():
                    try:
                        holiday_dt = datetime.strptime(date_str, '%Y-%m-%d')
                        if period_start_dt <= holiday_dt <= period_end_dt:
                            cycle_holidays.append(f"{date_str}: {holiday_info['name']} ({holiday_info['type']})")
                    except:
                        continue
            
            # 构建周期规划提示词：system纯指令，user动态数据
            system_planning_instructions = """
# 规划要求

## 主角中心的故事发展
1. **时间跨度感**：在给定天数的时间段中，主角的个人成长和发展轨迹
2. **个人目标推进**：主角的学术研究、工作项目、个人技能等方面的进展
3. **生活节奏建立**：工作与生活的平衡，日常习惯的养成和调整
4. **季节适应**：根据季节变化调整活动安排和心理状态
5. 规划以个人规划为主，不强制绑定某个角色，不会在大周期为某个其他角色而做事
6. **节假日体验**：在节假日中的个人安排和文化体验
7. 不强行绑定地点，以个人行为为主，地点只是辅助
不做和星空，天文有关的计划
## 每个周期规划内容
为每个周期制定：
- **周期主题**：这个周期的核心主题和重点
- **主要目标**：主角在这个周期想要达成的具体目标
- **核心地点**：主要活动场所
- **关键事件**：预计会发生的重要事件
- **情感基调**：整个周期的情感发展方向
- **衔接要点**：与前后周期的连接点

# 输出格式
请按以下JSON格式输出周期规划，禁止输出任何其他内容：

```json
{
  "overall_plan": {
    "total_days": <int>,
    "total_cycles": <int>,
    "story_theme": "整个时间段的故事主题",
    "major_milestones": [
      "重要节点1",
      "重要节点2"
    ]
  },
  "cycle_plans": [
    {
      "cycle_number": 1,
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD", 
      "total_days": 7,
      "cycle_theme": "周期主题",
      "cycle_plan": "第三人称，以穆昭为主体的详细周期计划描述，200-300字，包含这个周期的整体安排、重点目标、主要活动等,注意是计划而不是纲要所以不能有预知能力，只是计划不是实际发生的事情，以穆昭计划xxx开始",
      "main_objectives": [
        "目标1",
        "目标2"
      ],
      "focus_characters": ["无", "无"],
      "secondary_characters": ["无", "无"],
      "core_locations": ["地点1", "地点2"],
      "key_events": [
        "事件1",
        "事件2"
      ],
      "emotional_tone": "情感基调描述",
      "connection_points": {
        "from_previous": "与前周期的衔接",
        "to_next": "与后周期的衔接"
      }
    },
    // ... 其他周期
  ]
}
```

# 重要要求
1. **连贯性**：确保各周期之间有自然的过渡和发展
2. **平衡性**：角色和地点的分配要相对均衡
3. **现实性**：规划要符合主角的身份和云枢市的设定
4. **发展性**：每个周期都要有明确的进展，避免重复
5. **完整性**：为所有周期都制定详细规划

请开始制定这个全面而详细的周期规划，禁止输出任何其他内容。
"""

            user_planning_dynamic = f"""你是一名专业的长期规划师，需要为主角{protagonist}制定从{start_date}到{end_date}（共{total_days}天）的整体周期规划。

# 主角信息
{protagonist_data}

{f"# 历史背景信息{chr(10)}{previous_summary}{chr(10)}" if previous_summary else ''}

# 活动地点
{', '.join(selected_locations)}

# 周期分配
已分配为{len(cycles)}个周期：
{json.dumps(cycles, ensure_ascii=False, indent=2)}

# 节假日信息
当前周期内的节假日：
{chr(10).join(cycle_holidays) if cycle_holidays else '无特殊节假日'}"""
            
            # 调用LLM生成周期规划
            logger.info(f"周期规划: 开始LLM调用，user动态长度: {len(user_planning_dynamic)}")
            
            if llm:
                # 构建消息（system 纯指令 + user 动态资料）
                from core.types import Message, MessageRole
                messages = [
                    Message(role=MessageRole.SYSTEM, content=system_planning_instructions),
                    Message(role=MessageRole.USER, content=user_planning_dynamic)
                ]
                
                # 流式调用LLM（豆包自带打印）
                final_content = ""
                
                async for chunk_data in llm.stream_generate(
                    messages, 
                    mode="think",
                    return_dict=True
                ):
                    content_part = chunk_data.get("content", "")
                    final_content += content_part
                
                logger.info(f"周期规划生成完成，内容长度: {len(final_content)}")
            else:
                raise Exception("LLM未初始化")
            
            # 解析JSON结果
            cycle_planning_data = None
            try:
                from parsers.json_parser import JSONParser
                parser = JSONParser()
                
                json_content = self._extract_json_from_content(final_content)
                logger.info(f"🔍 提取的JSON内容长度: {len(json_content)}")
                logger.info(f"📝 JSON内容前200字符: {json_content[:200]}...")
                
                parsed_result = parser.parse(json_content)
                
                # 🔍 调试：打印解析结果的结构
                logger.info(f"📊 解析结果类型: {type(parsed_result)}")
                if isinstance(parsed_result, dict):
                    logger.info(f"🔑 解析结果顶级键: {list(parsed_result.keys())}")
                    logger.info(f"📝 解析结果部分内容: {str(parsed_result)[:500]}...")
                
                # 检查是否有cycle_plans字段
                if parsed_result and 'cycle_plans' in parsed_result:
                    cycle_planning_data = parsed_result
                    logger.info(f"✅ 方式1：直接找到cycle_plans，包含 {len(cycle_planning_data['cycle_plans'])} 个周期")
                elif parsed_result and isinstance(parsed_result, dict):
                    # 检查是否只有一个顶级键包含所有数据
                    if len(parsed_result) == 1:
                        root_key = list(parsed_result.keys())[0] 
                        root_data = parsed_result[root_key]
                        if isinstance(root_data, dict) and 'cycle_plans' in root_data:
                            cycle_planning_data = root_data
                            logger.info(f"✅ 方式2：从根键 '{root_key}' 中找到cycle_plans，包含 {len(cycle_planning_data['cycle_plans'])} 个周期")
                        else:
                            # 尝试用标准json解析
                            try:
                                complete_parsed = json.loads(json_content)
                                if 'cycle_plans' in complete_parsed:
                                    cycle_planning_data = complete_parsed
                                    logger.info(f"✅ 方式3：json.loads解析成功，包含 {len(cycle_planning_data['cycle_plans'])} 个周期")
                                else:
                                    raise Exception(f"所有解析方式都无法找到cycle_plans字段，顶级键: {list(complete_parsed.keys())}")
                            except Exception as json_error:
                                raise Exception(f"所有JSON解析方式都失败: {json_error}")
                    else:
                        raise Exception(f"解析结果有多个顶级键但无cycle_plans: {list(parsed_result.keys())}")
                else:
                    raise Exception("解析结果为空或不是字典类型")
                
                if cycle_planning_data and 'cycle_plans' in cycle_planning_data:
                    if workflow_chat:
                        await workflow_chat.add_node_message(
                            "周期规划",
                            f"✅ 成功生成 {len(cycle_planning_data['cycle_plans'])} 个周期的详细规划",
                            "success"
                        )
                else:
                    raise Exception("最终未能获取有效的cycle_planning_data")
                    
            except Exception as parse_error:
                logger.error(f"周期规划JSON解析失败: {parse_error}")
                # 使用原始分配的周期作为后备方案
                cycle_planning_data = {
                    'overall_plan': {
                        'total_days': total_days,
                        'total_cycles': len(cycles),
                        'story_theme': f"{protagonist}的{total_days}天生活规划",
                        'character_arcs': {},
                        'major_milestones': []
                    },
                    'cycle_plans': cycles
                }
                
                # 为后备方案也生成基础的周期计划描述
                for cycle_plan in cycle_planning_data['cycle_plans']:
                    cycle_number = cycle_plan.get('cycle_number', 1)
                    total_days = cycle_plan.get('total_days', 0)
                    cycle_plan['cycle_plan'] = f"周期{cycle_number}：{protagonist}将在{total_days}天内重点关注个人发展和日常生活的平衡，通过规律的工作学习和适度的社交活动，逐步推进各项目标的实现，保持身心健康和积极的生活状态。"
                
                if workflow_chat:
                    await workflow_chat.add_node_message(
                        "周期规划",
                        f"⚠️ JSON解析失败，使用基础周期分配（{len(cycles)}个周期）",
                        "warning"
                    )
            
            # 输出最终结果
            output_data = input_data.copy()
            output_data['cycle_planning_result'] = cycle_planning_data
            output_data['cycles'] = cycle_planning_data['cycle_plans']
            output_data['current_cycle_index'] = 0  # 当前处理的周期索引
            
            logger.info(f"✅ 周期规划完成，生成了 {len(cycle_planning_data['cycle_plans'])} 个周期")
            yield output_data
            
        except Exception as e:
            logger.error(f"周期规划失败: {e}")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "周期规划",
                    f"❌ 规划失败: {str(e)}",
                    "error"
                )
            raise Exception(f"周期规划失败: {str(e)}")
    

    
    def _extract_json_from_content(self, content: str) -> str:
        """从生成内容中提取JSON部分 - 增强版JSON提取"""
        import re
        import json
        
        logger.info(f"🔍 开始提取JSON，原始内容长度: {len(content)}")
        
        # 方法1: 优先查找```json...```代码块
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            extracted_json = match.strip()
            if self._is_valid_json(extracted_json):
                logger.info(f"✅ 从```json```代码块提取有效JSON，长度: {len(extracted_json)}")
                return extracted_json
        
        # 方法2: 查找```...```代码块（不一定标注json）
        code_pattern = r'```[a-zA-Z]*\s*(.*?)\s*```'
        code_matches = re.findall(code_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in code_matches:
            extracted = match.strip()
            if extracted.startswith('{') and self._is_valid_json(extracted):
                logger.info(f"✅ 从代码块提取有效JSON，长度: {len(extracted)}")
                return extracted
        
        # 方法3: 使用括号匹配计数提取完整JSON
        def extract_complete_json(text):
            start_pos = text.find('{')
            if start_pos == -1:
                return None
            
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i, char in enumerate(text[start_pos:], start_pos):
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\' and in_string:
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                    
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return text[start_pos:i+1]
            
            return None
        
        complete_json = extract_complete_json(content)
        if complete_json and self._is_valid_json(complete_json):
            logger.info(f"✅ 使用括号匹配提取有效JSON，长度: {len(complete_json)}")
            return complete_json.strip()
        
        # 方法4: 多重正则匹配后验证
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # 简单嵌套
            r'\{.*?\}',  # 贪婪匹配
            r'\{.*\}'    # 最贪婪匹配
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                # 按长度排序，优先尝试最长的匹配
                sorted_matches = sorted(matches, key=len, reverse=True)
                for match in sorted_matches:
                    if self._is_valid_json(match):
                        logger.info(f"✅ 正则模式匹配到有效JSON，长度: {len(match)}")
                        return match.strip()
        
        logger.warning("❌ 所有方法都未能提取有效JSON，返回原内容")
        return content.strip()
    
    def _is_valid_json(self, json_str: str) -> bool:
        """验证JSON字符串是否有效"""
        try:
            json.loads(json_str)
            return True
        except (json.JSONDecodeError, ValueError):
            return False


class ScheduleGenerateNode(BaseNode):
    """日程生成节点 - 分批渐进式生成，一次生成3天日程"""
    
    def __init__(self):
        super().__init__(name="schedule_generate", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行日程生成节点 - 非流式版本"""
        # 使用流式执行并返回最终结果
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行日程生成节点 - 多周期批次生成"""
        print("📅 开始批次日程生成...")
        
        try:
            workflow_chat = input_data.get('workflow_chat')
            llm = input_data.get('llm')
            
            # 获取当前执行状态
            current_cycle_index = input_data.get('current_cycle_index', 0)
            cycles = input_data.get('cycles', [])
            
            logger.info(f"🔍 日程生成节点状态检查:")
            logger.info(f"  current_cycle_index: {current_cycle_index}")
            logger.info(f"  cycles 数量: {len(cycles) if cycles else 0}")
            logger.info(f"  cycles 类型: {type(cycles)}")
            print(f"🔍 DEBUG: current_cycle_index={current_cycle_index}, cycles数量={len(cycles) if cycles else 0}")
            
            if not cycles:
                logger.error("❌ 缺少周期规划数据，请先执行周期规划节点")
                print("❌ DEBUG: 缺少周期规划数据")
                raise Exception("缺少周期规划数据，请先执行周期规划节点")
            
            # 检查是否所有周期都已完成
            if current_cycle_index >= len(cycles):
                logger.info(f"✅ 所有 {len(cycles)} 个周期已完成")
                print(f"✅ DEBUG: 所有 {len(cycles)} 个周期已完成")
                if workflow_chat:
                    await workflow_chat.add_node_message(
                        "日程生成",
                        f"✅ 所有 {len(cycles)} 个周期的日程生成已完成！",
                        "success"
                    )
                
                output_data = input_data.copy()
                output_data['generation_complete'] = True
                yield output_data
                return
                
            print(f"🔍 DEBUG: 准备处理周期 {current_cycle_index + 1}/{len(cycles)}")
                
            # 获取当前要处理的周期
            current_cycle = cycles[current_cycle_index]
            logger.info(f"🔄 开始处理第 {current_cycle_index + 1}/{len(cycles)} 个周期")
            logger.info(f"🔍 当前周期详细信息: {current_cycle}")
            print(f"🔍 DEBUG: 当前周期信息: {current_cycle}")
            
            cycle_start_date = current_cycle['start_date']
            cycle_end_date = current_cycle['end_date']
            cycle_total_days = current_cycle['total_days']
            
            logger.info(f"📅 周期日期范围: {cycle_start_date} - {cycle_end_date}, 共{cycle_total_days}天")
            print(f"📅 DEBUG: 日期范围: {cycle_start_date} - {cycle_end_date}, {cycle_total_days}天")
            
        except Exception as e:
            logger.error(f"❌ 日程生成节点初始化失败: {e}")
            print(f"❌ DEBUG: 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            raise e
        
        # 获取配置参数
        protagonist = input_data.get('protagonist', '穆昭')
        selected_characters = input_data.get('selected_characters', [])
        selected_locations = input_data.get('selected_locations', [])
        holidays_data = input_data.get('holidays_data', {})
        include_holidays = input_data.get('include_holidays', True)
        
        # 更新UI - 开始状态
        if workflow_chat:
            await workflow_chat.add_node_message(
                "日程生成",
                f"正在生成第 {current_cycle_index + 1}/{len(cycles)} 个周期的日程 ({cycle_start_date} - {cycle_end_date}, {cycle_total_days}天)...",
                "progress"
            )
                    
        # 获取当前周期的规划信息
        current_cycle_plan = current_cycle.get('cycle_theme', '')
        current_cycle_objectives = current_cycle.get('main_objectives', [])
        focus_characters = current_cycle.get('focus_characters', [])
        secondary_characters = current_cycle.get('secondary_characters', [])
        core_locations = current_cycle.get('core_locations', [])
        key_events = current_cycle.get('key_events', [])
        emotional_tone = current_cycle.get('emotional_tone', '')
        
        # 获取最近4个批次的summary作为历史记录
        recent_batch_summaries = await self._get_recent_batch_summaries(4, cycle_start_date)
        batch_history_context = ""
        logger.info(f"🔍 尝试获取历史批次总结，日期界限: {cycle_start_date}")
        logger.info(f"📋 获取到 {len(recent_batch_summaries)} 个历史批次总结:")
        for i, summary in enumerate(recent_batch_summaries):
            logger.info(f"  📝 总结 {i+1}: {summary[:150]}...")
        if recent_batch_summaries:
            batch_history_context = f"## 最近批次历史记录{chr(10)}{chr(10).join(recent_batch_summaries)}{chr(10)}"
            logger.info(f"✅ 历史记录上下文已构建，长度: {len(batch_history_context)} 字符")
        
        # 🔍 调试：确认代码继续执行
        print("🔍 DEBUG: 历史记录获取完成，继续执行...")
        logger.info("🔍 历史记录获取完成，继续执行...")
        
        # 分批生成：将周期分成3天一批
        batch_size = 3  # 每次生成3天
        cycle_daily_schedules = []  # 存储整个周期的日程
        current_batch_start = 0
        
        print(f"🔍 DEBUG: 准备分批生成，batch_size={batch_size}")
        logger.info(f"🔍 准备分批生成，batch_size={batch_size}")

        # 准备当前周期的所有日期信息
        cycle_dates_info = []
        print(f"🔍 DEBUG: cycle_dates_info 初始化完成，准备进入try块")
        logger.info(f"🔍 cycle_dates_info 初始化完成，准备进入try块")
        
        try:
            print("🔍 DEBUG: 进入日期解析try块")
            logger.info("🔍 进入日期解析try块")
            
            from datetime import datetime, timedelta
            
            print(f"🔍 DEBUG: 准备解析日期 - cycle_start_date={cycle_start_date}, cycle_end_date={cycle_end_date}")
            logger.info(f"🔍 准备解析日期 - cycle_start_date={cycle_start_date}, cycle_end_date={cycle_end_date}")
            
            # 解析周期日期范围
            cycle_start = datetime.strptime(cycle_start_date, '%Y-%m-%d')
            cycle_end = datetime.strptime(cycle_end_date, '%Y-%m-%d')
            
            logger.info(f"📅 解析的日期范围: {cycle_start} - {cycle_end}")
            print(f"📅 DEBUG: 解析的日期范围成功: {cycle_start} - {cycle_end}")
            
            # 获取周期内的所有日期信息
            current_date = cycle_start
            day_number = 1
            print(f"🔍 DEBUG: 开始生成日期，从 {cycle_start} 到 {cycle_end}")
            while current_date <= cycle_end:
                date_str = current_date.strftime('%Y-%m-%d')
                weekday = current_date.weekday()
                weekday_name = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][weekday]
            
                # 检查是否节假日
                is_holiday = False
                holiday_name = ""
                if include_holidays and date_str in holidays_data:
                    is_holiday = True
                    holiday_name = holidays_data[date_str]['name']
            
                # 添加日期信息
                cycle_dates_info.append({
                    'date': date_str,
                    'weekday': weekday,
                    'weekday_name': weekday_name,
                    'is_holiday': is_holiday,
                    'holiday_name': holiday_name,
                    'day_number': day_number,  # 周期内的天数
                    'cycle_day_number': day_number
                })
                
                print(f"  📅 DEBUG: 添加日期 {date_str} ({weekday_name})")
                
                current_date += timedelta(days=1)
                day_number += 1
                
            logger.info(f"📊 生成了 {len(cycle_dates_info)} 天的日期信息")
            if cycle_dates_info:
                logger.info(f"📅 第一天: {cycle_dates_info[0]}")
                logger.info(f"📅 最后一天: {cycle_dates_info[-1]}")
                
        except Exception as e:
            print(f"❌ DEBUG: 周期日期处理失败 - 异常类型: {type(e).__name__}, 错误信息: {str(e)}")
            logger.error(f"周期日期处理失败: {e}")
            import traceback
            traceback.print_exc()
            logger.error(traceback.format_exc())
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "日程生成",
                    f"周期日期处理失败: {str(e)}",
                    "error"
                )
            raise Exception(f"周期日期处理失败: {str(e)}")
            
        # 🔍 关键调试：检查while循环条件
        print(f"🔍 DEBUG: 日期解析完成，准备检查while循环条件")
        logger.info(f"🔍 DEBUG: 日期解析完成，准备检查while循环条件")
        
        logger.info(f"🔍 while循环条件检查:")
        logger.info(f"  current_batch_start: {current_batch_start}")
        logger.info(f"  len(cycle_dates_info): {len(cycle_dates_info)}")
        logger.info(f"  循环条件 current_batch_start < len(cycle_dates_info): {current_batch_start < len(cycle_dates_info)}")
        
        print(f"🔍 DEBUG: 检查cycle_dates_info长度")
        print(f"  len(cycle_dates_info) = {len(cycle_dates_info)}")
        print(f"  current_batch_start = {current_batch_start}")
        
        if len(cycle_dates_info) == 0:
            print("❌ DEBUG: cycle_dates_info 为空！")
            logger.error("❌ cycle_dates_info 为空，无法进行批次生成")
            raise Exception("cycle_dates_info 为空，无法进行批次生成")
        
        print(f"🔍 DEBUG: 准备进入while循环")
        logger.info(f"🔍 准备进入while循环")
            
        # 分批生成当前周期的日程
        batch_count = 0
        while current_batch_start < len(cycle_dates_info):
            batch_count += 1
            print(f"🔄 DEBUG: 进入while循环，批次 {batch_count}")
            logger.info(f"🔄 开始第 {batch_count} 个批次，current_batch_start = {current_batch_start}")
            
            print(f"🔍 DEBUG: 步骤1 - 确定批次日期范围")
            # 确定当前批次的日期范围
            batch_end = min(current_batch_start + batch_size, len(cycle_dates_info))
            batch_dates = cycle_dates_info[current_batch_start:batch_end]
            batch_days_count = len(batch_dates)
            
            batch_start_date = batch_dates[0]['date']
            batch_end_date = batch_dates[-1]['date']
            
            print(f"🔍 DEBUG: 步骤2 - 日期范围确定完成: {batch_start_date} - {batch_end_date}")
            logger.info(f"📅 批次 {batch_count} 日期范围: {batch_start_date} - {batch_end_date}, {batch_days_count}天")
            
            print(f"🔍 DEBUG: 步骤3 - 准备更新UI")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "日程生成",
                    f"正在生成第 {current_batch_start//batch_size + 1} 批次：{batch_start_date} - {batch_end_date} ({batch_days_count}天)",
                    "progress"
                )
            print(f"🔍 DEBUG: 步骤4 - UI更新完成")
        
            print(f"🔍 DEBUG: 步骤5 - 开始收集角色信息")
            # 收集所有可用角色信息（完整信息，不省略）
            char_list = input_data.get('characters_data', {}).get("角色列表", {})
            
            print(f"🔍 DEBUG: 步骤6 - 角色列表获取完成，包含 {len(char_list)} 个角色")
            
            # 收集批次角色信息
            all_batch_characters = set()
            
            # 优先使用周期推荐的重点角色
            if focus_characters:
                all_batch_characters.update(focus_characters)
            if secondary_characters:
                all_batch_characters.update(secondary_characters)
            
            # 补充其他选中的角色
            all_batch_characters.update(selected_characters)
            
            # 确保有足够的角色（最少5个）
            all_available_chars = [name for name in char_list.keys() if name != protagonist]
            while len(all_batch_characters) < min(5, len(all_available_chars)):
                for char_name in all_available_chars:
                    if char_name not in all_batch_characters:
                        all_batch_characters.add(char_name)
                        break
            
            all_batch_characters = list(all_batch_characters)
            logger.info(f"📋 批次角色池: {len(all_batch_characters)} 个角色")
            
            # 获取角色详细信息
            all_characters_info = []
            for char_name in all_batch_characters:
                if char_name in char_list:
                    char_info = char_list[char_name]
                    char_desc = f"{char_name}：{char_info.get('简介', '')}"
                    if char_info.get('性格'):
                        char_desc += f"，性格{char_info.get('性格')}"
                    if char_info.get('年龄'):
                        char_desc += f"，年龄{char_info.get('年龄')}"
                    if char_info.get('活动地点'):
                        char_desc += f"，主要活动地点：{', '.join(char_info.get('活动地点', []))}"
                    if char_info.get('可触发剧情'):
                        char_desc += f"，可触发剧情：{', '.join(char_info.get('可触发剧情', [])[:2])}"
                    all_characters_info.append(char_desc)
            
            # 获取主角信息
            protagonist_data = input_data.get('protagonist_data', '')
            print(f"🔍 DEBUG: 获取主角信息完成，长度: {len(protagonist_data)}")
            
            # 构建批次生成提示词
            print(f"🔍 DEBUG: 开始构建提示词...")
            print(f"  - batch_start_date: {batch_start_date}")
            print(f"  - batch_end_date: {batch_end_date}")
            print(f"  - batch_days_count: {batch_days_count}")
            print(f"  - protagonist: {protagonist}")
            print(f"  - len(all_characters_info): {len(all_characters_info)}")
            print(f"  - len(selected_locations): {len(selected_locations)}")
            print(f"  - len(batch_dates): {len(batch_dates)}")
            
            try:
                # 构建批次生成提示词：system纯指令，user动态数据
                system_generation_instructions = """# 核心生成要求
不做和星空，天文有关的计划
## 分批生成连贯性
1. **批次衔接**：虽然只生成指定天数，但要与前后批次自然衔接
2. **周期目标推进**：在这几天中推进当前周期的目标和主题

## 云枢市真实生活感
1. **日常随机事件**：偶遇熟人、发现新店铺、小意外、天气变化等生活化元素
2. **城市生活细节**：街边小店、咖啡馆、公园散步、菜市场、公交地铁、社区活动等
3. **季节节日氛围**：根据季节和节假日安排应景的活动和氛围
4. **生活化互动**：购物、用餐、休闲娱乐、运动健身、读书学习等日常活动
5. **避免设定**：严禁涉及天文、星空、宇宙等主题，重点突出都市生活的烟火气
6. 不出现和其他角色强相关的安排，以独立个人计划为主

## 故事性要求
1. **情感推进**：每个角色的出现都应该有关系发展，推进周期主题
2. **细节丰富度**：每个时间段的描述包含具体的对话片段、内心活动、环境描写
3. **事件连贯性**：当前批次内的事件要相互呼应，形成完整的故事片段
4. **生活真实感**：包含工作压力、情绪波动、小确幸、意外惊喜等真实元素

## 计划与总结的区别
- **每日计划(daily_plan)**：主角对这一天的预期和安排，基于他现有的信息和经验
- **每日总结(daily_summary)**：一天结束后对实际发生事件的回顾，可能与计划有出入，包含意外和惊喜
- **批次总结(batch_summary)**：几天结束后的阶段性总结，关注这几天的重要发展

## 时间段内容要求
1. **夜间(23:00-06:00)**：休息、梦境、深夜思考，偶尔有特殊情况
2. **上午(06:00-11:00)**：工作、研究、重要会议，精神状态最佳的时段
3. **中午(11:00-14:00)**：用餐、轻松社交、短暂休息
4. **下午(14:00-18:00)**：继续工作、实地考察、学术活动
5. **晚上(18:00-23:00)**：社交活动、娱乐、个人时间、深度交流

## 独立故事要求
1. **时间段故事独立性**：每个时间段的故事内容必须是独立完整的，能够单独阅读理解
2. **前因后果清晰**：即使是独立的时间段故事，也要描述清楚事件的前因后果
3. **情境完整性**：包含明确的场景、人物、对话和情感描述，保证内容的完整性
4. **独立叙事**：每个时间段内容可能被单独提取使用，因此必须是自包含的完整故事
5. **上下文连贯**：虽然是独立的，但各时间段之间应该有连贯的关系，形成日常生活的完整画面

# 重要提醒
1. **分批生成要求**：
   - 只生成指定天数的日程，不要生成整个周期
   - 要体现周期规划的主题和目标，但重点是当前批次
   - 要为后续批次留下自然的衔接点

2. **数据完整性要求**：
   - daily_plan：每天都要有具体的早晨计划
   - daily_involved_characters：必须列出当天所有出现的有配置的角色名称
   - 每天必须有5个完整的时间段（夜间、上午、中午、下午、晚上）
   - involved_characters：每个时间段都要明确列出涉及的角色名称列表
   - batch_summary：必须包含这几天的阶段性总结

3. **日程内容要求**：
   - 每个时间段的schedule_content必须简洁明确，重点记录实际活动
   - 各时间段内容独立完整，明确记录时间地点人员活动目的
   - 内容真实具体，避免虚构情节和不必要的描述
   - 可包含日常生活的真实元素：工作安排、社交活动、生活琐事、工作压力、小确幸、意外惊喜等真实元素
   - 禁止有任何男女恋爱元素
   - 严禁涉及天文、星空、宇宙等主题，重点体现普通都市生活
   - 体现云枢市的生活节奏：工作、用餐、社交、休闲、节日活动等日常安排

4. **角色处理要求**：
   - 重点角色要多安排，体现周期主题
   - 其他角色根据生活逻辑自然出现
   - 可以创造临时角色（如店主、路人、小动物）增加真实感
   - involved_characters中只需列出角色名称，不需要描述

5. **技术要求**：
   - 确保JSON格式完全正确，可以被程序解析
   - 每个字段都要填写完整，不能为空
   - 关注batch_summary字段，它是本批次的重要总结
   - 输出的内容中禁止包含""和\，人物对话直接用:衔接即可

禁止输入任何其他内容。

# 输出格式
请按以下JSON格式输出批次日程安排，必须附加markdown标识，禁止输出任何其他内容：

```json
{
  "batch_info": {
    "批次天数": <int>,
    "批次开始日期": "YYYY-MM-DD",
    "批次结束日期": "YYYY-MM-DD",
    "所属周期": <int>,
    "周期主题": "string",
    "批次特点": "描述这几天的主要特色和故事发展",
    "重点角色": ["string"],
    "主要地点": ["string"]
  },

  "daily_schedules": [
    {
      "date": "YYYY-MM-DD",
      "day_number": 1,
      "weekday_name": "周几",
      "is_holiday": true/false,
      "holiday_name": "节日名称（如果是节假日）",
      "weather": "天气情况",
      "daily_plan": "穆昭的计划安排，第三人称以他为主体描述当天的具体打算，200-300字，包含：主要目标、具体安排、期望收获",
      "daily_involved_characters": ["无", "无", "角色名3"],
      "time_slots": [
        {
          "slot_name": "夜间",
          "location": "具体地点",
          "schedule_content": "具体的日程安排记录：时间+具体地点+具体活动+目的，涉及的实体的细节。简洁明确，80-200字。",
          "involved_characters": ["无", "无"]
        },
        {
          "slot_name": "上午",
          "location": "具体地点",
          "schedule_content": "具体的日程安排记录：早晨需要符合主角饮食习惯的饮食细节，时间+地点+具体活动+目的，涉及的实体的细节。简洁明确，80-200字。",
          "involved_characters": ["无", "无"]
        },
        {
          "slot_name": "中午",
          "location": "具体地点",
          "schedule_content": "具体的日程安排记录：符合主角饮食习惯的饮食细节，时间+地点+具体活动+目的，涉及的实体的细节。简洁明确，80-200字。",
          "involved_characters": ["无", "无"]
        },
        {
          "slot_name": "下午",
          "location": "具体地点",
          "schedule_content": "具体的日程安排记录：时间+具体地点+参与人员+目的，涉及的实体的细节。简洁明确，80-200字。",
          "involved_characters": ["无", "无"]
        },
        {
          "slot_name": "晚上",
          "location": "具体地点",
          "schedule_content": "具体的日程安排记录：符合主角饮食习惯的饮食细节，时间+具体地点+具体活动+目的，涉及的实体的细节。简洁明确，80-200字。",
          "involved_characters": ["无", "无"]
        }
      ],
      "daily_summary": "第三人称，以角色名为主体，一天结束时的简要总结，200-300字，重点关注：重要事件、人物互动、心情变化、发现思考"
    }
  ],
  "batch_summary": "这几天的重要发展总结，包含目标推进和关系变化，150-200字"
}
```"""

                user_generation_dynamic = f"""你是一名专业的日程规划师和故事编剧，需要为主角{protagonist}生成{batch_start_date}到{batch_end_date}的详细日程安排（共{batch_days_count}天）。

这是一个分批渐进式生成任务，当前生成的是一个更大周期中的一部分。

# 主角信息
{protagonist_data}

{batch_history_context if batch_history_context else ''}

# 当前周期规划背景
## 周期信息
- 周期日期：{cycle_start_date} 至 {cycle_end_date}（第{current_cycle_index + 1}个周期，共{len(cycles)}个周期）
- 周期主题：{current_cycle_plan}
- 情感基调：{emotional_tone}

## 周期目标
{chr(10).join([f"- {obj}" for obj in current_cycle_objectives])}

## 核心地点（本周期）
{chr(10).join([f"- {loc}" for loc in core_locations])}

## 关键事件（本周期预期）
{chr(10).join([f"- {event}" for event in key_events])}

# 当前批次任务
- 批次日期：{batch_start_date} 至 {batch_end_date}
- 批次天数：{batch_days_count}天
- 这是当前周期的第 {current_batch_start//batch_size + 1} 个批次
- 每天划分为5个时间段：夜间(23:00-06:00)、上午(06:00-11:00)、中午(11:00-14:00)、下午(14:00-18:00)、晚上(18:00-23:00)

# 可用地点
{', '.join(selected_locations)}

# 批次日期信息
{json.dumps(batch_dates, ensure_ascii=False, indent=2)}"""
                
                print(f"🔍 DEBUG: 提示词构建完成，user长度: {len(user_generation_dynamic)}")
                logger.info(f"🚀 即将调用LLM生成批次 {batch_count}")
                logger.info(f"📝 user动态长度: {len(user_generation_dynamic)} 字符")
                logger.info(f"🤖 LLM 对象: {llm}")
                
                if not llm:
                    raise Exception("LLM对象未初始化")
                
                # 调用LLM生成批次日程（system 纯指令 + user 动态资料）
                from core.types import Message, MessageRole
                messages = [
                    Message(role=MessageRole.SYSTEM, content=system_generation_instructions),
                    Message(role=MessageRole.USER, content=user_generation_dynamic)
                ]
                
                print(f"🚀 DEBUG: 开始调用LLM流式生成...")
                
                final_content = ""
                chunk_count = 0
                async for chunk_data in llm.stream_generate(
                    messages, 
                    mode="think",
                    return_dict=True
                ):
                    chunk_count += 1
                    content_part = chunk_data.get("content", "")
                    final_content += content_part
                    
                    # 每100个chunk更新一次进度
                    if chunk_count % 100 == 0:
                        print(f"🔄 DEBUG: 已接收 {chunk_count} 个chunk，当前内容长度: {len(final_content)}")
                
                print(f"✅ DEBUG: LLM生成完成，总chunk数: {chunk_count}，最终内容长度: {len(final_content)}")
                logger.info(f"📝 批次 {batch_count} 生成完成，内容长度: {len(final_content)} 字符")
                
                # 保存原始回复到TXT文件
                await self._save_raw_response_to_txt(final_content, current_cycle_index + 1, batch_count, batch_start_date, batch_end_date)
                
            except Exception as prompt_error:
                logger.error(f"❌ 提示词构建或LLM调用失败: {prompt_error}")
                print(f"❌ DEBUG: 提示词构建或LLM调用失败: {prompt_error}")
                import traceback
                traceback.print_exc()
                
                # 继续处理下一个批次，不要因为一个批次失败就停止
                current_batch_start += batch_size
                continue
            
            # 解析JSON结果
            batch_data = None
            try:
                from parsers.json_parser import JSONParser
                parser = JSONParser()
                
                json_content = self._extract_json_from_content(final_content)
                logger.info(f"🔍 提取的JSON内容长度: {len(json_content)}")
                
                parsed_result = parser.parse(json_content)
                
                if parsed_result and 'daily_schedules' in parsed_result:
                    batch_data = parsed_result
                    logger.info(f"✅ 成功解析批次JSON，包含 {len(batch_data['daily_schedules'])} 天日程")
                else:
                    raise Exception("解析结果缺少daily_schedules字段")
                    
            except Exception as parse_error:
                logger.error(f"❌ 批次JSON解析失败: {parse_error}")
                
                # 创建基础的批次数据作为后备
                batch_data = {
                    'batch_summary': f"批次{batch_count}：{batch_start_date}至{batch_end_date}的日程（解析失败）",
                    'daily_schedules': []
                }
                
                
                if workflow_chat:
                    await workflow_chat.add_node_message(
                        "日程生成",
                        f"⚠️ 批次 {batch_count} JSON解析失败，使用基础结构继续",
                        "warning"
                    )
            
            # 保存批次JSON数据到TXT
            await self._save_batch_json_to_txt(batch_data, current_cycle_index + 1, batch_count, batch_start_date, batch_end_date)
            
            # 增量保存到CSV
            batch_daily_schedules = batch_data.get('daily_schedules', [])
            await self._save_batch_to_csv_incrementally(batch_daily_schedules, batch_data, current_cycle_index + 1, batch_count, current_cycle)
            
            # 将批次日程添加到周期日程中
            cycle_daily_schedules.extend(batch_daily_schedules)
            
            # 更新UI进度
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "日程生成", 
                    f"✅ 批次 {batch_count} 完成：{batch_start_date} - {batch_end_date} ({len(batch_daily_schedules)}天)",
                    "success"
                )
            
            # 更新批次进度
            current_batch_start += batch_size
        
        # 当前周期所有批次生成完成，构建周期结果
        logger.info(f"📋 周期 {current_cycle_index + 1} 所有批次完成，准备构建周期结果")
        
        # 生成周期总结
        cycle_summary = ""
        if cycle_daily_schedules:
            try:
                current_cycle_info = {
                    'cycle_number': current_cycle_index + 1,
                    'cycle_theme': current_cycle_plan,
                    'main_objectives': current_cycle_objectives,
                    'focus_characters': focus_characters
                }
                cycle_summary = await self._generate_cycle_summary(current_cycle_info, cycle_daily_schedules, llm, workflow_chat)
            except Exception as summary_error:
                logger.error(f"生成周期总结失败: {summary_error}")
                cycle_summary = f"周期{current_cycle_index + 1}完成，共{len(cycle_daily_schedules)}天，主题：{current_cycle_plan}。"
        
        # 构建周期数据
        schedule_data = {
            'cycle_info': {
                'cycle_number': current_cycle_index + 1,
                'start_date': cycle_start_date,
                'end_date': cycle_end_date,
                'total_days': cycle_total_days,
                'cycle_theme': current_cycle_plan,
                'cycle_plan': current_cycle.get('cycle_plan', f"周期{current_cycle_index + 1}主题：{current_cycle_plan}"),  # 添加详细周期计划
                'focus_characters': focus_characters,
                'core_locations': core_locations
            },
            'daily_schedules': cycle_daily_schedules,
            'cycle_summary': cycle_summary
        }
        
        # 立即保存周期到CSV
        await self._save_cycle_to_csv_immediately(schedule_data, current_cycle_index + 1)
        
        # 更新UI
        if workflow_chat:
            await workflow_chat.add_node_message(
                "日程生成",
                f"✅ 周期 {current_cycle_index + 1} 完成：共生成 {len(cycle_daily_schedules)} 天日程",
                "success"
            )
        
        # 更新输出数据
        output_data = input_data.copy()
        output_data['schedule_result'] = schedule_data
        output_data['daily_schedules'] = cycle_daily_schedules
        output_data['current_cycle_index'] = current_cycle_index + 1  # 指向下一个周期
        
        # 检查是否所有周期都完成了
        if current_cycle_index + 1 >= len(cycles):
            output_data['generation_complete'] = True
            logger.info(f"✅ 所有 {len(cycles)} 个周期生成完成")
            print(f"✅ DEBUG: 所有周期完成标记已设置")
        else:
            logger.info(f"✅ 周期 {current_cycle_index + 1} 完成，准备下一个周期")
            print(f"✅ DEBUG: 当前周期完成，准备下一个周期")
        
        print(f"✅ 周期 {current_cycle_index + 1} 日程生成完成")
        print(f"🔍 DEBUG: 准备yield输出数据")
        yield output_data
        print(f"🔍 DEBUG: yield完成")
    
    async def _save_batch_to_csv_incrementally(self, batch_daily_schedules: List[Dict], batch_data: Dict, cycle_number: int, batch_number: int, current_cycle: Dict):
        """每3天批次完成后增量保存到CSV（主要输出文件）"""
        try:
            from pathlib import Path
            import csv
            import os
            from datetime import datetime
            
            # 创建输出目录
            output_dir = Path("workspace/batch_schedule_output")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用固定文件名进行增量保存（主要输出）
            csv_file_path = output_dir / "batch_schedules_raw.csv"
            
            # 定义CSV列头（与batch_schedule_generator.py保持一致）
            csv_headers = [
                "日期", "星期", "节日信息", "季节", "天气", "主题", 
                "周期计划", "批次总结", "每日计划", "每日总结", "涉及角色", "角色简介",
                "上午", "中午", "下午", "晚上", "夜间"
            ]
            
            # 获取周期和批次信息
            cycle_theme = current_cycle.get('cycle_theme', '')
            cycle_plan = current_cycle.get('cycle_plan', f"周期{cycle_number}主题：{cycle_theme}")  # 详细的周期计划
            batch_summary = batch_data.get('batch_summary', '')  # 使用LLM生成的批次总结
            
            # 检查文件是否存在，决定是追加还是创建新文件
            file_exists = csv_file_path.exists()
            write_mode = 'a' if file_exists else 'w'
            
            logger.info(f"🔄 {'追加' if file_exists else '创建'}批次CSV: 周期{cycle_number}, 批次{batch_number}, 包含{len(batch_daily_schedules)}天")
            if batch_summary:
                logger.info(f"📝 批次总结: {batch_summary[:100]}...")
            
            # 写入CSV文件（增量保存）
            with open(csv_file_path, write_mode, encoding='utf-8', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # 只在文件不存在时写入表头
                if not file_exists:
                    writer.writerow(csv_headers)
                
                # 遍历每天的日程数据
                for day_index, day_data in enumerate(batch_daily_schedules):
                    date = day_data.get('date', '')
                    weekday = day_data.get('weekday_name', '')
                    weather = day_data.get('weather', '')
                    is_holiday = day_data.get('is_holiday', False)
                    holiday_name = day_data.get('holiday_name', '')
                    
                    # 节日信息处理
                    holiday_info = holiday_name if is_holiday and holiday_name else "无"
                    
                    # 根据日期确定季节
                    season = self._get_season_from_date(date)
                    
                    daily_plan = day_data.get('daily_plan', '')
                    daily_summary = day_data.get('daily_summary', '')
                    
                    # 提取每日涉及角色信息
                    daily_involved_characters = day_data.get('daily_involved_characters', [])
                    daily_characters_info = ''
                    
                    # 从时间段中自动提取角色信息（如果daily_involved_characters为空）
                    if not daily_involved_characters:
                        time_slot_chars = set()
                        for slot in day_data.get('time_slots', []):
                            involved_chars = slot.get('involved_characters', [])
                            time_slot_chars.update(involved_chars)
                        daily_involved_characters = list(time_slot_chars)
                    
                    # 生成角色简介信息（简化版，因为工作流内部没有完整角色数据）
                    if daily_involved_characters:
                        daily_characters_info = '；'.join([f"{char}-角色简介" for char in daily_involved_characters])
                    
                    # 初始化时间段数据
                    time_slots_data = {
                        '上午': '',
                        '中午': '', 
                        '下午': '',
                        '晚上': '',
                        '夜间': ''
                    }
                    
                    # 提取时间段数据
                    time_slots = day_data.get('time_slots', [])
                    for slot in time_slots:
                        slot_name = slot.get('slot_name', '')
                        if slot_name in time_slots_data:
                            time_slots_data[slot_name] = slot.get('schedule_content', '')
                    
                    # 批次总结：只在第一天显示批次总结，其他天为空
                    day_batch_summary = ""
                    if day_index == 0:  # 第一天显示批次总结
                        day_batch_summary = batch_summary
                    
                    # 构建CSV行数据
                    row_data = [
                        date,                          # 日期
                        weekday,                       # 星期
                        holiday_info,                  # 节日信息
                        season,                        # 季节
                        weather,                       # 天气
                        cycle_theme,                   # 主题
                        cycle_plan,                    # 周期计划
                        day_batch_summary,             # 批次总结
                        daily_plan,                    # 每日计划
                        daily_summary,                 # 每日总结
                        ', '.join(daily_involved_characters),  # 涉及角色
                        daily_characters_info,         # 角色简介
                        time_slots_data['上午'],        # 上午
                        time_slots_data['中午'],        # 中午
                        time_slots_data['下午'],        # 下午
                        time_slots_data['晚上'],        # 晚上
                        time_slots_data['夜间']         # 夜间
                    ]
                    
                    writer.writerow(row_data)
            
            logger.info(f"✅ 批次CSV{'追加' if file_exists else '保存'}成功: {csv_file_path}")
            logger.info(f"📊 本次添加: {len(batch_daily_schedules)}天日程数据")
            
        except Exception as e:
            logger.error(f"❌ 保存批次CSV失败: 周期{cycle_number}, 批次{batch_number}, 错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _save_batch_json_to_txt(self, batch_data: Dict, cycle_number: int, batch_number: int, start_date: str, end_date: str):
        """保存每3天批次的JSON数据到TXT文件（方便错误时手动解析）"""
        try:
            from pathlib import Path
            from datetime import datetime
            import json
            
            # 创建输出目录
            output_dir = Path("workspace/batch_schedule_output_raw")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用固定文件名进行增量保存
            txt_file_path = output_dir / "batch_json_data.txt"
            
            # 构建格式化的JSON内容
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            separator = "=" * 80
            
            # 美化JSON格式
            formatted_json = json.dumps(batch_data, ensure_ascii=False, indent=2)
            
            formatted_content = f"""
{separator}
批次JSON数据: 周期{cycle_number}-批次{batch_number} | 日期范围: {start_date} 至 {end_date}
保存时间: {timestamp}
数据完整性: {len(batch_data.get('daily_schedules', []))}天日程, 批次总结{len(batch_data.get('batch_summary', ''))}字符
{separator}

{formatted_json}

{separator}
批次JSON结束: 周期{cycle_number}-批次{batch_number}
{separator}

"""
            
            # 增量追加到文件
            with open(txt_file_path, 'a', encoding='utf-8') as f:
                f.write(formatted_content)
            
            logger.info(f"✅ 批次JSON数据已保存到TXT: 周期{cycle_number}-批次{batch_number}")
            logger.info(f"📄 文件路径: {txt_file_path}")
            
        except Exception as e:
            logger.error(f"保存批次JSON数据到TXT失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
    async def _save_cycle_to_csv_immediately(self, schedule_data: Dict[str, Any], cycle_number: int):
        """周期完成后立即保存到CSV（增量更新）"""
        try:
            from pathlib import Path
            import csv
            import os
            
            # 创建输出目录
            output_dir = Path("workspace/batch_schedule_output")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用固定CSV文件名，便于增量更新
            csv_file_path = output_dir / "batch_schedules.csv"
            
            # 定义CSV列头
            csv_headers = [
                "日期", "星期", "节日信息", "季节", "天气", "主题", 
                "周期计划", "批次总结", "每日计划", "每日总结", "涉及角色", "角色简介",
                "上午", "中午", "下午", "晚上", "夜间"
            ]
            
            # 检查文件是否存在，决定是追加还是创建新文件
            file_exists = csv_file_path.exists()
            write_mode = 'a' if file_exists else 'w'
            
            # 获取周期信息
            cycle_info = schedule_data.get('cycle_info', {})
            cycle_theme = cycle_info.get('cycle_theme', '')
            cycle_plan = cycle_info.get('cycle_plan', f"周期计划：{cycle_theme}")  # 使用详细的周期计划
            daily_schedules = schedule_data.get('daily_schedules', [])
            
            # 写入CSV文件
            with open(csv_file_path, write_mode, encoding='utf-8', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # 只在文件不存在时写入表头
                if not file_exists:
                    writer.writerow(csv_headers)
                
                # 处理批次总结：从schedule_data中获取，而不是自动生成
                cycle_summary = schedule_data.get('cycle_summary', '')
                
                # 遍历每天的日程数据
                for day_index, day_data in enumerate(daily_schedules):
                    date = day_data.get('date', '')
                    weekday = day_data.get('weekday_name', '')
                    weather = day_data.get('weather', '')
                    is_holiday = day_data.get('is_holiday', False)
                    holiday_name = day_data.get('holiday_name', '')
                    
                    # 节日信息处理
                    holiday_info = holiday_name if is_holiday and holiday_name else "无"
                    
                    # 根据日期确定季节
                    season = self._get_season_from_date(date)
                    
                    daily_plan = day_data.get('daily_plan', '')
                    daily_summary = day_data.get('daily_summary', '')  # 每日总结
                    
                    # 提取每日涉及角色信息
                    daily_involved_characters = day_data.get('daily_involved_characters', [])
                    daily_characters_info = day_data.get('daily_characters_info', '')
                    
                    # 如果没有提供字符串格式的角色信息，则自动生成
                    if not daily_characters_info and daily_involved_characters:
                        # 从角色数据中获取简介（这里需要传入角色数据）
                        char_infos = []
                        for char_name in daily_involved_characters:
                            char_infos.append(f"{char_name}-简介待补充")  # 简化处理
                        daily_characters_info = '；'.join(char_infos)
                    
                    # 初始化时间段数据
                    time_slots_data = {
                        '上午': '',
                        '中午': '', 
                        '下午': '',
                        '晚上': '',
                        '夜间': ''
                    }
                    
                    # 提取时间段数据
                    time_slots = day_data.get('time_slots', [])
                    for slot in time_slots:
                        slot_name = slot.get('slot_name', '')
                        if slot_name in time_slots_data:
                            time_slots_data[slot_name] = slot.get('schedule_content', '')
                    
                    # 批次总结：只在周期的第一天显示周期总结，其他天为空
                    day_cycle_summary = ""
                    if day_index == 0:  # 周期的第一天显示周期总结
                        day_cycle_summary = cycle_summary
                    
                    # 构建CSV行数据
                    row_data = [
                        date,                          # 日期
                        weekday,                       # 星期
                        holiday_info,                  # 节日信息
                        season,                        # 季节
                        weather,                       # 天气
                        cycle_theme,                   # 主题
                        cycle_plan,                    # 周期计划
                        day_cycle_summary,             # 批次总结
                        daily_plan,                    # 每日计划
                        daily_summary,                 # 每日总结
                        ', '.join(daily_involved_characters),  # 涉及角色
                        daily_characters_info,         # 角色简介
                        time_slots_data['上午'],        # 上午
                        time_slots_data['中午'],        # 中午
                        time_slots_data['下午'],        # 下午
                        time_slots_data['晚上'],        # 晚上
                        time_slots_data['夜间']         # 夜间
                    ]
                    
                    writer.writerow(row_data)
            
            logger.info(f"周期 {cycle_number} CSV数据已{'追加到' if file_exists else '保存为新'}文件: {csv_file_path}")
            
        except Exception as e:
            logger.error(f"保存周期 {cycle_number} CSV文件失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def _save_raw_response_to_txt(self, raw_content: str, cycle_number: int, batch_number: int, start_date: str, end_date: str):
        """增量保存LLM原始回复到TXT文件，保留格式便于后期解析"""
        try:
            from pathlib import Path
            from datetime import datetime
            
            # 创建输出目录
            output_dir = Path("workspace/batch_schedule_output")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用固定文件名进行增量保存
            txt_file_path = output_dir / "raw_llm_responses.txt"
            
            # 构建格式化的回复内容
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            separator = "=" * 80
            
            formatted_content = f"""
{separator}
批次信息: 周期{cycle_number}-批次{batch_number} | 日期范围: {start_date} 至 {end_date}
保存时间: {timestamp}
{separator}

{raw_content}

{separator}
批次结束: 周期{cycle_number}-批次{batch_number}
{separator}

"""
            
            # 增量追加到文件
            with open(txt_file_path, 'a', encoding='utf-8') as f:
                f.write(formatted_content)
            
            logger.info(f"✅ 原始回复已保存到TXT: 周期{cycle_number}-批次{batch_number}, 内容长度: {len(raw_content)} 字符")
            
        except Exception as e:
            logger.error(f"保存原始回复到TXT失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _get_season_from_date(self, date_str: str) -> str:
        """根据日期确定季节"""
        try:
            from datetime import datetime
            date = datetime.strptime(date_str, '%Y-%m-%d')
            month = date.month
            
            if month in [12, 1, 2]:
                return '冬季'
            elif month in [3, 4, 5]:
                return '春季'
            elif month in [6, 7, 8]:
                return '夏季'
            elif month in [9, 10, 11]:
                return '秋季'
            else:
                return '未知'
        except:
            return '未知'
    
    async def _get_recent_batch_summaries(self, count: int, before_date: str) -> List[str]:
        """获取最近4个批次的summary作为历史记录 - 跨周期跨批次记忆"""
        try:
            import csv
            import os
            from pathlib import Path
            from datetime import datetime
             
            print(f"🔍 DEBUG: 开始获取历史批次总结，before_date={before_date}")
            
            # 从CSV文件读取最近的批次总结
            csv_file_path = Path("workspace/batch_schedule_output/batch_schedules.csv")
            print(f"🔍 DEBUG: 查找CSV文件: {csv_file_path}")
            logger.info(f"🔍 查找CSV文件: {csv_file_path}")
            
            if not csv_file_path.exists():
                print("❌ DEBUG: CSV文件不存在，返回空历史记录")
                logger.info("❌ CSV文件不存在，返回空历史记录")
                return []
            
            print(f"✅ DEBUG: CSV文件存在，文件大小: {csv_file_path.stat().st_size} 字节")
            logger.info(f"✅ CSV文件存在，文件大小: {csv_file_path.stat().st_size} 字节")
            
            # 解析before_date为datetime对象
            try:
                before_dt = datetime.strptime(before_date, '%Y-%m-%d')
                print(f"🔍 DEBUG: 解析before_date成功: {before_dt}")
            except Exception as date_error:
                logger.error(f"日期解析失败: {date_error}")
                print(f"❌ DEBUG: 日期解析失败: {date_error}")
                return []
            
            # 读取CSV文件并收集批次总结
            batch_summaries = []
            unique_summaries = set()  # 避免重复
            
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.DictReader(f)
                
                for row in csv_reader:
                    try:
                        # 获取行数据
                        row_date_str = row.get('日期', '').strip()
                        batch_summary = row.get('批次总结', '').strip()
                        
                        # 跳过空的日期或总结
                        if not row_date_str or not batch_summary:
                            continue
                        
                        # 解析行日期
                        row_date = datetime.strptime(row_date_str, '%Y-%m-%d')
                        
                        # 只考虑before_date之前的记录
                        if row_date >= before_dt:
                            continue
                        
                        # 避免重复的总结（同一个批次会有多行相同的总结）
                        if batch_summary in unique_summaries:
                            continue
                        
                        unique_summaries.add(batch_summary)
                        batch_summaries.append({
                            'date': row_date,
                            'summary': batch_summary
                        })
                        
                    except Exception as row_error:
                        # 跳过有问题的行
                        continue
            
            # 按日期降序排序，获取最近的count个总结
            batch_summaries.sort(key=lambda x: x['date'], reverse=True)
            recent_summaries = batch_summaries[:count]
            
            # 提取总结文本
            summary_texts = [item['summary'] for item in recent_summaries]
            
            print(f"✅ DEBUG: 成功获取 {len(summary_texts)} 个历史批次总结")
            logger.info(f"✅ 成功获取 {len(summary_texts)} 个历史批次总结")
            
            # 打印总结预览
            for i, summary in enumerate(summary_texts):
                preview = summary[:100] + "..." if len(summary) > 100 else summary
                print(f"  📝 总结 {i+1}: {preview}")
                logger.info(f"  📝 总结 {i+1}: {preview}")
            
            return summary_texts
            
        except Exception as e:
            print(f"❌ DEBUG: 获取历史批次总结失败: {e}")
            logger.error(f"获取历史批次总结失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _generate_cycle_summary(self, cycle_info: Dict, daily_schedules: List[Dict], llm, workflow_chat) -> str:
        """生成周期总结"""
        try:
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "日程生成",
                    "正在生成周期总结...",
                    "progress"
                )
            
            # 提取周期关键信息
            cycle_theme = cycle_info.get('cycle_theme', '')
            objectives = cycle_info.get('main_objectives', [])
            focus_characters = cycle_info.get('focus_characters', [])
            
            # 统计各角色出现次数
            character_stats = {}
            location_stats = {}
            
            for day in daily_schedules:
                for slot in day.get('time_slots', []):
                    # 统计角色
                    chars = slot.get('involved_characters', [])
                    for char in chars:
                        character_stats[char] = character_stats.get(char, 0) + 1
                    
                    # 统计地点
                    location = slot.get('location', '')
                    if location:
                        location_stats[location] = location_stats.get(location, 0) + 1
            
            # 构建总结提示词：system纯指令，user动态数据
            system_summary_instructions = """请生成一个第三人称的周期总结，重点关注：
1. 周期主题的体现和目标达成情况
2. 重点角色关系的发展变化
3. 主要活动和重要事件
4. 穆昭的饮食细节
5. 为下个周期的铺垫

要求：简洁明了，突出重点，400字以内。仅输出总结文本，不添加额外解释或多余内容。"""

            user_summary_dynamic = f"""根据以下信息，为这个周期生成一个简洁的总结（300字以内）：

## 周期信息
- 主题：{cycle_theme}
- 目标：{', '.join(objectives)}
- 重点角色：{', '.join(focus_characters)}
- 实际天数：{len(daily_schedules)}天

## 角色互动统计
{chr(10).join([f"- {char}: {count}次互动" for char, count in sorted(character_stats.items(), key=lambda x: x[1], reverse=True)[:5]])}

## 地点活动统计  
{chr(10).join([f"- {loc}: {count}次" for loc, count in sorted(location_stats.items(), key=lambda x: x[1], reverse=True)[:5]])}"""
            
            # 调用LLM生成总结（system 纯指令 + user 动态资料）
            from core.types import Message, MessageRole
            messages = [
                Message(role=MessageRole.SYSTEM, content=system_summary_instructions),
                Message(role=MessageRole.USER, content=user_summary_dynamic)
            ]
            
            summary_content = ""
            async for chunk_data in llm.stream_generate(messages, mode="normal", return_dict=True):
                summary_content += chunk_data.get("content", "")
            
            # 清理总结内容
            summary_content = summary_content.strip()
            if len(summary_content) > 500:
                summary_content = summary_content[:500] + "..."
            
            logger.info(f"周期总结生成完成，长度: {len(summary_content)} 字符")
            return summary_content
            
        except Exception as e:
            logger.error(f"生成周期总结失败: {e}")
            return f"周期{cycle_info.get('cycle_number', '')}完成，共{len(daily_schedules)}天，主题：{cycle_info.get('cycle_theme', '')}。"
        
    def _extract_json_from_content(self, content: str) -> str:
        """从生成内容中提取JSON部分 - 修复完整JSON提取"""
        import re
        import json

        
        logger.info(f"🔍 开始提取JSON，原始内容长度: {len(content)}")
        
        # 优先查找```json...```代码块
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            extracted_json = match.strip()
            if self._is_valid_json(extracted_json):
                logger.info(f"✅ 从```json```代码块提取有效JSON，长度: {len(extracted_json)}")
                return extracted_json

        # 方法2: 查找```...```代码块（不一定标注json）
        code_pattern = r'```[a-zA-Z]*\s*(.*?)\s*```'
        code_matches = re.findall(code_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in code_matches:
            extracted = match.strip()
            if extracted.startswith('{') and self._is_valid_json(extracted):
                logger.info(f"✅ 从代码块提取有效JSON，长度: {len(extracted)}")
                return extracted
        
        # 方法3: 使用括号匹配计数提取完整JSON
        def extract_complete_json(text):
            start_pos = text.find('{')
            if start_pos == -1:
                return None
            
            brace_count = 0
            in_string = False
            escape_next = False
            
            for i, char in enumerate(text[start_pos:], start_pos):
                if escape_next:
                    escape_next = False
                    continue
                    
                if char == '\\' and in_string:
                    escape_next = True
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                    
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return text[start_pos:i+1]
            
            return None
        
        complete_json = extract_complete_json(content)
        if complete_json and self._is_valid_json(complete_json):
            logger.info(f"✅ 使用括号匹配提取有效JSON，长度: {len(complete_json)}")
            return complete_json.strip()       
        # 方法4: 多重正则匹配后验证
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # 简单嵌套
            r'\{.*?\}',  # 贪婪匹配
            r'\{.*\}'    # 最贪婪匹配
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                # 按长度排序，优先尝试最长的匹配
                sorted_matches = sorted(matches, key=len, reverse=True)
                for match in sorted_matches:
                    if self._is_valid_json(match):
                        logger.info(f"✅ 正则模式匹配到有效JSON，长度: {len(match)}")
                        return match.strip()
        logger.warning("❌ 所有方法都未能提取有效JSON，返回原内容")

    def _is_valid_json(self, json_str: str) -> bool:
        """验证JSON字符串是否有效"""
        try:
            json.loads(json_str)
            return True
        except (json.JSONDecodeError, ValueError):
            return False
# 数据库保存节点已删除，改为在batch_schedule_generator.py中直接保存CSV


async def main():
    """本地主函数 - 直接执行工作流进行大批次日程生成"""
    import random
    import argparse
    from datetime import datetime, timedelta
    from pathlib import Path
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # 命令行参数
    parser = argparse.ArgumentParser(description='日程生成工作流 - 本地批量执行')
    parser.add_argument('--start-date', default='2025-07-14', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--mega-batches', type=int, default=2, help='大批次数量')
    parser.add_argument('--days-per-batch', type=int, default=9, help='每大批次天数')
    
    args = parser.parse_args()
    
    print(f"🚀 日程生成工作流本地执行启动")
    print(f"📅 开始日期: {args.start_date}")
    print(f"🔢 大批次数量: {args.mega_batches}")
    print(f"📊 每批次天数: {args.days_per_batch}")
    print(f"📁 输出目录: workspace/batch_schedule_output/")
    
    try:
        # 初始化LLM
        from llm.base import LLMFactory
        from core.types import LLMConfig
        import os
        
        llm_config = LLMConfig(
            provider="doubao",
            api_key=os.getenv('DOUBAO_API_KEY', 'b633a622-b5d0-4f16-a8a9-616239cf15d1'),
            model_name=os.getenv('DOUBAO_MODEL_DEEPSEEKR1', 'ep-20250221154107-c4qc7'),
            temperature=0.7,
            max_tokens=16384
        )
        
        llm_factory = LLMFactory()
        llm = llm_factory.create(llm_config)
        
        # 创建工作流实例
        workflow = ScheduleWorkflow(llm=llm)
        
        print(f"✅ LLM和工作流初始化成功")
        
        # 初始化状态
        current_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        success_count = 0
        failed_count = 0
        
        # 创建简化的工作流聊天接口
        class LocalWorkflowChat:
            def __init__(self):
                self.current_node = ""
            
            async def add_node_message(self, node_name: str, message: str, status: str):
                # 简化输出，只显示重要信息
                clean_message = message.replace('✅', '[完成]').replace('❌', '[失败]').replace('⚠️', '[警告]').replace('🔄', '[进行中]')
                if status in ['success', 'error', 'warning']:
                    print(f"  [{node_name}] {clean_message}")
            
            def _create_workflow_progress(self):
                return ""
        
        # 循环执行大批次
        for mega_batch_num in range(1, args.mega_batches + 1):
            print(f"\n{'=' * 80}")
            print(f"🎯 正在执行第 {mega_batch_num}/{args.mega_batches} 个大批次")
            print(f"📅 当前开始日期: {current_date.strftime('%Y-%m-%d')}")
            print(f"{'='*80}")
            
            try:
                # 计算大批次的结束日期
                end_date = current_date + timedelta(days=args.days_per_batch - 1)
                
                # 获取可用角色和地点
                available_characters = list(workflow.characters_data.get("角色列表", {}).keys())
                if '穆昭' in available_characters:
                    available_characters.remove('穆昭')
                
                available_locations = []
                for district_info in workflow.locations_data.get("districts", {}).values():
                    for loc_info in district_info.get("locations", {}).values():
                        available_locations.append(loc_info.get('name', ''))
                
                # 随机选择角色和地点
                selected_characters = random.sample(available_characters, min(random.randint(4, 8), len(available_characters)))
                selected_locations = random.sample(available_locations, min(random.randint(5, 10), len(available_locations)))
                
                # 构建配置
                config = {
                    'protagonist': '穆昭',
                    'schedule_type': 'mega_batch',
                    'start_date': current_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'total_days': args.days_per_batch,
                    'selected_characters': selected_characters,
                    'selected_locations': selected_locations,
                    'selected_stories': [],
                    'time_slots_config': {
                        '夜间': {'start': '23:00', 'end': '06:00'},
                        '上午': {'start': '06:00', 'end': '11:00'},
                        '中午': {'start': '11:00', 'end': '14:00'},
                        '下午': {'start': '14:00', 'end': '18:00'},
                        '晚上': {'start': '18:00', 'end': '23:00'}
                    },
                    'character_distribution': 'balanced',
                    'story_integration': 'moderate',
                    'include_holidays': True,
                    'include_lunar': True,
                    'mood_variety': True,
                    'location_variety': True,
                    'enable_cycle_summary': True,
                    'previous_batch_summary': ""  # TODO: 可以从历史中获取
                }
                
                print(f"  📋 配置信息:")
                print(f"    日期范围: {config['start_date']} - {config['end_date']} ({config['total_days']}天)")
                print(f"    角色数量: {len(selected_characters)} ({', '.join(selected_characters[:3])}...)")
                print(f"    地点数量: {len(selected_locations)} ({', '.join(selected_locations[:3])}...)")
                
                # 创建工作流聊天接口
                workflow_chat = LocalWorkflowChat()
                
                # 执行工作流
                print(f"  🚀 开始执行工作流...")
                
                progress_count = 0
                async for stream_event in workflow.execute_workflow_stream(config, workflow_chat):
                    progress_count += 1
                    
                    # 检查是否是最终完成事件
                    if isinstance(stream_event, tuple) and len(stream_event) >= 4:
                        html, content, message, is_complete = stream_event
                        if "执行完成" in message or "生成完成" in message:
                            print(f"    ✅ 检测到完成信号: {message}")
                
                print(f"  📊 工作流执行完成，共收到 {progress_count} 次事件")
                
                # 等待数据库写入
                import time
                time.sleep(2)
                
                # 更新状态
                current_date = end_date + timedelta(days=1)
                success_count += 1
                
                print(f"  🎉 大批次 {mega_batch_num} 执行成功")
                print(f"    📅 下批次开始日期: {current_date.strftime('%Y-%m-%d')}")
                
            except Exception as e:
                failed_count += 1
                print(f"  💥 大批次 {mega_batch_num} 执行失败: {e}")
                import traceback
                traceback.print_exc()
                
                # 失败时也要推进日期，避免卡住
                current_date += timedelta(days=args.days_per_batch)
                print(f"    ⏭️ 跳过到下批次开始日期: {current_date.strftime('%Y-%m-%d')}")
            
            # 批次间休息
            print(f"  ⏸️ 大批次间休息 3 秒...")
            import asyncio
            await asyncio.sleep(3)
        
        # 生成总结报告
        print(f"\n🏁 所有大批次执行完成!")
        print(f"✅ 成功: {success_count}/{args.mega_batches}")
        print(f"❌ 失败: {failed_count}/{args.mega_batches}")
        print(f"📈 成功率: {success_count/args.mega_batches*100:.1f}%")
        print(f"📁 输出文件: workspace/batch_schedule_output/batch_schedules.csv")
        print(f"📅 最终日期: {current_date.strftime('%Y-%m-%d')}")
        
    except KeyboardInterrupt:
        print(f"\n⏹️ 用户中断，程序退出")
    except Exception as e:
        print(f"💥 程序执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n👋 程序退出")


if __name__ == "__main__":
    """本地执行入口"""
    import asyncio
    import sys
    
    # 设置Windows异步事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    # 添加项目路径
    import os
    from pathlib import Path
    
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent  # 回到项目根目录
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(current_dir.parent))  # src目录
    
    asyncio.run(main())