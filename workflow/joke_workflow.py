"""笑话生成工作流 - 基于方知衡人设的笑话创作系统
根据主角的性格特点生成符合人设的幽默内容，支持批量生成几千条不重样的笑话
"""

import json
import asyncio
import random
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.graph import StateGraph
from core.base import BaseNode
from llm.base import LLMFactory
from core.types import LLMConfig, TaskResult, Message, MessageRole

logger = logging.getLogger(__name__)

class JokeWorkflow:
    """笑话生成工作流管理器"""
    
    def __init__(self, llm=None):
        self.llm = llm
        self.graph = None

        self.current_config = {
            'batch_size': 50,  # 每批生成的笑话数量
            'total_target': 1000,  # 总目标数量
            'joke_categories': [
                '哲学日常梗', '科学双关梗', '逻辑生活梗', 
                '文字游戏梗', '生活科学梗', '反差幽默梗'
            ],
            'difficulty_levels': ['简单', '中等', '复杂'],
            'humor_styles': ['冷幽默', '自嘲', '观察式', '反差萌'],
            'csv_output': {
                'enabled': True,
                'output_dir': 'workspace/joke_output',
                'filename': 'jokes_batch_output.csv',
                'encoding': 'utf-8-sig'  # 支持中文的CSV编码
            },
            'database_enabled': True,  # 启用数据库功能
            'pg_config': {
                'host': 'localhost',
                'port': 5432,
                'database': 'postgres',  # 使用默认的postgres数据库
                'user': 'postgres',
                'password': '12345'  # 你的数据库密码
            }
        }
        
        # 初始化数据库（如果启用）
        if self.current_config.get('database_enabled', False):
            self._init_database()
        else:
            self.current_config['database_available'] = False
            logger.info("数据库功能已禁用，将仅使用CSV保存")
    
    def _test_database_connection(self) -> bool:
        """测试数据库连接是否可用"""
        try:
            pg_config = self.current_config['pg_config']
            conn = psycopg2.connect(**pg_config)
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"数据库连接测试失败: {e}")
            return False

    def _init_database(self):
        """初始化PostgreSQL数据库和表结构"""
        # 先测试连接
        if not self._test_database_connection():
            logger.warning("数据库连接失败，将跳过数据库相关操作")
            self.current_config['database_available'] = False
            return
            
        try:
            pg_config = self.current_config['pg_config']
            
            # 连接数据库
            conn = psycopg2.connect(**pg_config)
            cursor = conn.cursor()
            
            # 创建笑话表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS jokes (
                id SERIAL PRIMARY KEY,
                joke_id VARCHAR(50) UNIQUE NOT NULL,
                category VARCHAR(50) NOT NULL,
                difficulty_level VARCHAR(20) NOT NULL,
                humor_style VARCHAR(30) NOT NULL,
                setup TEXT NOT NULL,
                punchline TEXT NOT NULL,
                context TEXT,
                character_traits TEXT[],
                tags TEXT[],
                rating INTEGER DEFAULT 0,
                is_used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_jokes_category ON jokes(category);
            CREATE INDEX IF NOT EXISTS idx_jokes_rating ON jokes(rating);
            CREATE INDEX IF NOT EXISTS idx_jokes_created_at ON jokes(created_at);
            """
            
            cursor.execute(create_table_sql)
            conn.commit()
            
            cursor.close()
            conn.close()
            
            logger.info("数据库表结构初始化完成")
            self.current_config['database_available'] = True
            
        except Exception as e:
            logger.warning(f"数据库初始化失败，将跳过数据库相关操作: {e}")
            # 设置标志，表示数据库不可用
            self.current_config['database_available'] = False
    
    def update_config(self, config_updates: Dict[str, Any]):
        """更新工作流配置"""
        self.current_config.update(config_updates)
    
    async def create_joke_graph(self) -> StateGraph:
        """创建笑话生成图工作流"""
        self.graph = StateGraph(name="joke_generation_workflow")
        
        # 创建节点
        theme_planning_node = ThemePlanningNode()  # 主题规划节点
        joke_generate_node = JokeGenerateNode()   # 笑话生成节点
        database_save_node = JokeDatabaseSaveNode()  # 数据库保存节点
        
        # 添加节点到图
        self.graph.add_node("theme_planning", theme_planning_node)
        self.graph.add_node("joke_generate", joke_generate_node)
        self.graph.add_node("database_save", database_save_node)
        
        # 定义节点连接关系
        self.graph.add_edge("theme_planning", "joke_generate")
        self.graph.add_edge("joke_generate", "database_save")
        
        # 新增条件边：如果尚未完成全部批次，则回到笑话生成节点
        def loop_condition(state):
            """当尚未完成全部批次时继续循环到 joke_generate，否则结束"""
            if state.get('generation_complete', False):
                return "__end__"
            return "joke_generate"
        
        self.graph.add_conditional_edges("database_save", loop_condition)
        
        # 设置入口点
        self.graph.set_entry_point("theme_planning")
        
        return self.graph
    
    async def execute_workflow_stream(self, config: Dict[str, Any], workflow_chat):
        """流式执行笑话生成工作流"""
        try:
            # 准备初始输入
            initial_input = {
                'config': config,
                'batch_size': config.get('batch_size', 50),
                'total_target': config.get('total_target', 1000),
                'joke_categories': config.get('joke_categories', self.current_config['joke_categories']),
                'difficulty_levels': config.get('difficulty_levels', self.current_config['difficulty_levels']),
                'humor_styles': config.get('humor_styles', self.current_config['humor_styles']),
                'pg_config': config.get('pg_config', self.current_config['pg_config']),
                'workflow_chat': workflow_chat,
                'llm': self.llm
            }
            
            # 创建并编译图工作流
            if not self.graph:
                await self.create_joke_graph()
            
            compiled_graph = self.graph.compile()
            
            # 使用图的流式执行
            async for stream_event in compiled_graph.stream(initial_input):
                event_type = stream_event.get('type')
                node_name = stream_event.get('node')
                
                if event_type == 'start':
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        "笑话生成工作流开始执行...",
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
                        content_length = 0
                        for key in ['jokes_data', 'generated_jokes', 'checked_jokes']:
                            if key in intermediate_result.state_update:
                                if isinstance(intermediate_result.state_update[key], list):
                                    content_length = len(intermediate_result.state_update[key])
                                break
                        
                        if content_length > 0:
                            node_display_name = self._get_node_display_name(node_name)
                            await workflow_chat.add_node_message(
                                node_display_name,
                                f"正在处理笑话内容... 当前数量: {content_length}",
                                "streaming"
                            )
                            
                            yield (
                                workflow_chat._create_workflow_progress(),
                                "",
                                f"正在处理笑话... 当前数量: {content_length}",
                                False
                            )
                
                elif event_type == 'node_complete':
                    node_display_name = self._get_node_display_name(node_name)
                    
                    if node_name == 'joke_generate':
                        result_content = "✅ 笑话生成完成"
                        if 'generated_jokes' in stream_event.get('output', {}):
                            jokes_data = stream_event['output']['generated_jokes']
                            if isinstance(jokes_data, list):
                                result_content = f"✅ 已成功生成{len(jokes_data)}条笑话"
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
                        "笑话生成工作流执行完成",
                        False
                    )
                
                else:
                    yield (
                        workflow_chat._create_workflow_progress(),
                        "",
                        "笑话生成工作流执行中...",
                        False
                    )
                
        except Exception as e:
            logger.error(f"笑话生成工作流流式执行失败: {e}")
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
            'theme_planning': '主题规划',
            'joke_generate': '笑话生成',
            'quality_check': '质量检查',
            'database_save': '数据库保存'
        }
        return name_mapping.get(node_name, node_name)
    
    def _get_node_id(self, node_name: str) -> str:
        """获取节点ID"""
        id_mapping = {
            'theme_planning': 'planning',
            'joke_generate': 'generate',
            'quality_check': 'check',
            'database_save': 'save'
        }
        return id_mapping.get(node_name, node_name)

    def enable_database(self, pg_config: Optional[Dict] = None):
        """手动启用数据库功能"""
        if pg_config:
            self.current_config['pg_config'].update(pg_config)
        
        self.current_config['database_enabled'] = True
        self._init_database()
        
        if self.current_config.get('database_available', False):
            logger.info("✅ 数据库功能已成功启用")
            return True
        else:
            logger.warning("⚠️ 数据库启用失败，将继续使用CSV保存")
            return False


class ThemePlanningNode(BaseNode):
    """主题规划节点 - 根据人设特点规划笑话主题和风格"""
    
    def __init__(self):
        super().__init__(name="theme_planning", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行主题规划节点 - 非流式版本"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行主题规划节点"""
        print("🎯 开始主题规划...")
        
        workflow_chat = input_data.get('workflow_chat')
        
        # 获取配置参数
        batch_size = input_data.get('batch_size', 50)
        total_target = input_data.get('total_target', 1000)
        joke_categories = input_data.get('joke_categories', [])
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "主题规划",
                f"正在规划{total_target}条笑话的主题分布...",
                "progress"
            )
        
        try:
            # 计算需要多少个批次
            total_batches = (total_target + batch_size - 1) // batch_size
            
            # 为每个批次分配主题
            theme_plan = {
                'total_batches': total_batches,
                'batch_size': batch_size,
                'category_distribution': {},
                'batch_themes': []
            }
            
            # 平衡分配各个类别
            categories_per_batch = max(1, len(joke_categories) // total_batches)
            
            for batch_idx in range(total_batches):
                # 为当前批次选择主题类别
                start_cat = (batch_idx * categories_per_batch) % len(joke_categories)
                end_cat = min(start_cat + categories_per_batch, len(joke_categories))
                batch_categories = joke_categories[start_cat:end_cat]
                
                # 如果类别不够，从头开始补充
                if len(batch_categories) < categories_per_batch:
                    remaining = categories_per_batch - len(batch_categories)
                    batch_categories.extend(joke_categories[:remaining])
                
                batch_theme = {
                    'batch_number': batch_idx + 1,
                    'categories': batch_categories,
                    'focus_trait': self._get_focus_trait(batch_idx),
                    'humor_emphasis': self._get_humor_emphasis(batch_idx)
                }
                
                theme_plan['batch_themes'].append(batch_theme)
            
            # 统计类别分布
            for theme in theme_plan['batch_themes']:
                for cat in theme['categories']:
                    theme_plan['category_distribution'][cat] = theme_plan['category_distribution'].get(cat, 0) + 1
            
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "主题规划",
                    f"✅ 规划完成：{total_batches}个批次，平衡分配{len(joke_categories)}个主题类别",
                    "success"
                )
            
            # 输出结果
            output_data = input_data.copy()
            output_data['theme_plan'] = theme_plan
            output_data['current_batch_index'] = 0
            
            logger.info(f"✅ 主题规划完成，生成了{total_batches}个批次的主题分配")
            yield output_data
            
        except Exception as e:
            logger.error(f"主题规划失败: {e}")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "主题规划",
                    f"❌ 规划失败: {str(e)}",
                    "error"
                )
            raise Exception(f"主题规划失败: {str(e)}")
    
    def _get_focus_trait(self, batch_idx: int) -> str:
        """根据批次获取重点人设特征"""
        traits = [
            '理性严谨', '内敛温和', '毒奶体质', '网络落伍',
            '古板认真', '学术专注', '生活细致', '温和吐槽'
        ]
        return traits[batch_idx % len(traits)]
    
    def _get_humor_emphasis(self, batch_idx: int) -> str:
        """根据批次获取幽默重点"""
        emphasis = [
            '冷幽默', '自嘲式', '观察式', '反差萌',
            '学者风范', '生活智慧', '意外惊喜', '温和吐槽'
        ]
        return emphasis[batch_idx % len(emphasis)]


