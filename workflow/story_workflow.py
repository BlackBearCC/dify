"""
剧情生成工作流 - 基于Graph+Node的剧情创作系统
集成角色库、地点库、剧情生成等功能
"""

import json
import asyncio
import csv
import random
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.graph import StateGraph
from core.base import BaseNode
from llm.base import LLMFactory
from core.types import LLMConfig, TaskResult, Message, MessageRole

logger = logging.getLogger(__name__)

class StoryWorkflow:
    """剧情生成工作流管理器"""
    
    def __init__(self, llm=None):
        self.llm = llm
        self.graph = None
        self.characters_data = {}
        self.locations_data = {}
        self.protagonist_data = ""  # 主角方知衡的详细人设
        self.current_config = {
            'protagonist': '方知衡',  # 固定主角
            'selected_characters': [],
            'selected_locations': [],
            'story_type': 'daily_life',  # daily_life, romance, adventure, mystery
            'story_length': 'medium',    # short, medium, long
            'relationship_depth': 'casual',  # casual, close, intimate
            'time_setting': 'current',   # current, specific_date
            'mood_tone': 'neutral',      # light, neutral, serious, dramatic
            'interaction_level': 'normal'  # minimal, normal, intensive
        }
        
        # 加载角色、地点和主角数据
        self._load_game_data()
        self._load_protagonist_data()
    
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
        """加载主角方知衡的详细人设"""
        try:
            protagonist_path = os.path.join(os.path.dirname(__file__), '../../config/基础人设.txt')
            if os.path.exists(protagonist_path):
                with open(protagonist_path, 'r', encoding='utf-8') as f:
                    self.protagonist_data = f.read()
                    logger.info(f"成功加载主角人设，内容长度: {len(self.protagonist_data)} 字符")
            else:
                logger.warning("主角人设文件不存在")
                
        except Exception as e:
            logger.error(f"加载主角人设失败: {e}")
    
    def get_protagonist_info(self) -> Dict[str, Any]:
        """获取主角信息"""
        return {
            'name': '方知衡',
            'type': 'protagonist',
            'description': '大学天文系教授、研究员，28岁，理性严谨、内敛温和、平等包容、责任感强',
            'full_profile': self.protagonist_data
        }
    
    def get_characters_list(self) -> List[Dict[str, Any]]:
        """获取角色列表（不包含主角）"""
        characters = []
        char_list = self.characters_data.get("角色列表", {})
        
        for name, info in char_list.items():
            # 跳过主角，主角单独处理
            if name == '方知衡':
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
    
    def get_character_details(self, character_name: str) -> Dict[str, Any]:
        """获取指定角色的详细信息"""
        char_list = self.characters_data.get("角色列表", {})
        char_info = char_list.get(character_name, {})
        
        if not char_info:
            return {}
            
        return {
            'name': character_name,
            'age': char_info.get('年龄', '未知'),
            'personality': char_info.get('性格', ''),
            'description': char_info.get('简介', ''),
            'backstory': char_info.get('背景故事', ''),
            'relationships': char_info.get('人际关系', {}),
            'habits': char_info.get('生活习惯', []),
            'appearance': char_info.get('外貌特征', ''),
            'skills': char_info.get('特长技能', []),
            'locations': char_info.get('活动地点', []),
            'plots': char_info.get('可触发剧情', []),
            'dialogue_style': char_info.get('对话风格', ''),
            'motivations': char_info.get('动机目标', [])
        }
    
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
    
    def update_config(self, config_updates: Dict[str, Any]):
        """更新工作流配置"""
        self.current_config.update(config_updates)
    
    async def create_story_graph(self) -> StateGraph:
        """创建剧情生成图工作流"""
        self.graph = StateGraph(name="story_generation_workflow")
        
        # 创建节点
        story_plan_node = StoryPlanningNode()
        plot_generation_node = PlotGenerationNode()
        database_save_node = DatabaseSaveNode()
        
        # 添加节点到图
        self.graph.add_node("story_planning", story_plan_node)
        self.graph.add_node("plot_generation", plot_generation_node)
        self.graph.add_node("database_save", database_save_node)
        
        # 定义节点连接关系
        self.graph.add_edge("story_planning", "plot_generation")
        self.graph.add_edge("plot_generation", "database_save")
        
        # 设置入口点
        self.graph.set_entry_point("story_planning")
        
        return self.graph
    
    async def execute_story_generation(self, config: Dict[str, Any]) -> TaskResult:
        """执行剧情生成工作流"""
        if not self.graph:
            await self.create_story_graph()
        
        # 准备初始输入
        initial_input = {
            'characters_data': self.characters_data,
            'locations_data': self.locations_data,
            'protagonist_data': self.protagonist_data,
            'config': config,
            'protagonist': config.get('protagonist', '方知衡'),
            'selected_characters': config.get('selected_characters', []),
            'selected_locations': config.get('selected_locations', []),
            'story_count': config.get('story_count', 5),  # 剧情数量配置
            'story_type': config.get('story_type', 'daily_life'),
            'story_length': config.get('story_length', 'medium'),
            'relationship_depth': config.get('relationship_depth', 'casual'),
            'time_setting': config.get('time_setting', 'current'),
            'mood_tone': config.get('mood_tone', 'neutral'),
            'interaction_level': config.get('interaction_level', 'normal'),
            'llm': self.llm  # 传递LLM实例
        }
        
        # 编译并执行图工作流
        compiled_graph = self.graph.compile()
        result = await compiled_graph.invoke(initial_input)
        
        return result

    async def execute_workflow_stream(self, config: Dict[str, Any], workflow_chat):
        """流式执行工作流 - 使用StateGraph自动编排"""
        try:
            # 准备初始输入
            initial_input = {
                'characters_data': self.characters_data,
                'locations_data': self.locations_data,
                'protagonist_data': self.protagonist_data,  # 添加主角完整人设
                'config': config,
                'protagonist': config.get('protagonist', '方知衡'),
                'selected_characters': config.get('selected_characters', []),
                'selected_locations': config.get('selected_locations', []),
                'story_count': config.get('story_count', 5),  # 剧情数量配置
                'story_type': config.get('story_type', 'daily_life'),
                'story_length': config.get('story_length', 'medium'),
                'relationship_depth': config.get('relationship_depth', 'casual'),
                'time_setting': config.get('time_setting', 'current'),
                'mood_tone': config.get('mood_tone', 'neutral'),
                'interaction_level': config.get('interaction_level', 'normal'),
                'workflow_chat': workflow_chat,  # 传递UI更新器
                'llm': self.llm  # 传递LLM实例
            }
            
            # 创建并编译图工作流
            if not self.graph:
                await self.create_story_graph()
            
            compiled_graph = self.graph.compile()
            
            # 使用图的流式执行
            async for stream_event in compiled_graph.stream(initial_input):
                event_type = stream_event.get('type')
                node_name = stream_event.get('node')
                
                if event_type == 'start':
                    # 工作流开始
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        "工作流开始执行...",
                        False
                    )
                
                elif event_type == 'node_start':
                    # 节点开始执行
                    node_display_name = self._get_node_display_name(node_name)
                    workflow_chat.current_node = self._get_node_id(node_name)
                    
                    yield (
                        workflow_chat.update_node_state(self._get_node_id(node_name), "active"),
                        "",
                        f"{node_display_name}开始执行...",
                        False
                    )
                
                elif event_type == 'node_streaming':
                    # 节点流式执行中 - 实时更新UI显示进度
                    intermediate_result = stream_event.get('intermediate_result')
                    if intermediate_result and intermediate_result.state_update:
                        # 获取当前生成的内容长度
                        content_length = 0
                        for key in ['planning_result', 'plot_content']:
                            if key in intermediate_result.state_update:
                                content_length = len(intermediate_result.state_update[key])
                                break
                        
                        # 实时更新进度信息 - 重要：获取最新的进度HTML，因为节点内部已经更新了结果
                        if content_length > 0:
                            yield (
                                workflow_chat._create_workflow_progress(),  # 这个会包含节点内部更新的最新内容
                                "",  # 快捷回复区域保持空
                                f"正在生成内容... 当前长度: {content_length} 字符",
                                False  # 发送按钮保持禁用
                            )
                
                elif event_type == 'node_complete':
                    # 节点执行完成
                    node_display_name = self._get_node_display_name(node_name)
                    
                    yield (
                        workflow_chat.update_node_state(self._get_node_id(node_name), "completed"),
                        "",
                        f"{node_display_name}执行完成",
                        False
                    )
                
                elif event_type == 'node_error':
                    # 节点执行错误
                    error_msg = stream_event.get('error', '未知错误')
                    
                    await workflow_chat.add_node_message(
                        "系统",
                        f"节点执行失败: {error_msg}",
                        "error"
                    )
                    
                    yield (
                        workflow_chat.update_node_state(self._get_node_id(node_name), "error"),
                        "",
                        "",
                        False
                    )
                
                elif event_type == 'final':
                    # 工作流完成
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        "工作流执行完成",
                        False
                    )
                
                # 其他事件类型可以忽略或记录日志
                else:
                    # 持续更新UI以保持流畅性
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        "工作流执行中...",
                        False
                    )
                
        except Exception as e:
            logger.error(f"工作流流式执行失败: {e}")
            await workflow_chat.add_node_message(
                "系统",
                f"工作流执行失败: {str(e)}",
                "error"
            )
            yield (
                workflow_chat.update_node_state("planning", "error"),
                "",
                "",
                False
            )
    
    def _get_node_display_name(self, node_name: str) -> str:
        """获取节点显示名称"""
        name_mapping = {
            'story_planning': '剧情规划',
            'plot_generation': '剧情生成',
            'database_save': '数据库保存'
        }
        return name_mapping.get(node_name, node_name)
    
    def _get_node_id(self, node_name: str) -> str:
        """获取节点ID"""
        id_mapping = {
            'story_planning': 'planning',
            'plot_generation': 'plot', 
            'database_save': 'save'
        }
        return id_mapping.get(node_name, node_name)


