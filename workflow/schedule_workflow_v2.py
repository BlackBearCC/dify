"""主角日程生成工作流 v2 - 简化版，专注主角个人日程
仅关注主角方知衡的个人生活安排，去除所有NPC角色互动，保持代码清爽
"""

import json
import asyncio
import csv
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.graph import StateGraph
from core.base import BaseNode
from llm.base import LLMFactory
from core.types import LLMConfig, TaskResult, Message, MessageRole
# 内部简化版周期规划节点，避免角色依赖

logger = logging.getLogger(__name__)

class ScheduleWorkflowV2:
    """主角日程生成工作流v2 - 简化版管理器"""
    
    def __init__(self, llm=None):
        self.llm = llm
        self.graph = None
        self.protagonist_data = ""
        self.holidays_data = {}
        self.locations_data = {}
        self.current_config = {
            'protagonist': '方知衡',
            'schedule_type': 'personal',
            'start_date': '',
            'end_date': '',
            'total_days': 7,
            'selected_locations': [],
            'time_slots_config': {
                '夜间': {'start': '23:00', 'end': '06:00'},
                '上午': {'start': '06:00', 'end': '11:00'},
                '中午': {'start': '11:00', 'end': '14:00'},
                '下午': {'start': '14:00', 'end': '18:00'},
                '晚上': {'start': '18:00', 'end': '23:00'}
            },
            'include_holidays': True,
            'personal_focus': True,
            'life_theme': 'daily_routine'
        }
        
        self._load_protagonist_data()
        self._load_locations_data()
        self._load_holidays_data()
    
    async def create_personal_schedule_graph(self) -> StateGraph:
        """创建主角个人日程生成图工作流"""
        self.graph = StateGraph(name="personal_schedule_workflow")

        # 使用原版多周期节点
        cycle_planning_node = PersonalCyclePlanningNode()
        schedule_generate_node = PersonalScheduleGenerateNode()

        self.graph.add_node("cycle_planning", cycle_planning_node)
        self.graph.add_node("schedule_generate", schedule_generate_node)

        # 条件路由：参考原版 should_continue_generation
        def should_continue_generation(state):
            current_cycle_index = state.get('current_cycle_index', 0)
            cycles = state.get('cycles', [])
            generation_complete = state.get('generation_complete', False)
            if generation_complete or current_cycle_index >= len(cycles):
                return "END"
            else:
                return "schedule_generate"

        self.graph.add_edge("cycle_planning", "schedule_generate")
        self.graph.add_conditional_edges(
            "schedule_generate",
            should_continue_generation,
            {
                "schedule_generate": "schedule_generate",
                "END": "__end__"
            }
        )

        self.graph.set_entry_point("cycle_planning")
        return self.graph
    
    def _load_protagonist_data(self):
        """加载主角基础人设"""
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
    
    def _load_holidays_data(self):
        """加载节假日数据"""
        try:
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
            self.holidays_data = {}
    
    def _load_locations_data(self):
        """加载地点数据，支持后续周期规划使用"""
        try:
            loc_path = os.path.join(os.path.dirname(__file__), '../../config/yunhub_locations.json')
            if os.path.exists(loc_path):
                with open(loc_path, 'r', encoding='utf-8') as f:
                    self.locations_data = json.load(f)
                    district_count = len(self.locations_data.get("districts", {}))
                    logger.info(f"成功加载地点数据，包含 {district_count} 个区域")
        except Exception as e:
            logger.error(f"加载地点数据失败: {e}")
            self.locations_data = {}
    
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
    
    async def execute_workflow_stream(self, config: Dict[str, Any], workflow):
        """流式执行个人日程工作流"""
        try:
            # 准备初始输入
            initial_input = {
                'protagonist_data': self.protagonist_data,
                'holidays_data': self.holidays_data,
                'config': config,
                'protagonist': config.get('protagonist', '方知衡'),
                'start_date': config.get('start_date', ''),
                'end_date': config.get('end_date', ''),
                'total_days': config.get('total_days', 7),
                'time_slots_config': config.get('time_slots_config', self.current_config['time_slots_config']),
                'include_holidays': config.get('include_holidays', True),
                'personal_focus': config.get('personal_focus', True),
                'life_theme': config.get('life_theme', 'daily_routine'),
                'locations_data': self.locations_data,
                'selected_locations': config.get('selected_locations', []),
                'workflow_chat': workflow,
                'llm': self.llm
            }
            
            # 创建并编译图工作流
            if not self.graph:
                await self.create_personal_schedule_graph()
            
            compiled_graph = self.graph.compile()
            
            # 流式执行
            async for stream_event in compiled_graph.stream(initial_input):
                event_type = stream_event.get('type')
                node_name = stream_event.get('node')
                
                if event_type == 'start':
                    yield (
                        workflow._create_workflow_progress(),
                        "",
                        "个人日程生成工作流开始执行...",
                        False
                    )
                
                elif event_type == 'node_start':
                    node_display_name = self._get_node_display_name(node_name)
                    workflow.current_node = node_name
                    
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
                    intermediate_result = stream_event.get('intermediate_result')
                    if intermediate_result and intermediate_result.state_update:
                        content_length = 0
                        for key in ['schedule_content', 'daily_schedules', 'personal_schedule']:
                            if key in intermediate_result.state_update:
                                if isinstance(intermediate_result.state_update[key], str):
                                    content_length = len(intermediate_result.state_update[key])
                                elif isinstance(intermediate_result.state_update[key], (list, dict)):
                                    content_length = len(str(intermediate_result.state_update[key]))
                                break
                        
                        if content_length > 0:
                            node_display_name = self._get_node_display_name(node_name)
                            await workflow.add_node_message(
                                node_display_name,
                                f"正在生成个人日程... 当前生成{content_length}字符",
                                "streaming"
                            )
                            
                            yield (
                                workflow._create_workflow_progress(),
                                "",
                                f"正在生成个人日程... 当前长度: {content_length} 字符",
                                False
                            )
                
                elif event_type == 'node_complete':
                    node_display_name = self._get_node_display_name(node_name)
                    
                    if node_name == 'generate':
                        result_content = "✅ 个人日程生成完成"
                        if 'personal_schedule' in stream_event.get('output', {}):
                            schedule_data = stream_event['output']['personal_schedule']
                            if isinstance(schedule_data, (dict, list)):
                                result_content = f"✅ 已成功生成{config['total_days']}天的个人日程"
                    else:
                        result_content = "✅ 执行完成"
                    
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
                    yield (
                        workflow._create_workflow_progress(),
                        "",
                        "个人日程生成工作流执行完成",
                        False
                    )
                
        except Exception as e:
            logger.error(f"个人日程工作流执行失败: {e}")
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
            'schedule_generate': '日程生成',
            'planning': '日程规划',  # 兼容旧名称
            'generate': '日程生成(旧)'
        }
        return name_mapping.get(node_name, node_name)