class JokeGenerateNode(BaseNode):
    """笑话生成节点 - 基于人设生成符合特点的笑话"""
    
    def __init__(self):
        super().__init__(name="joke_generate", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行笑话生成节点 - 非流式版本"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行笑话生成节点 - 分批生成"""
        print("😄 开始笑话生成...")
        
        workflow_chat = input_data.get('workflow_chat')
        llm = input_data.get('llm')
        
        # 获取主题规划数据
        theme_plan = input_data.get('theme_plan', {})
        current_batch_index = input_data.get('current_batch_index', 0)
        batch_themes = theme_plan.get('batch_themes', [])
        
        if not batch_themes or current_batch_index >= len(batch_themes):
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "笑话生成",
                    "✅ 所有批次的笑话生成已完成！",
                    "success"
                )
            
            output_data = input_data.copy()
            output_data['generation_complete'] = True
            yield output_data
            return
        
        # 获取当前批次信息
        current_batch = batch_themes[current_batch_index]
        batch_categories = current_batch['categories']
        focus_trait = current_batch['focus_trait']
        humor_emphasis = current_batch['humor_emphasis']
        batch_size = input_data.get('batch_size', 10)
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "笑话生成",
                f"正在生成第 {current_batch_index + 1}/{len(batch_themes)} 批次笑话（{batch_size}条）...",
                "progress"
            )
        
        # 构建笑话生成提示词
        
        generation_prompt = f"""
请创作{batch_size}条真正好笑的笑话，重点是要让人笑出来！

## 笑话结构要求
每条笑话包含：
- **关键词**：搜索用关键词组，用逗号分隔，包含：主题，适用场合，情境等，方便检索，不要重复笑话内容
- **笑话内容**：完整的笑话，包含情境和笑点，100-250字

## 笑话创作方向
谐音梗，谐音双关，符合以下要求：
- 轻松有趣，让人想笑
- 符合爱上网年轻人的口味，有网感
- 让人听完笑话有一种 你牛逼的感觉

# 示例
m和n打架了 m最后认错了，因为I'm sorry。
小动物们聚餐，只有小象很生气，原来这是一个气象局。
为什么柯南永远都穿那套衣服?因为他怕被别人说:哎唷:是新衣哦。
有一块玻璃它有点困了然后它从楼上跳下来并且说:晚安我碎啦!
小朋友的巧克力融化掉在了地上，小朋友说好像泥呀好像泥呀，你听见了吗，好想你。
螃蟹出门散步不小心撞到了泥鳅，泥鳅很生气:"你是不是瞎啊?"螃蟹很委屈:"不是啊，我是螃蟹!"
两个大爷在下棋，小孩:大爷你车没了。大爷:什么车，这叫 ju。小孩:哦，大爷你自行 ju 被人骑走了。
刚刚出门买生蚝,走出超市他们突然跳出袋子钻进土里，回来一想，原来是蚝喜欢泥。
诸葛亮火烧赤壁，借东风，借了八次,就变成了诸八借!
你知道吗?哆啦A梦没有脖子是出于卫生考虑。为什么?因为“蓝脖积泥”
小鸭子对小鸡说:“小鸡，我喜欢你”小鸡:你 duck不必。

# 输出格式
请按以下JSON格式输出{batch_size}条笑话，禁止输出任何其他内容：

```json
{{
  "jokes": [
    {{
      "关键词": "简短主题关键词",
      "笑话内容": "完整笑话内容"
    }},
    {{
      "关键词": "简短主题关键词", 
      "笑话内容": "完整笑话内容"
    }},
    // ... 继续到第{batch_size}条
  ]
}}
```
"""
        
        # 调用LLM生成笑话
        if llm:
            try:
                from core.types import Message, MessageRole
                message = Message(role=MessageRole.USER, content=generation_prompt)
                messages = [message]
                
                logger.info(f"笑话生成批次 {current_batch_index + 1}: 开始LLM调用")
                
                # 流式调用LLM
                final_content = ""
                async for chunk_data in llm.stream_generate(
                    messages, 
                    mode="think",
                    return_dict=True
                ):
                    content_part = chunk_data.get("content", "")
                    final_content += content_part
                
                logger.info(f"批次 {current_batch_index + 1} LLM生成完成，内容长度: {len(final_content)}")
                        
            except Exception as e:
                error_msg = f"批次 {current_batch_index + 1} LLM调用失败: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise Exception(error_msg)
        else:
            raise Exception("LLM未初始化")
        
        # 解析JSON结果
        jokes_data = None
        try:
            json_content = self._extract_json_from_content(final_content)
            from parsers.json_parser import JSONParser
            parser = JSONParser()
            parsed_result = parser.parse(json_content)
            
            if parsed_result and 'jokes' in parsed_result:
                jokes_data = parsed_result
                generated_jokes = jokes_data.get('jokes', [])
                logger.info(f"批次 {current_batch_index + 1} 成功解析，包含 {len(generated_jokes)} 条笑话")
                
                if workflow_chat:
                    await workflow_chat.add_node_message(
                        "笑话生成",
                        f"✅ 批次 {current_batch_index + 1} 生成完成（{len(generated_jokes)}条笑话）",
                        "success"
                    )
            else:
                raise Exception(f"批次解析失败：缺少jokes字段")
                
        except Exception as parse_error:
            logger.error(f"批次 {current_batch_index + 1} JSON解析失败: {parse_error}")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "笑话生成",
                    f"⚠️ 批次 {current_batch_index + 1} 解析失败，跳过",
                    "warning"
                )
            jokes_data = None
        
        # 构建输出数据
        output_data = input_data.copy()
        output_data['generated_jokes'] = jokes_data.get('jokes', []) if jokes_data else []
        output_data['current_batch_index'] = current_batch_index + 1
        
        print(f"✅ 批次 {current_batch_index + 1} 笑话生成完成")
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
        
        return content.strip()