class StoryPlanningNode(BaseNode):
    """剧情规划节点 - 分析角色关系和故事大纲"""
    
    def __init__(self):
        super().__init__(name="story_planning", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行剧情规划节点 - 非流式版本"""
        # 使用流式执行并返回最终结果
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行剧情规划节点"""
        print("🎯 开始剧情规划...")
        
        workflow_chat = input_data.get('workflow_chat')
        llm = input_data.get('llm')
        
        # 获取所有配置参数
        protagonist_data = input_data.get('protagonist_data', '')
        characters_data = input_data.get('characters_data', {})
        locations_data = input_data.get('locations_data', {})
        selected_characters = input_data.get('selected_characters', [])
        selected_locations = input_data.get('selected_locations', [])
        story_count = input_data.get('story_count', 5)  # 剧情数量
        story_type = input_data.get('story_type', 'daily_life')
        story_length = input_data.get('story_length', 'medium')
        relationship_depth = input_data.get('relationship_depth', 'casual')
        
        # 更新UI - 开始状态
        if workflow_chat:
            await workflow_chat.add_node_message(
                "剧情规划",
                "正在查询现有剧情，分析主角方知衡与选定角色的关系，生成剧情框架...",
                "progress"
            )
        
        # 获取已有剧情作为参考
        existing_stories_summary = {}
        existing_story_ids = []
        max_story_number = 0
        try:
            from database import story_manager
            
            # 查询所有选中角色的已有剧情
            all_characters = ['方知衡'] + selected_characters
            existing_stories_summary = story_manager.get_character_existing_stories_summary(all_characters)
            
            # 获取所有现有的故事ID，用于避免重复
            all_stories = story_manager.get_stories_by_filter({}, limit=1000)
            existing_story_ids = [story['story_id'] for story in all_stories]
            
            # 分析现有ID模式，找出最大编号
            import re
            story_numbers = []
            for story_id in existing_story_ids:
                # 匹配STORY_XXX格式的ID
                match = re.match(r'STORY_(\d+)', story_id)
                if match:
                    story_numbers.append(int(match.group(1)))
            
            max_story_number = max(story_numbers) if story_numbers else 0
            
            existing_count = existing_stories_summary.get('total_stories', 0)
            if workflow_chat and existing_count > 0:
                await workflow_chat.add_node_message(
                    "剧情规划",
                    f"已找到 {existing_count} 个相关剧情作为参考，现有最大故事编号: {max_story_number}，正在分析剧情风格和主题...",
                    "progress"
                )
                
        except Exception as e:
            logger.warning(f"获取已有剧情失败，将不使用历史参考: {e}")
            existing_stories_summary = {
                'existing_stories': [],
                'story_themes': [],
                'character_relationships': {},
                'common_locations': [],
                'story_styles': []
            }
            existing_story_ids = []
            max_story_number = 0
        
        # 构建详细的角色信息
        character_details = []
        char_list = characters_data.get("角色列表", {})
        for char_name in selected_characters:
            if char_name in char_list:
                char_info = char_list[char_name]
                detail = f"""
## {char_name}

- 年龄：{char_info.get('年龄', '未知')}
- 性格：{char_info.get('性格', '')}
- 简介：{char_info.get('简介', '')}
- 背景故事：{char_info.get('背景故事', '')}
- 活动地点：{', '.join(char_info.get('活动地点', []))}
- 人际关系：{char_info.get('人际关系', {})}
- 可触发剧情：{', '.join(char_info.get('可触发剧情', []))}
"""
                character_details.append(detail)
        
        # 构建详细的地点信息
        location_details = []
        districts = locations_data.get("districts", {})
        for loc_name in selected_locations:
            for district_name, district_info in districts.items():
                locations = district_info.get("locations", {})
                for location_key, location_info in locations.items():
                    if location_info.get('name') == loc_name or location_key == loc_name:
                        detail = f"""
## {location_info.get('name', loc_name)}（{district_info.get('name', district_name)}区）

- 类型：{location_info.get('type', '')}
- 描述：{location_info.get('description', '')}
- 氛围：{location_info.get('atmosphere', '')}
- 关键词：{', '.join(location_info.get('keywords', []))}
"""
                        location_details.append(detail)
        
        # 构建已有剧情参考信息
        existing_stories_info = ""
        if existing_stories_summary.get('existing_stories'):
            existing_stories_info = f"""
# 已有剧情参考（避免重复）

## 已有剧情列表（共 {existing_stories_summary.get('total_stories', 0)} 个）

{chr(10).join([f"- {story.get('story_id', 'N/A')}: {story.get('story_overview', story.get('main_conflict', 'N/A'))}" for story in existing_stories_summary['existing_stories'][:10]])}

## 已有故事ID信息

现有故事ID: {', '.join(existing_story_ids[:20])}{'...' if len(existing_story_ids) > 20 else ''}
最大故事编号: {max_story_number}

**重要要求**：
1. 请避免与已有剧情内容重复，创作新的剧情
2. 新生成的故事ID必须从 STORY_{max_story_number + 1:03d} 开始递增，避免与现有ID重复
"""
        else:
            existing_stories_info = f"# 首次创作（无已有剧情参考）\n\n当前最大故事编号: {max_story_number}\n新故事ID将从 STORY_{max_story_number + 1:03d} 开始"

        # 构建通用的剧情规划提示词
        planning_prompt = f"""
你是一名专业的剧情策划师，需要基于以下信息制定剧情规划框架：

# 主角设定

{protagonist_data}

# 参与角色信息

{''.join(character_details) if character_details else '无其他角色参与'}

# 地点信息

{''.join(location_details) if location_details else '无特定地点限制'}

{existing_stories_info}

# 剧情配置

- 剧情数量：{story_count} 个大剧情
- 剧情类型：{story_type}
- 剧情细分程度：{story_length}（每个剧情包含的独立小节数量）
- 关系深度：{relationship_depth}

**重要要求**：
1. 每个小节都是独立的一幕演绎，不能有时间或空间的连续性，应该是不同天数的故事，但是注意内容禁止出现日级别的时间比如周六，星期几这种描述
2. 这些小节会被分布到任意时间地点使用，必须完全独立
3. 每个小节必须包含完整的四幕式结构（开端→发展→高潮→结局）
4. 每个小节都必须出现主角方知衡和指定的参与角色

# 输出要求

请以JSON格式输出 **{story_count} 个完整大剧情** 的规划框架，重点关注独立小节的设计：

```json
{{
  "planning": {{
    "总体设计": {{
      "剧情总数": {story_count},
      "整体主题": "所有剧情的统一主题",
      "角色关系网络": {{
        "主角关系定位": {{
          "与角色A": "具体关系定位和发展路径",
          "与角色B": "具体关系定位和发展路径"
        }},
        "角色间关系": "相互关系和互动模式",
        "关系发展路径": "关系演变的可能性和方向"
      }},
      "地点运用策略": {{
        "地点功能定位": {{
          "地点1": "在剧情中的功能定位和氛围作用",
          "地点2": "在剧情中的功能定位和氛围作用"
        }},
        "氛围营造": "地点氛围如何服务于情节发展",
        "空间转换意义": "空间转换的叙事作用"
      }}
    }},
    "剧情规划列表": [
      {{
        "剧情ID": "STORY_{max_story_number + 1:03d}",
        "剧情名称": "第1个大剧情的名称",
        "剧情概述": "整段大剧情的四幕式描述：开端（背景设定） → 发展（矛盾升级） → 高潮（冲突顶点） → 结局（问题解决），完整讲述这个大剧情的故事脉络",
        "故事主题与核心冲突": {{
          "故事主题": "基于主角性格特征和生活背景确定的主题，避免与已有剧情重复",
          "核心冲突": "结合参与角色设计的合理冲突点，确保新颖性"
        }},
        "主要剧情线": {{
          "开端": "设定背景和初始情况的具体描述",
          "发展": "矛盾逐步升级和角色互动的详细过程",
          "高潮": "核心冲突达到顶点的关键事件",
          "结局": "问题解决和角色成长的完整描述"
        }},
        "关键事件节点": [
          {{
            "事件名": "重要转折点描述",
            "触发条件": "前置要求和条件",
            "预期结果": "对后续剧情的影响",
            "逻辑关联": "与其他事件的逻辑关系"
          }}
        ],
        "情感张力设计": {{
          "情感基调": "根据配置的mood_tone设计基调",
          "情感起伏曲线": "情感发展的具体安排",
          "表达方式": "符合主角性格的情感表达",
          "理性感性平衡": "理性与感性冲突的处理"
        }}
      }}
    ]
  }}
}}
```

请确保：
1. 准确生成 **{story_count} 个完整的大剧情规划**
2. 每个剧情的关键事件节点设计要考虑独立小节的特性
3. 角色关系网络清晰详细，适用于所有剧情
4. 地点运用策略要支持独立场景的设计
5. 情感张力设计要在单个小节内形成完整弧线
6. 所有剧情相互独立，每个小节也必须独立
7. 每个剧情都有独特的冲突点，但要能分解为独立的小节情境
"""
        
        # 流式调用LLM
        if llm:
            try:
                # 构建消息列表
                message = Message(role=MessageRole.USER, content=planning_prompt)
                messages = [message]
                
                logger.info(f"剧情规划: 开始流式LLM调用，提示词长度: {len(planning_prompt)}")
                
                # 使用think模式流式调用
                chunk_count = 0
                think_content = ""
                final_content = ""
                
                async for chunk_data in llm.stream_generate(
                    messages, 
                    mode="think",
                    return_dict=True
                ):
                    chunk_count += 1
                    
                    think_part = chunk_data.get("think", "")
                    content_part = chunk_data.get("content", "")
                    
                    think_content += think_part
                    final_content += content_part
                    
                    # 实时更新UI
                    if workflow_chat:
                        try:
                            display_content = ""
                            if think_content.strip():
                                display_content += f"""
<div style="background: #f8f9fa; border-left: 4px solid #6c757d; padding: 10px; margin: 10px 0; border-radius: 4px;">
思考过程：<br>
{think_content}
</div>"""
                            
                            if final_content.strip():
                                display_content += f"""
<div style="background: #e8f5e9; border-left: 4px solid #28a745; padding: 10px; margin: 10px 0; border-radius: 4px;">
规划结果：<br>
{final_content}
</div>"""
                            
                            await workflow_chat.add_node_message(
                                "剧情规划",
                                display_content,
                                "streaming"
                            )
                        except Exception as ui_error:
                            logger.warning(f"剧情规划UI更新失败: {ui_error}")
                    
                    # 每个chunk都yield
                    yield {
                        'planning_result': final_content,
                        'planning_think': think_content,
                        'chunk_progress': f"{chunk_count} chunks processed"
                    }
                
                logger.info(f"剧情规划: 流式生成完成，总chunk数: {chunk_count}，内容长度: {len(final_content)}")
                        
            except Exception as e:
                error_msg = f"剧情规划LLM调用失败: {type(e).__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise Exception(error_msg)
        else:
            error_msg = "剧情规划: LLM未初始化"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 解析JSON格式的结果
        try:
            from parsers.json_parser import JSONParser
            parser = JSONParser()
            
            json_content = self._extract_json_from_content(final_content)
            parsed_result = parser.parse(json_content)
            
            if parsed_result and 'planning' in parsed_result:
                planning_data = parsed_result['planning']
                logger.info(f"成功解析剧情规划JSON结果")
            else:
                # 如果解析失败，使用原始内容作为备选
                planning_data = final_content
                logger.warning(f"剧情规划JSON解析失败，使用原始内容")
                
        except Exception as parse_error:
            logger.warning(f"剧情规划JSON解析异常: {parse_error}，使用原始内容")
            planning_data = final_content
        
        # 最终完整结果
        output_data = input_data.copy()
        output_data['planning_result'] = planning_data
        
        print(f"✅ 剧情规划完成")
        yield output_data
    
    def _extract_json_from_content(self, content: str) -> str:
        """从生成内容中提取JSON部分"""
        import re
        
        # 查找```json...```代码块
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # 如果没有代码块，尝试查找以{开头}结尾的内容
        json_pattern2 = r'\{.*\}'
        matches2 = re.findall(json_pattern2, content, re.DOTALL)
        
        if matches2:
            return matches2[0].strip()
        
        # 如果都没找到，返回原内容
        return content.strip()


class PlotGenerationNode(BaseNode):
    """剧情生成节点 - 生成具体的剧情事件"""
    
    def __init__(self):
        super().__init__(name="plot_generation", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行剧情生成节点 - 非流式版本"""
        # 使用流式执行并返回最终结果
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行剧情生成节点"""
        print("📚 开始生成剧情...")
        
        workflow_chat = input_data.get('workflow_chat')
        llm = input_data.get('llm')
        planning_result = input_data.get('planning_result', '')
        
        # 验证规划结果
        if not planning_result or not planning_result.strip():
            error_msg = f"剧情生成失败：缺少剧情规划结果。input_data键: {list(input_data.keys())}"
            logger.error(error_msg)
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "剧情生成",
                    error_msg,
                    "error"
                )
            raise Exception(error_msg)
        
        # 更新UI - 开始状态
        if workflow_chat:
            await workflow_chat.add_node_message(
                "剧情生成", 
                f"正在基于规划结果生成具体剧情（规划长度：{len(planning_result)} 字符）...",
                "progress"
            )
        
        # 获取完整的配置和规划结果（先获取变量）
        protagonist_data = input_data.get('protagonist_data', '')
        characters_data = input_data.get('characters_data', {})
        selected_characters = input_data.get('selected_characters', [])
        selected_locations = input_data.get('selected_locations', [])
        story_count = input_data.get('story_count', 5)
        story_type = input_data.get('story_type', 'daily_life')
        story_length = input_data.get('story_length', 'medium')
        relationship_depth = input_data.get('relationship_depth', 'casual')
        
        # 获取现有故事ID信息，确保生成的ID不重复
        existing_story_ids = []
        max_story_number = 0
        try:
            from database import story_manager
            all_stories = story_manager.get_stories_by_filter({}, limit=1000)
            existing_story_ids = [story['story_id'] for story in all_stories]
            
            # 生成临时ID前缀，实际存储时会被替换为数据库自增ID
            temp_prefix = "TEMP_"
            
        except Exception as e:
            logger.warning(f"获取现有故事ID失败: {e}")
            existing_story_ids = []
            temp_prefix = "TEMP_"
        
        # 构建通用的剧情生成提示词
        plot_prompt = f"""
你是一名专业的剧情编剧，需要基于剧情规划生成具体的剧情内容。

# 剧情规划

{planning_result}

# 角色设定

{protagonist_data}

# 剧情配置

- 剧情数量：{story_count} 个大剧情
- 剧情类型：{story_type}
- 剧情细分程度：{story_length}（每个剧情包含的独立小节数量）
- 关系深度：{relationship_depth}

# 剧情ID生成说明

- 使用临时ID，格式为 TEMP_001, TEMP_002 等
- 数据库保存时会自动分配真正的ID

**核心要求**：
1. 每个小节都是独立的一幕演绎，包含完整的四幕式结构
2. 每个小节必须同时出现主角方知衡和指定的参与角色
3. 小节之间没有时间空间联系，可以在任意时间地点使用
4. 每个小节都有开端→发展→高潮→结局的完整戏剧弧线
5. **故事使用临时ID，数据库会自动替换为真正的ID**

# 输出要求

请基于规划中的 **{story_count} 个大剧情**，以JSON格式输出丰富的独立小节内容：

```json
{{
  "story": {{
    "总体信息": {{
      "剧情总数": {story_count},
      "生成时间": "{{生成时间}}",
      "主角": "方知衡"
    }},
    "剧情列表": [
      {{
        "剧情ID": "TEMP_001",
        "剧情名称": "第1个大剧情的名称",
        "剧情概述": "整段大剧情的四幕式概述，清晰描述从开端到结局的完整故事弧线",
        "剧情小节": [
          {{
            "小节ID": "STEMP_001_SCENE_001",
            "小节标题": "独立小节的标题",
            "小节内容": "完整的故事内容，自然融入四幕式结构（开端→发展→高潮→结局），包含角色对话和情感变化，体现独立完整的一幕演绎，禁止包含时间，主角说话要正常合理的人设语气，禁止装逼",
            "地点": "发生地点",
            "参与角色": ["方知衡", "指定角色名"]
          }}
        ],
        "剧情总结": {{
          "主要冲突": "核心矛盾点",
          "情感发展": "角色关系的整体发展",
          "后续铺垫": "为后续剧情设置的伏笔"
        }}
      }}
    ]
  }}
}}
```

请确保：
1. 准确生成 **{story_count} 个完整的大剧情**
2. **故事ID使用临时ID**：第1个剧情使用 TEMP_001，第2个使用 TEMP_002，以此类推
3. **小节ID格式**：第1个剧情的小节使用 STEMP_001_SCENE_001、STEMP_001_SCENE_002 等
4. 每个大剧情根据story_length设置生成相应数量的独立小节：
   - short: 1-2个独立小节
   - medium: 3-5个独立小节  
   - long: 5-8个独立小节
5. **小节内容必须是完整的故事段落**，自然融入四幕式结构
6. **每个小节都必须同时出现主角方知衡和指定的参与角色**
7. **小节完全独立**，不依赖前后小节的时间空间联系
8. **对话和情感变化自然融入故事内容**，不单独分离
9. 每个小节都是独立完整的一幕演绎，可以单独使用
10. 内容生动详细，包含场景描述、角色互动、冲突解决
"""
        
        # 流式调用LLM
        if llm:
            try:
                # 构建消息列表
                message = Message(role=MessageRole.USER, content=plot_prompt)
                messages = [message]
                
                logger.info(f"剧情生成: 开始流式LLM调用，提示词长度: {len(plot_prompt)}")
                
                # 使用think模式流式调用
                chunk_count = 0
                think_content = ""
                final_content = ""
                
                async for chunk_data in llm.stream_generate(
                    messages, 
                    mode="think",
                    return_dict=True
                ):
                    chunk_count += 1
                    
                    think_part = chunk_data.get("think", "")
                    content_part = chunk_data.get("content", "")
                    
                    think_content += think_part
                    final_content += content_part
                    
                    # 实时更新UI
                    if workflow_chat:
                        try:
                            display_content = ""
                            if think_content.strip():
                                display_content += f"""
<div style="background: #f8f9fa; border-left: 4px solid #6c757d; padding: 10px; margin: 10px 0; border-radius: 4px;">
思考过程：<br>
{think_content}
</div>"""
                            
                            if final_content.strip():
                                display_content += f"""
<div style="background: #e8f5e9; border-left: 4px solid #28a745; padding: 10px; margin: 10px 0; border-radius: 4px;">
📖 剧情内容：<br>
{final_content}
</div>"""
                            
                            await workflow_chat.add_node_message(
                                "剧情生成",
                                display_content,
                                "streaming"
                            )
                        except Exception as ui_error:
                            logger.warning(f"剧情生成UI更新失败: {ui_error}")
                    
                    # 每个chunk都yield
                    yield {
                        'plot_content': final_content,
                        'plot_think': think_content,
                        'chunk_progress': f"{chunk_count} chunks processed"
                    }
                
                logger.info(f"剧情生成: 流式生成完成，总chunk数: {chunk_count}，内容长度: {len(final_content)}")
                        
            except Exception as e:
                error_msg = f"剧情生成LLM调用失败: {type(e).__name__}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise Exception(error_msg)
        else:
            error_msg = f"剧情生成: LLM未初始化"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 解析JSON格式的结果
        try:
            from parsers.json_parser import JSONParser
            parser = JSONParser()
            
            json_content = self._extract_json_from_content(final_content)
            logger.info(f"提取的JSON内容长度: {len(json_content)} 字符")
            
            parsed_result = parser.parse(json_content)
            
            if parsed_result and 'story' in parsed_result:
                story_data = parsed_result['story']
                logger.info("成功解析剧情生成JSON结果，找到story字段")
            elif parsed_result and ('总体信息' in parsed_result or '剧情列表' in parsed_result):
                # 直接是story内容格式
                story_data = parsed_result
                logger.info("成功解析剧情生成JSON结果，直接是story内容格式")
            else:
                logger.warning(f"剧情生成JSON解析失败，解析结果键: {list(parsed_result.keys()) if parsed_result else 'None'}，使用原始内容")
                story_data = final_content
                
        except Exception as parse_error:
            logger.warning(f"剧情生成JSON解析异常: {parse_error}，final_content前100字符: {final_content[:100]}，使用原始内容")
            story_data = final_content
        
        output_data = input_data.copy()
        output_data['plot_content'] = story_data
        
        # 添加调试信息
        logger.info(f"剧情生成完成，plot_content类型: {type(story_data)}, 是否为dict: {isinstance(story_data, dict)}")
        if isinstance(story_data, dict):
            logger.info(f"plot_content字典键: {list(story_data.keys())}")
        
        print("✅ 剧情生成完成")
        yield output_data
    
    def _extract_json_from_content(self, content: str) -> str:
        """从生成内容中提取JSON部分"""
        import re
        
        # 查找```json...```代码块
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # 如果没有代码块，尝试查找以{开头}结尾的内容
        json_pattern2 = r'\{.*\}'
        matches2 = re.findall(json_pattern2, content, re.DOTALL)
        
        if matches2:
            return matches2[0].strip()
        
        # 如果都没找到，返回原内容
        return content.strip()


class DatabaseSaveNode(BaseNode):
    """数据库保存节点 - 将剧情数据保存到SQLite数据库"""
    
    def __init__(self):
        super().__init__(name="database_save")
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据库保存"""
        print("💾 开始保存到数据库...")
        
        workflow_chat = input_data.get('workflow_chat')
        plot_content = input_data.get('plot_content', '')
        config = input_data.get('config', {})
        
        # 添加调试信息
        logger.info(f"数据库保存节点接收到plot_content类型: {type(plot_content)}")
        if isinstance(plot_content, dict):
            logger.info(f"plot_content字典键: {list(plot_content.keys())}")
        elif isinstance(plot_content, str):
            logger.info(f"plot_content字符串长度: {len(plot_content)}，前100字符: {plot_content[:100]}")
        
        # 更新UI - 开始状态
        if workflow_chat:
            await workflow_chat.add_node_message(
                "数据库保存",
                "正在解析剧情数据并保存到SQLite数据库...",
                "progress"
            )
        
        try:
            from database import story_manager
            from datetime import datetime
            import json
            
            # 解析剧情数据
            story_data = None
            if isinstance(plot_content, dict):
                # 如果plot_content是dict，说明前面节点已经解析成功
                # 检查是否是完整的story数据结构还是已经提取的story内容
                if 'story' in plot_content:
                    # 包含story字段的完整JSON
                    story_data = plot_content['story']
                elif '总体信息' in plot_content or '剧情列表' in plot_content:
                    # 已经是story字段的内容
                    story_data = plot_content
                else:
                    # 尝试作为完整story数据使用
                    story_data = plot_content
                    
            elif isinstance(plot_content, str):
                # 从字符串中解析JSON
                try:
                    from parsers.json_parser import JSONParser
                    parser = JSONParser()
                    
                    json_content = self._extract_json_from_content(plot_content)
                    parsed_data = parser.parse(json_content)
                    
                    if parsed_data and 'story' in parsed_data:
                        story_data = parsed_data['story']
                    elif parsed_data and ('总体信息' in parsed_data or '剧情列表' in parsed_data):
                        # 直接是story内容
                        story_data = parsed_data
                    else:
                        logger.error(f"JSON解析结果格式不正确: {list(parsed_data.keys()) if parsed_data else 'None'}")
                        raise ValueError(f"未找到有效的剧情数据结构")
                        
                except Exception as parse_error:
                    logger.error(f"JSON解析失败: {parse_error}")
                    raise ValueError(f"无法解析剧情数据: {parse_error}")
            else:
                logger.error(f"无法处理的剧情数据类型: {type(plot_content)}")
                raise ValueError(f"无法处理的剧情数据类型: {type(plot_content)}")
            
            # 验证story_data结构
            if not story_data:
                raise ValueError("解析后的剧情数据为空")
                
            # 确保story_data有必要的字段
            if not isinstance(story_data, dict):
                raise ValueError(f"剧情数据不是字典格式: {type(story_data)}")
                
            if '剧情列表' not in story_data:
                raise ValueError("剧情数据缺少'剧情列表'字段")
                
            logger.info(f"成功解析剧情数据: {len(story_data.get('剧情列表', []))} 个剧情")
            
            # 保存到数据库
            success = story_manager.save_story_data(story_data, config)
            
            if not success:
                raise Exception("数据库保存失败")
            
            # 获取统计信息
            stats = story_manager.get_story_statistics()
            
            # 生成CSV导出（可选）
            csv_path = story_manager.export_story_data(format='csv')
            
            # 生成结果信息
            story_count = len(story_data.get('剧情列表', []))
            total_scenes = sum(len(story.get('剧情小节', [])) for story in story_data.get('剧情列表', []))
            
            result = f"""✅ 数据库保存成功！

# 保存信息

- 保存剧情数：{story_count} 个
- 保存小节数：{total_scenes} 个
- 保存时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# 数据库统计

- 总剧情数：{stats.get('total_stories', 0)} 个
- 总小节数：{stats.get('total_scenes', 0)} 个
- 总角色数：{stats.get('total_characters', 0)} 个
- 最新创建：{stats.get('latest_creation', '未知')}

# 导出文件

- CSV导出路径：{csv_path}
- 可在前端数据库管理界面查看和编辑数据

# 后续操作

- 在前端"数据库管理"页面查看剧情
- 按角色筛选查看相关剧情
- 直接编辑数据库表内容
- 导出指定数据为CSV文件
"""
            
            # 更新UI - 完成状态
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "数据库保存",
                    result,
                    "completed"
                )
            
            output_data = input_data.copy()
            output_data['database_saved'] = True
            output_data['csv_export_path'] = csv_path
            output_data['saved_story_count'] = story_count
            output_data['saved_scene_count'] = total_scenes
            output_data['database_stats'] = stats
            
            print(f"✅ 数据库保存完成，导出CSV: {csv_path}")
            return output_data
            
        except Exception as e:
            error_msg = f"数据库保存失败: {str(e)}"
            print(error_msg)
            logger.error(error_msg, exc_info=True)
            
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "数据库保存",
                    error_msg,
                    "error"
                )
            
            raise e
    
    def _extract_json_from_content(self, content: str) -> str:
        """从生成内容中提取JSON部分"""
        import re
        
        # 查找```json...```代码块
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # 如果没有代码块，尝试查找以{开头}结尾的内容
        json_pattern2 = r'\{.*\}'
        matches2 = re.findall(json_pattern2, content, re.DOTALL)
        
        if matches2:
            return matches2[0].strip()
        
        # 如果都没找到，返回原内容
        return content.strip()