class PersonalSchedulePlanningNode(BaseNode):
    """个人日程规划节点"""
    
    def __init__(self):
        super().__init__(name="personal_planning", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行个人日程规划"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行个人日程规划"""
        print("📋 开始个人日程规划...")
        
        workflow_chat = input_data.get('workflow_chat')
        
        # 获取配置参数
        start_date = input_data.get('start_date', '')
        end_date = input_data.get('end_date', '')
        total_days = input_data.get('total_days', 7)
        protagonist = input_data.get('protagonist', '方知衡')
        life_theme = input_data.get('life_theme', 'daily_routine')
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "日程规划",
                f"正在为{protagonist}制定{total_days}天的个人生活规划...",
                "progress"
            )
        
        try:
            # 生成日期列表
            dates_info = []
            current_date = datetime.strptime(start_date, '%Y-%m-%d')
            for day in range(total_days):
                date_obj = current_date + timedelta(days=day)
                date_str = date_obj.strftime('%Y-%m-%d')
                weekday = date_obj.weekday()
                weekday_name = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][weekday]
                
                # 检查节假日
                holidays_data = input_data.get('holidays_data', {})
                is_holiday = date_str in holidays_data
                holiday_info = holidays_data.get(date_str, {})
                holiday_name = holiday_info.get('name', '') if is_holiday else ''
                holiday_type = holiday_info.get('type', '') if is_holiday else ''
                
                dates_info.append({
                    'date': date_str,
                    'weekday': weekday,
                    'weekday_name': weekday_name,
                    'is_holiday': is_holiday,
                    'holiday_name': holiday_name,
                    'holiday_type': holiday_type,
                    'day_number': day + 1
                })
            
            # 构建规划数据
            planning_data = {
                'protagonist': protagonist,
                'start_date': start_date,
                'end_date': end_date,
                'total_days': total_days,
                'life_theme': life_theme,
                'dates_info': dates_info,
                'planning_complete': True
            }
            
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "日程规划",
                    f"✅ 成功规划{total_days}天的日期安排",
                    "success"
                )
            
            output_data = input_data.copy()
            output_data['planning_result'] = planning_data
            output_data['dates_info'] = dates_info
            
            logger.info(f"✅ 个人日程规划完成，生成了 {total_days} 天的规划")
            yield output_data
            
        except Exception as e:
            logger.error(f"个人日程规划失败: {e}")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "日程规划",
                    f"❌ 规划失败: {str(e)}",
                    "error"
                )
            raise Exception(f"个人日程规划失败: {str(e)}")