class JokeDatabaseSaveNode(BaseNode):
    """数据库保存节点 - 将检查过的笑话保存到PostgreSQL"""
    
    def __init__(self):
        super().__init__(name="joke_database_save", stream=True)
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据库保存节点 - 非流式版本"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行数据库保存节点"""
        print("💾 开始保存笑话数据...")
        
        workflow_chat = input_data.get('workflow_chat')
        generated_jokes = input_data.get('generated_jokes', [])
        pg_config = input_data.get('pg_config', {})
        config = input_data.get('config', {})
        current_batch_index = input_data.get('current_batch_index', 1)
        
        if not generated_jokes:
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "数据库保存",
                    "⚠️ 没有笑话需要保存",
                    "warning"
                )
            yield input_data
            return
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "数据库保存",
                f"正在保存第{current_batch_index}批次的{len(generated_jokes)}条笑话...",
                "progress"
            )
        
        # 先保存到CSV文件（增量更新）
        csv_save_result = await self._save_to_csv(generated_jokes, current_batch_index, workflow_chat, config)
        
        # 如果数据库可用，再保存到数据库
        db_save_result = None
        if config.get('database_enabled', False) and config.get('database_available', True) != False:
            db_save_result = await self._save_to_database(generated_jokes, pg_config, workflow_chat)
        else:
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "数据库保存",
                    "⚠️ 数据库功能已禁用，跳过数据库保存",
                    "warning"
                )
        
        # 构建最终输出
        output_data = input_data.copy()
        output_data.update({
            'csv_save_result': csv_save_result,
            'db_save_result': db_save_result,
            'save_success': csv_save_result.get('success', False) or (db_save_result and db_save_result.get('success', False)),
            'save_message': self._build_save_message(csv_save_result, db_save_result)
        })
        
        yield output_data
    
    async def _save_to_csv(self, generated_jokes: List[Dict], current_batch_index: int, workflow_chat=None, config=None) -> Dict:
        """保存笑话到CSV文件，支持增量更新"""
        try:
            import csv
            from datetime import datetime
            
            # 获取CSV配置
            csv_config = config.get('csv_output', {}) if config else {}
            output_dir = csv_config.get('output_dir', 'workspace/joke_output')
            filename = csv_config.get('filename', 'jokes_batch_output.csv')
            encoding = csv_config.get('encoding', 'utf-8-sig')
            
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # CSV文件路径
            csv_file = os.path.join(output_dir, filename)
            
            # 检查文件是否存在，决定是否写入表头
            file_exists = os.path.exists(csv_file)
            
            # 写入CSV文件（追加模式）
            with open(csv_file, 'a', newline='', encoding=encoding) as f:
                fieldnames = ['批次', '关键词', '笑话内容', '生成时间']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # 如果文件不存在，先写入表头
                if not file_exists:
                    writer.writeheader()
                
                # 写入当前批次的笑话
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for joke in generated_jokes:
                    writer.writerow({
                        '批次': f"第{current_batch_index}批",
                        '关键词': joke.get('关键词', ''),
                        '笑话内容': joke.get('笑话内容', ''),
                        '生成时间': timestamp
                    })
            
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "CSV保存",
                    f"✅ 第{current_batch_index}批次{len(generated_jokes)}条笑话已保存到CSV文件",
                    "success"
                )
            
            logger.info(f"✅ CSV保存完成：第{current_batch_index}批次{len(generated_jokes)}条笑话保存到 {csv_file}")
            
            return {
                'success': True,
                'count': len(generated_jokes),
                'file_path': csv_file,
                'batch_index': current_batch_index
            }
            
        except Exception as e:
            logger.error(f"CSV保存失败: {e}")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "CSV保存",
                    f"❌ CSV保存失败: {str(e)}",
                    "error"
                )
            
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _save_to_database(self, generated_jokes: List[Dict], pg_config: Dict, workflow_chat=None) -> Dict:
        """保存笑话到PostgreSQL数据库"""
        try:
            # 连接数据库
            conn = psycopg2.connect(**pg_config)
            cursor = conn.cursor()
            
            # 批量插入笑话
            success_count = 0
            duplicate_count = 0
            error_count = 0
            
            for joke in generated_jokes:
                try:
                    # 生成唯一ID
                    import uuid
                    joke_id = str(uuid.uuid4())[:8]
                    
                    insert_sql = """
                    INSERT INTO jokes (
                        joke_id, category, difficulty_level, humor_style,
                        setup, punchline, context, character_traits, tags, rating
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (joke_id) DO NOTHING
                    """
                    
                    cursor.execute(insert_sql, (
                        joke_id,
                        '自由创作',
                        '中等',
                        '冷幽默',
                        joke.get('关键词', ''),
                        joke.get('笑话内容', ''),
                        '',
                        [],
                        joke.get('关键词', '').split(','),
                        80
                    ))
                    
                    if cursor.rowcount > 0:
                        success_count += 1
                    else:
                        duplicate_count += 1
                        
                except Exception as e:
                    logger.warning(f"保存单条笑话失败: {e}")
                    error_count += 1
                    continue
            
            # 提交事务
            conn.commit()
            cursor.close()
            conn.close()
            
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "数据库保存",
                    f"✅ 数据库保存完成：{success_count}条成功，{duplicate_count}条重复，{error_count}条失败",
                    "success"
                )
            
            logger.info(f"✅ 数据库保存完成：{success_count}条成功保存")
            
            return {
                'success': True,
                'success_count': success_count,
                'duplicate_count': duplicate_count,
                'error_count': error_count
            }
            
        except Exception as e:
            logger.error(f"数据库保存失败: {e}")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "数据库保存",
                    f"❌ 数据库保存失败: {str(e)}",
                    "error"
                )
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _build_save_message(self, csv_result: Dict, db_result: Dict) -> str:
        """构建保存结果消息"""
        messages = []
        
        if csv_result and csv_result.get('success'):
            messages.append(f"CSV保存成功({csv_result.get('count', 0)}条)")
        elif csv_result:
            messages.append(f"CSV保存失败({csv_result.get('error', '未知错误')})")
        
        if db_result and db_result.get('success'):
            messages.append(f"数据库保存成功({db_result.get('success_count', 0)}条)")
        elif db_result:
            messages.append(f"数据库保存失败({db_result.get('error', '未知错误')})")
        
        return "; ".join(messages) if messages else "保存完成"


