"""对话故事生成器 - 直接生成适合分享的对话故事
无需前置图片描述，直接生成温馨有趣的对话故事，并保存为CSV文件
"""

import os
import csv
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.base import BaseNode
from core.types import Message, MessageRole

logger = logging.getLogger(__name__)

class TalkStoryGenerationNode(BaseNode):
    """对话故事生成节点 - 直接生成适合与亲密的人分享的对话故事"""
    
    def __init__(self):
        super().__init__(name="talk_story_generation", stream=True)
        self.protagonist_data = ""
        self._load_protagonist_data()
    
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
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行对话故事生成节点"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行对话故事生成节点 - 支持批量处理和增量保存"""
        print("📝 开始生成对话故事...")
        
        workflow_chat = input_data.get('workflow_chat')
        llm = input_data.get('llm')
        story_count = input_data.get('story_count', 5)  # 默认生成5个故事
        topics = input_data.get('topics', [])  # 可选的话题列表
        output_dir = input_data.get('output_dir', 'workspace/talk_story_output')
        batch_size = input_data.get('batch_size', 5)  # 默认每批处理5个故事
        
        if not llm:
            # LLM未初始化，无法生成故事
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "对话故事生成",
                    "⚠️ LLM未初始化，无法生成对话故事",
                    "warning"
                )
            
            output_data = input_data.copy()
            output_data['story_results'] = []
            output_data['story_save_result'] = {
                'success': False,
                'message': "LLM未初始化，无法生成对话故事"
            }
            yield output_data
            return
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "对话故事生成",
                f"正在生成{story_count}个对话故事...",
                "progress"
            )
        
        # 分批处理
        total_batches = (story_count + batch_size - 1) // batch_size
        all_story_results = []
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "对话故事生成",
                f"将分{total_batches}批生成{story_count}个故事，每批{batch_size}个...",
                "progress"
            )
        
        # 创建CSV文件并写入表头
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = os.path.join(output_dir, f'talk_stories_{timestamp}.csv')
        
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['故事ID', '故事标题', '故事内容', '故事主题', '故事寓意', '生成时间']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        
        logger.info(f"已创建CSV文件: {csv_path}")
        
        # 分批异步处理
        import asyncio
        batch_tasks = []
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, story_count)
            batch_count = end_idx - start_idx
            
            # 为当前批次选择话题（如果有）
            batch_topics = []
            if topics:
                for i in range(start_idx, end_idx):
                    topic_idx = i % len(topics)
                    batch_topics.append(topics[topic_idx])
            
            # 创建批处理任务
            task = asyncio.create_task(
                self._process_batch(
                    batch_idx, batch_count, batch_topics, llm, csv_path, workflow_chat
                )
            )
            batch_tasks.append(task)
        
        # 等待所有批次完成并收集结果
        for completed_task in asyncio.as_completed(batch_tasks):
            batch_story_results = await completed_task
            all_story_results.extend(batch_story_results)
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "对话故事生成",
                f"✅ 已成功生成并保存 {len(all_story_results)} 个对话故事",
                "success"
            )
        
        # 输出结果
        output_data = input_data.copy()
        output_data['story_results'] = all_story_results
        output_data['story_save_result'] = {
            'success': True,
            'message': f"成功生成并保存{len(all_story_results)}个对话故事",
            'count': len(all_story_results),
            'file_path': csv_path
        }
        
        logger.info(f"✅ 对话故事生成完成，共 {len(all_story_results)} 个")
        yield output_data
    
    async def _process_batch(self, batch_idx: int, batch_count: int, batch_topics: List[str], 
                           llm, csv_path: str, workflow_chat=None) -> List[Dict]:
        """处理单个批次的故事生成"""
        logger.info(f"开始处理第{batch_idx+1}批，生成{batch_count}个对话故事")
        if workflow_chat:
            await workflow_chat.add_node_message(
                "对话故事生成",
                f"正在处理第{batch_idx+1}批，生成{batch_count}个对话故事...",
                "progress"
            )
        
        # 生成故事
        story_results = []
        for idx in range(batch_count):
            try:
                # 获取当前故事的话题（如果有）
                current_topic = ""
                if idx < len(batch_topics):
                    current_topic = batch_topics[idx]
                
                # 构建故事生成提示词
                system_prompt = f"""你是一个专业的对话故事创作助手，擅长生成高质量、情感丰富、适合分享的对话故事。

请根据提供的角色人设，创作一个精彩的短篇对话故事。
故事应专注于描述一个具体的有趣事件或情境，能够引发情感共鸣，但不包含任何私密或敏感的个人信息。

## 角色人设
{self.protagonist_data}  

{f'## 故事话题\n{current_topic}' if current_topic else ''}

请创作一个200-400字的高质量对话故事，要求：
1. 故事必须有清晰的开端、发展、高潮和结尾结构
2. 故事必须包含具体的事件和冲突，避免平淡叙述
3. 角色对话要自然生动，展现人物性格特点
4. 不要提及任何具体的地点名称，保持场景描述通用化
7. 故事可以包含幽默、温馨或感人的瞬间，增强情感连接
8. 角色行为要完全符合其人设，保持一致性
9. 故事最后应该有一个温暖、有意义或引人思考的结尾
10. 不要用"结束了一天的工作"作为引子
11. 故事中应包含一个小小的意外或转折，增加趣味性

输出格式要求：JSON格式，包含以下字段：
- title: 故事标题（简洁有吸引力）
- story: 故事内容
- theme: 故事主题或关键词（3-5个词语）

{
  "title": "口袋里的小惊喜",
  "story": "方知衡整理旧外套时，从口袋里摸出一张早已褪色的地铁票，背面歪歪扭扭地画着一只微笑的猫。他完全想不起这张票的来历，便随手贴在书桌前当装饰。几天后，同事路过时突然惊呼：\"这不就是我大学社团印的小猫吗？\" 原来那天社团义卖，他捐出了最后一张印有幸运猫的纪念票，恰巧被方知衡随手买下。两人对视一笑，仿佛时光在此刻完成了一次温柔的连结——那只微笑的猫，竟让多年后的人生路径在不经意间重叠。",
  "theme": "偶遇, 回忆, 小幸运",
}

请确保输出为严格的JSON格式，禁止输出任何其他内容。"""
                
                # 构建用户消息
                user_message = Message(
                    role=MessageRole.USER,
                    content=f"请创作一个精彩的短篇对话故事"
                )
                
                # 构建消息列表
                messages = [
                    Message(role=MessageRole.SYSTEM, content=system_prompt),
                    user_message
                ]
                
                # 调用LLM生成故事
                story_id = batch_idx * batch_count + idx + 1
                logger.info(f"开始生成第{story_id}个对话故事")
                
                # 使用文本模型
                original_model = llm.config.model_name
                text_model = os.getenv('DOUBAO_MODEL_PRO', 'ep-20250312153153-npj4s')
                llm.config.model_name = text_model
                
                logger.info(f"使用文本模型: {text_model}")
                
                # 调用LLM - 使用流式输出
                content = ""
                logger.info("开始流式生成对话故事...")
                async for chunk in llm.stream_generate(
                    messages,
                    temperature=0.85,  # 提高创意性
                    max_tokens=4096,
                    mode="normal"
                ):
                    # 打印每个chunk
                    chunk_text = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    print(chunk_text,end='',flush=True)
                    content += chunk_text
                    
                # 恢复原始模型名称
                llm.config.model_name = original_model
                
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
                    story_data = json.loads(json_str.strip())
                    # 确保包含必要字段
                    if 'story' not in story_data:
                        story_data["story"] = content
                    if 'title' not in story_data:
                        story_data["title"] = f"对话故事 #{story_id}"
                    if 'theme' not in story_data:
                        story_data["theme"] = "日常,对话,情感"
                except json.JSONDecodeError:
                    logger.warning(f"JSON解析失败，使用原始回复")
                    story_data = {
                        "story": content,
                        "title": f"对话故事 #{story_id}",
                        "theme": "日常,对话,情感"
                    }
                
                # 添加故事ID和生成时间
                story_data["story_id"] = story_id
                story_data["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                story_results.append(story_data)
                logger.info(f"对话故事生成成功: {story_data.get('title', '')}")
                
            except Exception as e:
                logger.error(f"对话故事生成失败: {e}")
                story_id = batch_idx * batch_count + idx + 1
                story_results.append({
                    "story_id": story_id,
                    "title": f"对话故事 #{story_id} (生成失败)",
                    "story": f"对话故事生成过程中出错: {str(e)}",
                    "theme": "错误",
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "error": str(e)
                })
        
        # 增量保存当前批次结果到CSV
        await self._append_to_csv(story_results, csv_path, workflow_chat)
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "对话故事生成",
                f"✅ 第{batch_idx+1}批：已生成并保存 {len(story_results)} 个对话故事",
                "streaming"
            )
        
        logger.info(f"✅ 第{batch_idx+1}批处理完成，生成 {len(story_results)} 个对话故事")
        return story_results
    
    async def _append_to_csv(self, story_results: List[Dict], csv_path: str, workflow_chat=None) -> Dict:
        """增量追加故事结果到CSV文件"""
        try:
            if not story_results:
                return {
                    'success': False,
                    'message': "没有故事结果需要保存"
                }
            
            # 追加模式写入CSV文件
            with open(csv_path, 'a', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['故事ID', '故事标题', '故事内容', '故事主题', '故事寓意', '生成时间']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # 写入故事结果
                for result in story_results:
                    writer.writerow({
                        '故事ID': result.get('story_id', ''),
                        '故事标题': result.get('title', ''),
                        '故事内容': result.get('story', ''),
                        '故事主题': result.get('theme', ''),
                        '故事寓意': result.get('moral', ''),
                        '生成时间': result.get('generated_at', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    })
            
            logger.info(f"✅ 增量保存：{len(story_results)}个对话故事已追加到 {os.path.basename(csv_path)}")
            
            return {
                'success': True,
                'message': f"成功追加{len(story_results)}个对话故事",
                'count': len(story_results),
                'file_path': csv_path
            }
            
        except Exception as e:
            logger.error(f"对话故事CSV增量保存失败: {e}")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "对话故事生成",
                    f"❌ 对话故事CSV增量保存失败: {str(e)}",
                    "error"
                )
            
            return {
                'success': False,
                'message': f"增量保存失败: {str(e)}",
                'error': str(e)
            }


# 测试代码
if __name__ == "__main__":
    import asyncio
    from llm.doubao import DoubaoLLM
    from core.types import LLMConfig
    
    async def test_talk_story_generation():
        # 初始化LLM
        # 创建LLM配置
        llm_config = LLMConfig(
            provider="doubao",
            model_name=os.getenv('DOUBAO_MODEL_PRO', 'ep-20250312153153-npj4s'),
            api_key=os.getenv('DOUBAO_API_KEY', 'b633a622-b5d0-4f16-a8a9-616239cf15d1'),
            api_base=os.getenv('DOUBAO_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3'),
            temperature=0.7,
            max_tokens=4096,
            streaming=True
        )
        # 使用配置初始化LLM
        llm = DoubaoLLM(config=llm_config)
        
        # 初始化对话故事生成节点
        node = TalkStoryGenerationNode()
        
        # 准备输入数据
        input_data = {
            'llm': llm,
            'story_count': 2,  # 生成2个故事用于测试
            'topics': ['一次有趣的误会', '一次温馨的日常对话'],
            'batch_size': 2
        }
        
        # 执行节点
        result = await node.execute(input_data)
        
        # 打印结果
        print(f"\n生成完成，结果保存在: {result.get('story_save_result', {}).get('file_path', '')}")
        
        # 打印第一个故事示例
        if result.get('story_results'):
            first_story = result['story_results'][0]
            print(f"\n示例故事: {first_story.get('title', '')}")
            print(f"主题: {first_story.get('theme', '')}")
            print(f"内容:\n{first_story.get('story', '')}")
    
    # 运行测试
    asyncio.run(test_talk_story_generation())