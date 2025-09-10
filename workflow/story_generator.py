"""故事生成器 - 基于图片描述结果生成故事
读取图片识别结果，结合角色人设生成故事，并保存为带故事后缀的CSV文件
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

class StoryGenerationNode(BaseNode):
    """故事生成节点 - 读取图片描述结果，结合角色人设生成故事"""
    
    def __init__(self):
        super().__init__(name="story_generation", stream=True)
        self.protagonist_data = ""
        self.locations_data = {}
        self._load_protagonist_data()
        self._load_locations_data()
    
    def _load_protagonist_data(self):
        """加载主角方知衡的详细人设"""
        try:
            protagonist_path = os.path.join(os.path.dirname(__file__), '../../config/基础人设_方知衡100.txt')
            if os.path.exists(protagonist_path):
                with open(protagonist_path, 'r', encoding='utf-8') as f:
                    self.protagonist_data = f.read()
                    logger.info(f"成功加载主角人设，内容长度: {len(self.protagonist_data)} 字符")
            else:
                logger.warning("主角人设文件不存在")
                
        except Exception as e:
            logger.error(f"加载主角人设失败: {e}")
            
    def _load_locations_data(self):
        """加载云枢市地点数据"""
        try:
            locations_path = os.path.join(os.path.dirname(__file__), '../../config/yunhub_locations.json')
            if os.path.exists(locations_path):
                with open(locations_path, 'r', encoding='utf-8') as f:
                    self.locations_data = json.load(f)
                    districts_count = len(self.locations_data.get("districts", {}))
                    logger.info(f"成功加载云枢市地点数据，包含 {districts_count} 个区域")
            else:
                logger.warning("云枢市地点数据文件不存在")
                
        except Exception as e:
            logger.error(f"加载云枢市地点数据失败: {e}")
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行故事生成节点"""
        final_result = None
        async for result in self.execute_stream(input_data):
            final_result = result
        return final_result or input_data
    
    async def execute_stream(self, input_data: Dict[str, Any]):
        """流式执行故事生成节点 - 支持批量处理和增量保存"""
        print("📝 开始生成故事...")
        
        workflow_chat = input_data.get('workflow_chat')
        llm = input_data.get('llm')
        recognition_results = input_data.get('recognition_results', [])
        csv_save_result = input_data.get('csv_save_result', {})
        csv_file_path = csv_save_result.get('file_path', '')
        batch_size = input_data.get('batch_size', 1)  # 默认每批处理5个图片
        
        if not recognition_results:
            # 没有识别结果，无法生成故事
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "故事生成",
                    "⚠️ 没有图片识别结果，无法生成故事",
                    "warning"
                )
            
            output_data = input_data.copy()
            output_data['story_results'] = []
            output_data['story_save_result'] = {
                'success': False,
                'message': "没有图片识别结果，无法生成故事"
            }
            yield output_data
            return
        
        if not llm:
            # LLM未初始化，无法生成故事
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "故事生成",
                    "⚠️ LLM未初始化，无法生成故事",
                    "warning"
                )
            
            output_data = input_data.copy()
            output_data['story_results'] = []
            output_data['story_save_result'] = {
                'success': False,
                'message': "LLM未初始化，无法生成故事"
            }
            yield output_data
            return
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "故事生成",
                f"正在为{len(recognition_results)}张图片生成故事...",
                "progress"
            )
        
        # 分批处理图片
        total_results = len(recognition_results)
        total_batches = (total_results + batch_size - 1) // batch_size
        all_story_results = []
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "故事生成",
                f"将分{total_batches}批处理{total_results}张图片，每批{batch_size}张...",
                "progress"
            )
        
        # 分批异步处理
        import asyncio
        batch_tasks = []
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_results)
            batch_results = recognition_results[start_idx:end_idx]
            
            # 创建批处理任务
            task = asyncio.create_task(
                self._process_batch(
                    batch_idx, batch_results, llm, csv_file_path, workflow_chat
                )
            )
            batch_tasks.append(task)
        
        # 等待所有批次完成并收集结果
        for completed_task in asyncio.as_completed(batch_tasks):
            batch_story_results = await completed_task
            all_story_results.extend(batch_story_results)
        
        # 批量更新原始CSV文件中的关键词和故事内容
        update_result = await self._update_csv_with_stories(all_story_results, csv_file_path, workflow_chat)
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "故事生成",
                f"✅ 已成功生成并保存 {len(all_story_results)} 个故事",
                "success"
            )
        
        # 输出结果
        output_data = input_data.copy()
        output_data['story_results'] = all_story_results
        output_data['story_save_result'] = update_result
        
        logger.info(f"✅ 故事生成完成，共 {len(all_story_results)} 个")
        yield output_data
    
    async def _process_batch(self, batch_idx: int, batch_results: List[Dict], 
                           llm, csv_path: str, workflow_chat=None) -> List[Dict]:
        """处理单个批次的图片"""
        logger.info(f"开始处理第{batch_idx+1}批，包含{len(batch_results)}张图片")
        if workflow_chat:
            await workflow_chat.add_node_message(
                "故事生成",
                f"正在处理第{batch_idx+1}批，{len(batch_results)}张图片...",
                "progress"
            )
        
        # 生成故事
        story_results = []
        for idx, result in enumerate(batch_results):
            try:
                # 不再需要准备云枢市地点信息，因为我们不希望故事中包含具体地点
                
                # 构建故事生成提示词
                system_prompt = """你是一个专业的故事创作助手，擅长根据图片描述和角色人设生成有深度、情节丰富的故事。

请根据提供的图片描述和角色人设，创作一个短篇故事。故事应该围绕主角方知衡展开，并与图片描述中的场景、元素自然融合。
注意这个故事是像亲密的人分享使用的，他应该能触发甜蜜美好的话题

## 角色人设
""" + self.protagonist_data + f"""

## 图片描述
标题：{result.get('title', '')}
详细描述：{result.get('description', '')}
（这是角色拍下的照片的描述，但不需要交代相机或手机拍摄的过程）

请创作一个100-150字的短篇故事，要求：
1. 故事必须以方知衡为主角，并与图片描述中的场景和元素自然融合
2. 故事必须包含具体的事件和冲突，避免空洞的描述
6. 不要提及任何具体的地点名称，保持场景描述通用化
7. 有点像游戏支线剧情，情节要有意外性和转折
9. 角色行为要符合其人设，保持一致性
10. 故事最后不要改变任何人物状态，比如养动物
11. 不要用xxx结束了一天的工作作为引子

输出格式要求：JSON格式，包含以下字段：
- story: 故事内容（包含具体对话、内心活动和环境描写）
- elements: 故事中出现的具体物品、人物、动物实体名词，5-20个（数组，如：猫、树、车、人、花、建筑等，不要概念、形容词、颜色）

请确保输出为严格的JSON格式，禁止输出任何其他内容。
示例：
{{
  "story": "方知衡走在街道上...",
  "elements": [ "街道", "猫", "树", "车"]
}}"""
                
                # 构建用户消息
                user_message = Message(
                    role=MessageRole.USER,
                    content=f"请根据以下图片描述和角色人设，创作一个短篇故事：\n\n图片标题：{result.get('title', '')}\n图片描述：{result.get('description', '')}\n主要元素：{', '.join(result.get('elements', []))}\n\n请确保故事以方知衡为主角，不要提及具体地点名称，并与图片描述中的场景、元素自然融合。"
                )
                
                # 构建消息列表
                messages = [
                    Message(role=MessageRole.SYSTEM, content=system_prompt),
                    user_message
                ]
                
                # 调用LLM生成故事
                logger.info(f"开始为图片生成故事: {result.get('image_name', '')}")
                
                # 使用原始模型（文本模型）
                original_model = llm.config.model_name
                text_model = os.getenv('DOUBAO_MODEL_PRO', 'ep-20250312153153-npj4s')
                llm.config.model_name = text_model
                
                logger.info(f"使用文本模型: {text_model}")
                
                # 调用LLM - 使用流式输出
                content = ""
                logger.info("开始流式生成故事...")
                async for chunk in llm.stream_generate(
                    messages,
                    temperature=0.8,  # 稍微提高创意性
                    max_tokens=4096,
                    mode="normal"
                ):
                    # 打印每个chunk
                    chunk_text = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    print(chunk_text,end='',flush=True)
                    content += chunk_text
                    
                # 恢复原始模型名称
                llm.config.model_name = original_model
                
                # 解析结果
                # content已经在流式生成过程中累积
                
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
                        story_data = {"story": content}
                    if 'elements' not in story_data:
                        story_data['elements'] = []
                except json.JSONDecodeError:
                    logger.warning(f"JSON解析失败，使用原始回复")
                    story_data = {"story": content, "elements": []}
                
                # 添加图片信息和原始描述
                story_data["image_name"] = result.get("image_name", "")
                story_data["image_path"] = result.get("image_path", "")
                story_data["original_title"] = result.get("title", "")
                story_data["original_description"] = result.get("description", "")
                story_data["original_elements"] = result.get("elements", [])
                
                story_results.append(story_data)
                logger.info(f"故事生成成功: {result.get('image_name', '')}")
                
            except Exception as e:
                logger.error(f"故事生成失败: {e}")
                story_results.append({
                    "image_name": result.get("image_name", "未知图片"),
                    "image_path": result.get("image_path", "未知路径"),
                    "original_title": result.get("title", ""),
                    "original_description": result.get("description", ""),
                    "original_elements": result.get("elements", []),
                    "title": f"方知衡与{result.get('title', '未知场景')}",
                    "story": f"故事生成过程中出错: {str(e)}",
                    "theme": "错误",
                    "elements": [],
                    "error": str(e)
                })
        
        # 注释掉批次保存，改为在主方法中统一更新
        # await self._append_to_csv(story_results, csv_path, workflow_chat)
        
        if workflow_chat:
            await workflow_chat.add_node_message(
                "故事生成",
                f"✅ 第{batch_idx+1}批：已生成并保存 {len(story_results)} 个故事",
                "streaming"
            )
        
        logger.info(f"✅ 第{batch_idx+1}批处理完成，生成 {len(story_results)} 个故事")
        return story_results
    
    async def _prepare_csv_file(self, original_csv_path: str) -> str:
        """准备CSV文件并写入表头"""
        # 生成带故事后缀的CSV文件名
        if not original_csv_path or not os.path.exists(original_csv_path):
            # 如果原始CSV不存在，创建一个新的
            output_dir = 'workspace/image_recognition_output'
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            story_csv_path = os.path.join(output_dir, f'image_recognition_with_story_{timestamp}.csv')
        else:
            # 基于原始CSV创建带故事后缀的新文件
            base_name, ext = os.path.splitext(original_csv_path)
            story_csv_path = f"{base_name}_with_story{ext}"
        
        # 创建文件并写入表头
        with open(story_csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['图片名称', '图片路径', '原始标题', '原始描述', '原始元素', '故事内容']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        
        logger.info(f"已创建CSV文件: {story_csv_path}")
        return story_csv_path
    
    async def _update_csv_with_stories(self, story_results: List[Dict], csv_path: str, workflow_chat=None) -> Dict:
        """更新原始CSV文件，填充关键词和故事内容"""
        try:
            if not story_results:
                return {
                    'success': False,
                    'message': "没有故事结果需要保存"
                }
            
            # 读取原始CSV文件
            rows = []
            fieldnames = []
            
            if os.path.exists(csv_path):
                with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    rows = list(reader)
            else:
                # 如果文件不存在，创建默认结构
                fieldnames = ['序号ID', '图片名称', '图片路径', '图片标题', '图片描述', '关键词', '故事内容']
            
            # 创建故事结果的索引，以图片路径为键
            story_dict = {}
            for story in story_results:
                image_path = story.get('image_path', '')
                if image_path:
                    story_dict[image_path] = story
            
            # 更新行数据
            for row in rows:
                image_path = row.get('图片路径', '')
                if image_path in story_dict:
                    story_data = story_dict[image_path]
                    # 更新关键词字段（使用故事中的实体名词）
                    elements = story_data.get('elements', [])
                    if isinstance(elements, list):
                        row['关键词'] = ' '.join(elements)
                    else:
                        row['关键词'] = elements
                    
                    # 更新故事内容
                    row['故事内容'] = story_data.get('story', '')
            
            # 写回CSV文件
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            logger.info(f"✅ 已更新CSV文件：{len(story_results)}个故事的关键词和内容已添加到 {os.path.basename(csv_path)}")
            
            return {
                'success': True,
                'message': f"成功更新{len(story_results)}条记录的故事和关键词",
                'count': len(story_results),
                'file_path': csv_path
            }
            
        except Exception as e:
            logger.error(f"CSV文件更新失败: {e}")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "故事生成",
                    f"❌ CSV文件更新失败: {str(e)}",
                    "error"
                )
            
            return {
                'success': False,
                'message': f"更新失败: {str(e)}",
                'error': str(e)
            }
    
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
                fieldnames = ['图片名称', '图片路径', '图片标题', '图片描述', '关键词', '故事内容']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # 写入故事结果
                for result in story_results:
                    writer.writerow({
                        '图片名称': result.get('image_name', ''),
                        '图片路径': result.get('image_path', ''),
                        '图片标题': result.get('original_title', ''),
                        '图片描述': result.get('original_description', ''),
                        '关键词': ','.join(result.get('original_elements', [])) if isinstance(result.get('original_elements', []), list) else result.get('original_elements', ''),
                        '故事内容': result.get('story', '')
                    })
            
            logger.info(f"✅ 增量保存：{len(story_results)}个故事已追加到 {os.path.basename(csv_path)}")
            
            return {
                'success': True,
                'message': f"成功追加{len(story_results)}个故事",
                'count': len(story_results),
                'file_path': csv_path
            }
            
        except Exception as e:
            logger.error(f"故事CSV增量保存失败: {e}")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "故事生成",
                    f"❌ 故事CSV增量保存失败: {str(e)}",
                    "error"
                )
            
            return {
                'success': False,
                'message': f"增量保存失败: {str(e)}",
                'error': str(e)
            }
    
    async def _save_to_csv(self, story_results: List[Dict], original_csv_path: str, workflow_chat=None) -> Dict:
        """保存故事结果到CSV文件（旧方法，保留向后兼容）"""
        """保存故事结果到CSV文件"""
        try:
            if not story_results:
                return {
                    'success': False,
                    'message': "没有故事结果需要保存"
                }
            
            # 生成带故事后缀的CSV文件名
            if not original_csv_path or not os.path.exists(original_csv_path):
                # 如果原始CSV不存在，创建一个新的
                output_dir = 'workspace/image_recognition_output'
                os.makedirs(output_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                story_csv_path = os.path.join(output_dir, f'image_recognition_with_story_{timestamp}.csv')
            else:
                # 基于原始CSV创建带故事后缀的新文件
                base_name, ext = os.path.splitext(original_csv_path)
                story_csv_path = f"{base_name}_with_story{ext}"
            
            # 写入CSV文件
            with open(story_csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = ['图片名称', '图片路径', '标题', '图片描述', '图片元素', '故事内容']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                # 写入故事结果
                for result in story_results:
                    writer.writerow({
                        '图片名称': result.get('image_name', ''),
                        '图片路径': result.get('image_path', ''),
                        '原始标题': result.get('original_title', ''),
                        '原始描述': result.get('original_description', ''),
                        '原始元素': ','.join(result.get('original_elements', [])) if isinstance(result.get('original_elements'), list) else result.get('original_elements', ''),
                        '故事内容': result.get('story', '')
                    })
            
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "故事生成",
                    f"✅ {len(story_results)}个故事已保存到CSV文件: {os.path.basename(story_csv_path)}",
                    "success"
                )
            
            logger.info(f"✅ 故事CSV保存完成：{len(story_results)}个故事保存到 {story_csv_path}")
            
            return {
                'success': True,
                'message': f"成功保存{len(story_results)}个故事",
                'count': len(story_results),
                'file_path': story_csv_path
            }
            
        except Exception as e:
            logger.error(f"故事CSV保存失败: {e}")
            if workflow_chat:
                await workflow_chat.add_node_message(
                    "故事生成",
                    f"❌ 故事CSV保存失败: {str(e)}",
                    "error"
                )
            
            return {
                'success': False,
                'message': f"保存失败: {str(e)}",
                'error': str(e)
            }

    @staticmethod
    def read_csv_file(csv_file_path: str) -> List[Dict]:
        """读取CSV文件中的图片识别结果"""
        recognition_results = []
        try:
            if not os.path.exists(csv_file_path):
                print(f"❌ CSV文件不存在: {csv_file_path}")
                return []
            
            with open(csv_file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 将CSV行转换为识别结果格式
                    elements = row.get('主要元素', '').split(',') if row.get('主要元素') else []
                    recognition_result = {
                        'image_name': row.get('图片名称', ''),
                        'image_path': row.get('图片路径', ''),
                        'title': row.get('标题', ''),
                        'description': row.get('详细描述', ''),
                        'elements': elements
                    }
                    recognition_results.append(recognition_result)
            
            print(f"✅ 成功读取CSV文件，共{len(recognition_results)}条图片识别结果")
            return recognition_results
        except Exception as e:
            print(f"❌ 读取CSV文件失败: {e}")
            return []


# 测试代码
if __name__ == "__main__":
    print("故事生成器模块 - 直接运行测试")
    
    # 创建节点实例
    node = StoryGenerationNode()
    print(f"成功加载主角人设，长度: {len(node.protagonist_data)} 字符")
    
    # 检查是否有命令行参数指定CSV文件
    if len(sys.argv) > 1:
        csv_file_path = sys.argv[1]
    else:
        # 默认处理最新的图片识别结果CSV文件
        csv_file_path = "workspace/image_recognition_output/image_recognition_20250704_112047.csv"
    
    # 检查是否指定了批处理大小
    batch_size = 5  # 默认每批5个
    if len(sys.argv) > 2:
        try:
            batch_size = int(sys.argv[2])
        except ValueError:
            print(f"批处理大小参数无效，使用默认值: {batch_size}")
    
    # 读取CSV文件
    recognition_results = StoryGenerationNode.read_csv_file(csv_file_path)
    
    if recognition_results:
        print(f"开始处理{len(recognition_results)}条图片识别结果...")
        
        # 导入必要的模块
        import asyncio
        from llm.doubao import DoubaoLLM
        
        # 创建异步运行函数
        async def run_story_generation():
            # 初始化LLM
            from core.types import LLMConfig
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
            
            # 准备输入数据
            input_data = {
                'llm': llm,
                'recognition_results': recognition_results,
                'csv_save_result': {'file_path': csv_file_path},
                'batch_size': batch_size  # 设置批处理大小
            }
            
            # 执行故事生成
            async for result in node.execute_stream(input_data):
                # 处理完成
                story_results = result.get('story_results', [])
                story_save_result = result.get('story_save_result', {})
                
                if story_save_result.get('success'):
                    print(f"✅ 故事生成完成，结果已保存到: {story_save_result.get('file_path')}")
                else:
                    print(f"❌ 故事生成失败: {story_save_result.get('message')}")
        
        # 运行异步函数
        asyncio.run(run_story_generation())
    else:
        print("没有找到图片识别结果，无法生成故事")
    
    print("测试完成")