# 本地测试运行入口
async def main():
    """本地测试运行笑话生成工作流"""
    print("🎭 启动方知衡笑话生成工作流本地测试...")
    
    # 简单的模拟聊天界面
    class MockWorkflowChat:
        def __init__(self):
            self.current_node = ""
        
        async def add_node_message(self, node_name: str, message: str, status: str):
            print(f"[{node_name}] {status}: {message}")
        
        def _create_workflow_progress(self):
            return "<div>工作流进度</div>"
    
    try:
        # 配置LLM（如果有有效的API密钥）
        llm = None
        try:
            from llm.doubao import DoubaoLLM
            from core.types import LLMConfig
            
            # 这里使用测试配置，实际使用时需要替换为真实的API密钥
            llm_config = LLMConfig(
                provider="doubao",
                model_name="ep-20241230141654-5tvbr",
                api_key="b633a622-b5d0-4f16-a8a9-616239cf15d1",  # 替换为真实的API密钥
                api_base="https://ark.cn-beijing.volces.com/api/v3"
            )
            llm = DoubaoLLM(config=llm_config)
            print("✅ LLM配置成功")
        except Exception as e:
            print(f"⚠️ LLM配置失败，将跳过实际生成: {e}")
        
        # 初始化工作流
        workflow = JokeWorkflow(llm=llm)
        print("✅ 笑话工作流初始化完成")
        
        # 尝试启用数据库（使用正确的密码）
        db_config = {
            'password': '12345'  # 使用你的数据库密码
        }
        if workflow.enable_database(db_config):
            print("✅ 数据库功能已启用，笑话将同时保存到数据库和CSV")
        else:
            print("⚠️ 数据库连接失败，将仅保存到CSV文件")
        
        # 测试配置
        test_config = {
            'total_target': 5000,  # 生成1000条笑话
            'batch_size': 10,
            'joke_categories': [
                '哲学日常梗', '科学双关梗', '逻辑生活梗', 
                '文字游戏梗', '生活科学梗', '反差幽默梗'
            ],
            'database_enabled': False,  # 启用数据库功能
            'csv_output': {
                'enabled': True,
                'output_dir': 'workspace/joke_output',
                'filename': 'jokes_batch_output.csv',
                'encoding': 'utf-8-sig'
            }
        }
        
        print(f"📊 测试配置: {test_config}")
        
        # 创建模拟聊天界面
        mock_chat = MockWorkflowChat()
        
        # 创建工作流图
        graph = await workflow.create_joke_graph()
        compiled_graph = graph.compile()
        print("✅ 工作流图创建完成")
        
        # 准备输入数据
        input_data = {
            'config': test_config,
            'batch_size': test_config['batch_size'],
            'total_target': test_config['total_target'],
            'joke_categories': test_config['joke_categories'],
            'difficulty_levels': ['简单', '中等', '复杂'],
            'humor_styles': ['冷幽默', '自嘲', '观察式', '反差萌'],
            'pg_config': {},
            'workflow_chat': mock_chat,
            'llm': llm
        }
        
        print("\n🚀 开始执行笑话生成工作流...")
        
        # 执行工作流
        final_result = None
        async for result in compiled_graph.stream(input_data):
            if result:
                final_result = result
        
        # 显示结果
        if final_result:
            print("\n✅ 工作流执行完成!")
            
            generated_jokes = final_result.get('generated_jokes', [])
            print(f"📝 生成笑话数量: {len(generated_jokes)}")
            
            if generated_jokes:
                print("\n🎭 生成的笑话示例:")
                for i, joke in enumerate(generated_jokes[:5], 1):  # 显示前5条
                    print(f"\n--- 笑话 {i} ---")
                    print(f"关键词: {joke.get('关键词', 'N/A')}")
                    print(f"内容: {joke.get('笑话内容', 'N/A')}")
                    print("-" * 50)
                
                # 显示CSV保存结果
                csv_result = final_result.get('csv_save_result', {})
                if csv_result.get('success'):
                    csv_file = csv_result.get('file_path', '未知')
                    print(f"\n💾 CSV结果已保存到: {csv_file}")
                else:
                    print(f"\n⚠️ CSV保存失败: {csv_result.get('error', '未知错误')}")
                
                # 额外保存JSON备份
                import json
                from datetime import datetime
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"workspace/joke_output/backup_jokes_{timestamp}.json"
                
                # 确保目录存在
                os.makedirs(os.path.dirname(backup_file), exist_ok=True)
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'config': test_config,
                        'generated_jokes': generated_jokes,
                        'total_count': len(generated_jokes),
                        'timestamp': timestamp,
                        'csv_save_result': csv_result
                    }, f, ensure_ascii=False, indent=2)
                
                print(f"💾 JSON备份已保存到: {backup_file}")
            
            else:
                print("⚠️ 没有生成笑话（可能是API密钥无效或网络问题）")
        
        else:
            print("❌ 工作流执行失败")
    
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    """直接运行此文件进行本地测试"""
    print("🎭 方知衡笑话生成工作流 - 本地测试模式")
    print("=" * 60)
    
    # 运行异步主函数
    asyncio.run(main())