class PersonalScheduleGenerateNode(BaseNode):
    """个人日程生成节点"""
    
    def __init__(self):
        super().__init__(name="personal_generate", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行个人日程生成"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行个人日程生成"""
        print("📅 开始个人日程生成...")
        from datetime import datetime, timedelta
        try:
            workflow_chat = input_data.get('workflow_chat')
            llm = input_data.get('llm')
            
            # 判断是否为多周期迭代
            cycles = input_data.get('cycles', [])
            current_cycle_index = input_data.get('current_cycle_index', 0)
            if cycles:
                if current_cycle_index >= len(cycles):
                    raise Exception("当前周期索引超出范围")
                current_cycle = cycles[current_cycle_index]
                start_date = current_cycle['start_date']
                end_date = current_cycle['end_date']
                total_days = current_cycle['total_days']

                # 生成 dates_info 基于当前周期
                dates_info = []
                current_dt = datetime.strptime(start_date, '%Y-%m-%d')
                for i in range(total_days):
                    dt = current_dt + timedelta(days=i)
                    weekday = dt.weekday()
                    weekday_name = ['周一','周二','周三','周四','周五','周六','周日'][weekday]
                    date_str = dt.strftime('%Y-%m-%d')

                    is_holiday = False
                    holiday_name = ''
                    holidays_data = input_data.get('holidays_data', {})
                    if date_str in holidays_data:
                        is_holiday = True
                        holiday_name = holidays_data[date_str]['name']

                    dates_info.append({
                        'date': date_str,
                        'weekday': weekday,
                        'weekday_name': weekday_name,
                        'is_holiday': is_holiday,
                        'holiday_name': holiday_name,
                        'day_number': i+1
                    })
            else:
                # 兼容单周期老逻辑
                dates_info = input_data.get('dates_info', [])
                if not dates_info:
                    raise Exception("缺少日期规划数据")
 
            # start_date/end_date/total_days 已在上面处理（若多周期）；如果 dates_info 来自上级，则提取第一/最后日期。
            if cycles:
                pass  # start_date, end_date 已设置
            else:
                start_date = input_data.get('start_date', '')
                end_date = input_data.get('end_date', '')
                total_days = input_data.get('total_days', 7)
 
            protagonist = input_data.get('protagonist', '方知衡')
            protagonist_data = input_data.get('protagonist_data', '')
            life_theme = input_data.get('life_theme', 'daily_routine')
            
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "日程生成",
                    f"正在生成{protagonist}的{total_days}天个人日程...",
                    "progress"
                )
            
            # 构建生成提示词
            generation_prompt = f"""
你是一名专业的个人生活规划师，需要为{protagonist}生成{start_date}到{end_date}的详细个人日程安排（共{total_days}天）。

# 主角信息
{protagonist_data}

# 日期信息
{json.dumps(dates_info, ensure_ascii=False, indent=2)}

# 日程生成要求

## 核心原则
1. **个人视角**：专注{protagonist}的个人活动，不安排与他人的互动
2. **生活真实**：包含具体的时间、地点、活动内容和内心状态
3. **语句通顺**：content必须语句通顺，有主语{protagonist}在做什么
4. **详细具体**：每个时间段都要有具体的时间、地点信息和活动细节

## 内容要求

- content必须包含：时间+地点+{protagonist}在做什么+具体细节
- 语句必须通顺，有明确的主语和动作
- 避免空泛描述，要有具体的生活细节

# 输出格式
请按以下JSON格式输出个人日程安排：

```json
{{
  "personal_schedule_info": {{
    "protagonist": "{protagonist}",
    "start_date": "{start_date}",
    "end_date": "{end_date}",
    "total_days": {total_days},
    "life_theme": "{life_theme}"
  }},
  
  "daily_schedules": [
    {{
      "date": "YYYY-MM-DD",
      "day_number": 1,
      "weekday_name": "周几",
      "is_holiday": true/false,
      "holiday_name": "节日名称（如果是节假日）",
      "weather": "天气情况",
      "daily_theme": "今日主题",
      "daily_plan": "{protagonist}的个人计划安排，第三人称描述当天的具体打算",
      "time_slots": [
        {{
          "slot_name": "夜间",
          "content": "详细描述{protagonist}在这个时间段的具体活动，包含时间、地点、做什么、细节"
        }},
        {{
          "slot_name": "上午",
          "content": "详细描述{protagonist}上午的具体活动，包含时间、地点、做什么、细节"
        }},
        {{
          "slot_name": "中午",
          "content": "详细描述{protagonist}中午的具体活动，包含时间、地点、做什么、细节"
        }},
        {{
          "slot_name": "下午",
          "content": "详细描述{protagonist}下午的具体活动，包含时间、地点、做什么、细节"
        }},
        {{
          "slot_name": "晚上",
          "content": "详细描述{protagonist}晚上的具体活动，包含时间、地点、做什么、细节"
        }}
      ],
      "daily_summary": "第三人称，以{protagonist}为主体，一天结束时的简要总结"
    }}
  ],
  "period_summary": "这{total_days}天的个人生活总结"
}}
```

请生成{protagonist}的个人日程安排。
"""
            
            if not llm:
                raise Exception("LLM对象未初始化")
            
            # 调用LLM生成个人日程
            from core.types import Message, MessageRole
            message = Message(role=MessageRole.USER, content=generation_prompt)
            messages = [message]
            
            final_content = ""
            async for chunk_data in llm.stream_generate(
                messages, 
                mode="think",
                return_dict=True
            ):
                content_part = chunk_data.get("content", "")
                final_content += content_part
            
            logger.info(f"个人日程生成完成，内容长度: {len(final_content)} 字符")
            
            # 解析JSON结果
            schedule_data = None
            try:
                from parsers.json_parser import JSONParser
                parser = JSONParser()
                
                json_content = self._extract_json_from_content(final_content)
                parsed_result = parser.parse(json_content)
                
                if parsed_result and 'daily_schedules' in parsed_result:
                    schedule_data = parsed_result
                    logger.info(f"✅ 成功解析个人日程JSON，包含 {len(schedule_data['daily_schedules'])} 天日程")
                else:
                    raise Exception("解析结果缺少daily_schedules字段")
                    
            except Exception as parse_error:
                logger.error(f"个人日程JSON解析失败: {parse_error}")
                
                # 创建基础的个人日程数据作为后备
                schedule_data = {
                    'personal_schedule_info': {
                        'protagonist': protagonist,
                        'start_date': start_date,
                        'end_date': end_date,
                        'total_days': total_days,
                        'life_theme': life_theme
                    },
                    'daily_schedules': [],
                    'period_summary': f"{protagonist}的{total_days}天个人生活安排（解析失败，使用基础结构）"
                }
                
                if workflow_chat:
                    await workflow_chat.add_node_message(
                        "日程生成",
                        f"⚠️ JSON解析失败，使用基础日程结构",
                        "warning"
                    )
            
            # 保存个人日程到CSV
            await self._save_personal_schedule_to_csv(schedule_data)
            
            # 更新UI
            if workflow_chat:
                daily_schedules = schedule_data.get('daily_schedules', [])
                await workflow_chat.add_node_message(
                    "日程生成",
                    f"✅ 个人日程生成完成：共生成 {len(daily_schedules)} 天日程",
                    "success"
                )
            
            # 构建输出数据
            output_data = input_data.copy()
            output_data['personal_schedule'] = schedule_data
            output_data['daily_schedules'] = schedule_data.get('daily_schedules', [])
            output_data['generation_complete'] = True

            # 多周期：更新索引与完成标记
            if cycles:
                output_data['current_cycle_index'] = current_cycle_index + 1
                if current_cycle_index + 1 >= len(cycles):
                    output_data['generation_complete'] = True
                else:
                    output_data['generation_complete'] = False
 
            logger.info(f"✅ 个人日程生成完成")
            yield output_data
            
        except Exception as e:
            logger.error(f"个人日程生成失败: {e}")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "日程生成",
                    f"❌ 生成失败: {str(e)}",
                    "error"
                )
            raise Exception(f"个人日程生成失败: {str(e)}")
    
    async def _save_personal_schedule_to_csv(self, schedule_data: Dict[str, Any]):
        """保存个人日程到CSV文件"""
        try:
            from pathlib import Path
            import csv
            from datetime import datetime
            
            # 创建输出目录
            output_dir = Path("workspace/personal_schedule_output")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用时间戳创建文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_file_path = output_dir / f"personal_schedule_{timestamp}.csv"
            
            # 定义CSV列头
            csv_headers = [
                "日期", "星期", "节日信息", "天气", "每日主题", "每日计划", "每日总结",
                "夜间-活动", "上午-活动", "中午-活动", "下午-活动", "晚上-活动"
            ]
            
            # 获取日程信息
            schedule_info = schedule_data.get('personal_schedule_info', {})
            daily_schedules = schedule_data.get('daily_schedules', [])
            
            # 写入CSV文件
            with open(csv_file_path, 'w', encoding='utf-8', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(csv_headers)
                
                # 遍历每天的日程数据
                for day_data in daily_schedules:
                    date = day_data.get('date', '')
                    weekday = day_data.get('weekday_name', '')
                    is_holiday = day_data.get('is_holiday', False)
                    holiday_name = day_data.get('holiday_name', '')
                    weather = day_data.get('weather', '')
                    daily_theme = day_data.get('daily_theme', '')
                    daily_plan = day_data.get('daily_plan', '')
                    daily_summary = day_data.get('daily_summary', '')
                    
                    # 节日信息处理
                    holiday_info = holiday_name if is_holiday and holiday_name else "无"
                    
                    # 初始化时间段数据
                    time_slots_data = {
                        '夜间': '',
                        '上午': '',
                        '中午': '',
                        '下午': '',
                        '晚上': ''
                    }
                    
                    # 提取时间段数据
                    time_slots = day_data.get('time_slots', [])
                    for slot in time_slots:
                        slot_name = slot.get('slot_name', '')
                        if slot_name in time_slots_data:
                            time_slots_data[slot_name] = slot.get('content', '')
                    
                    # 构建CSV行数据
                    row_data = [
                        date, weekday, holiday_info, weather, daily_theme, daily_plan, daily_summary,
                        time_slots_data['夜间'], time_slots_data['上午'], time_slots_data['中午'], 
                        time_slots_data['下午'], time_slots_data['晚上']
                    ]
                    
                    writer.writerow(row_data)
            
            logger.info(f"个人日程CSV保存成功: {csv_file_path}")
            logger.info(f"包含 {len(daily_schedules)} 天的个人日程数据")
            
        except Exception as e:
            logger.error(f"保存个人日程CSV失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _extract_json_from_content(self, content: str) -> str:
        """从生成内容中提取JSON部分"""
        import re
        import json
        
        logger.info(f"开始提取JSON，原始内容长度: {len(content)}")
        
        # 查找```json...```代码块
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            extracted_json = match.strip()
            if self._is_valid_json(extracted_json):
                logger.info(f"✅ 从```json```代码块提取有效JSON，长度: {len(extracted_json)}")
                return extracted_json
        
        # 查找```...```代码块
        code_pattern = r'```[a-zA-Z]*\s*(.*?)\s*```'
        code_matches = re.findall(code_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in code_matches:
            extracted = match.strip()
            if extracted.startswith('{') and self._is_valid_json(extracted):
                logger.info(f"✅ 从代码块提取有效JSON，长度: {len(extracted)}")
                return extracted
        
        logger.warning("❌ 未能提取有效JSON，返回原内容")
        return content.strip()
    
    def _is_valid_json(self, json_str: str) -> bool:
        """验证JSON字符串是否有效"""
        try:
            json.loads(json_str)
            return True
        except (json.JSONDecodeError, ValueError):
            return False


class PersonalCyclePlanningNode(BaseNode):
    """简化版周期规划节点：只考虑主角与日期，将整体区间拆分为若干周期，不涉及其他角色。"""

    def __init__(self):
        super().__init__(name="personal_cycle_planning", stream=False)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        from datetime import datetime, timedelta
        import random
        workflow_chat = input_data.get('workflow_chat')

        start_date = input_data.get('start_date', '')
        total_days = input_data.get('total_days', 7)

        if not start_date:
            raise Exception("缺少 start_date")

        start_dt = datetime.strptime(start_date, '%Y-%m-%d')

        remaining_days = total_days
        cycle_num = 1
        cycles = []
        current_dt = start_dt

        min_cycle, max_cycle = 7, 15

        while remaining_days > 0:
            if remaining_days <= max_cycle:
                cycle_days = remaining_days
            else:
                # 保证最后一个周期不少于 min_cycle
                if remaining_days <= max_cycle + min_cycle:
                    cycle_days = remaining_days // 2
                else:
                    cycle_days = random.randint(min_cycle, max_cycle)

            end_dt = current_dt + timedelta(days=cycle_days - 1)
            cycles.append({
                'cycle_number': cycle_num,
                'start_date': current_dt.strftime('%Y-%m-%d'),
                'end_date': end_dt.strftime('%Y-%m-%d'),
                'total_days': cycle_days,
                'cycle_theme': f"个人成长周期{cycle_num}",
                'main_objectives': [],
                'core_locations': []
            })

            remaining_days -= cycle_days
            current_dt = end_dt + timedelta(days=1)
            cycle_num += 1

        if workflow_chat:
            await workflow_chat.add_node_message(
                "周期规划",
                f"已将 {total_days} 天拆分为 {len(cycles)} 个周期",
                "success"
            )

        output_data = input_data.copy()
        output_data['cycles'] = cycles
        output_data['current_cycle_index'] = 0

        return output_data


async def main():
    """本地主函数 - 执行个人日程生成"""
    import argparse
    from datetime import datetime, timedelta
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # 命令行参数
    parser = argparse.ArgumentParser(description='个人日程生成工作流v2 - 本地执行')
    parser.add_argument('--start-date', default='2025-07-15', help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=7, help='天数')
    parser.add_argument('--theme', default='daily_routine', help='生活主题')
    
    args = parser.parse_args()
    
    print(f"🚀 个人日程生成工作流v2启动")
    print(f"📅 开始日期: {args.start_date}")
    print(f"📊 天数: {args.days}")
    print(f"🎯 主题: {args.theme}")
    
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
        workflow = ScheduleWorkflowV2(llm=llm)
        
        print(f"✅ LLM和工作流初始化成功")
        
        # 计算结束日期
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_date = start_date + timedelta(days=args.days - 1)
        
        # 构建配置
        config = {
            'protagonist': '方知衡',
            'schedule_type': 'personal',
            'start_date': args.start_date,
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_days': args.days,
            'life_theme': args.theme,
            'personal_focus': True,
            'include_holidays': True
        }
        
        print(f"📋 配置信息:")
        print(f"  日期范围: {config['start_date']} - {config['end_date']} ({config['total_days']}天)")
        print(f"  生活主题: {config['life_theme']}")
        
        # 创建简化的工作流聊天接口
        class LocalWorkflowChat:
            def __init__(self):
                self.current_node = ""
            
            async def add_node_message(self, node_name: str, message: str, status: str):
                clean_message = message.replace('✅', '[完成]').replace('❌', '[失败]').replace('⚠️', '[警告]').replace('🔄', '[进行中]')
                if status in ['success', 'error', 'warning']:
                    print(f"  [{node_name}] {clean_message}")
            
            def _create_workflow_progress(self):
                return ""
        
        # 执行工作流
        workflow_chat = LocalWorkflowChat()
        print(f"🚀 开始执行个人日程工作流...")
        
        progress_count = 0
        async for stream_event in workflow.execute_workflow_stream(config, workflow_chat):
            progress_count += 1
            
            # 检查是否完成
            if isinstance(stream_event, tuple) and len(stream_event) >= 4:
                html, content, message, is_complete = stream_event
                if "执行完成" in message or "生成完成" in message:
                    print(f"    ✅ 检测到完成信号: {message}")
        
        print(f"🎉 个人日程工作流执行完成")
        print(f"📊 工作流执行过程中收到 {progress_count} 次事件")
        print(f"📁 输出文件: workspace/personal_schedule_output/")
        
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
    project_root = current_dir.parent.parent
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(current_dir.parent))
    
    asyncio.run(main())