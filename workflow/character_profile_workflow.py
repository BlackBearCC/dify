"""
角色资料生成工作流
基于人物资料需求表格，结合向量知识库，生成详细的角色背景资料
"""

import json
import asyncio
import csv
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import aiofiles
import aiofiles.os

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from core.graph import StateGraph, CompiledStateGraph
from core.base import BaseNode
from llm.base import LLMFactory
from core.types import LLMConfig, TaskResult, Message, MessageRole, NodeType
from tools.knowledge_base_manager import GlobalKnowledgeBase
from tools.mcp_tools import MCPToolManager
from pydantic import BaseModel, Field

# Pydantic 数据模型
class ProfileItem(BaseModel):
    """资料条目模型"""
    item: str = Field(..., description="条目名称")
    content: str = Field("", description="条目内容")
    keywords: str = Field("", description="关键词")
    notes: str = Field("", description="备注")

class ProfileCategory(BaseModel):
    """资料类别模型"""
    name: str = Field(..., description="类别名称")
    items: List[ProfileItem] = Field(default_factory=list, description="条目列表")

class ProfileRequest(BaseModel):
    """角色资料生成请求模型"""
    name: str = Field(..., description="角色名称")
    info: str = Field(..., description="基础信息")
    categories: List[str] = Field(default_factory=list, description="选中的类别")
    collections: List[str] = Field(default_factory=list, description="选中的知识集合")

class SearchQuery(BaseModel):
    """搜索查询模型"""
    query: str = Field(..., description="查询文本")
    angle: str = Field(..., description="查询角度")
    description: str = Field("", description="查询描述")

class SearchExpansionResult(BaseModel):
    """搜索扩充结果模型"""
    queries: List[SearchQuery] = Field(default_factory=list, description="生成的查询列表")
    context: str = Field("", description="扩充的上下文信息")

class ProfileResult(BaseModel):
    """角色资料生成结果模型"""
    success: bool = Field(..., description="是否成功")
    name: str = Field("", description="角色名称")
    profile: Dict[str, Any] = Field(default_factory=dict, description="生成的资料")
    output_file: str = Field("", description="输出文件路径")
    error: str = Field("", description="错误信息")
    progress: str = Field("", description="进度信息")

# 配置日志 - 强制输出到标准输出
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
    force=True
)
logger = logging.getLogger(__name__)

# 自定义异常类
class ProfileGenerationError(Exception):
    """角色资料生成异常"""
    pass

class TemplateLoadError(ProfileGenerationError):
    """模板加载异常"""
    pass

class LLMGenerationError(ProfileGenerationError):
    """LLM生成异常"""
    pass

class FileSaveError(ProfileGenerationError):
    """文件保存异常"""
    pass

class SearchExpansionNode(BaseNode):
    """搜索扩充节点 - 根据当前处理内容生成多角度查询词"""
    
    def __init__(self, name: str = "search_expansion", llm_config: Optional[LLMConfig] = None):
        super().__init__(name=name, node_type=NodeType.CUSTOM, stream=True)
        self.llm_config = llm_config
        
        self.emit_info("init", "搜索扩充节点已初始化", {
            "has_llm_config": bool(llm_config)
        })
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行搜索扩充 - 调用流式方法获取最终结果"""
        final_result = None
        async for result in self.execute_stream(state):
            final_result = result
        return final_result or {"success": False, "error": "搜索扩充执行失败"}
    
    async def execute_stream(self, state: Dict[str, Any]):
        """流式执行搜索扩充节点"""
        try:
            request = state.get("request", {})
            current_item = state.get("current_item", {})
            llm = state.get("llm")
            
            name = request.get("name", "")
            info = request.get("info", "")
            category = current_item.get("category", "")
            item = current_item.get("item", {})
            
            # 处理item对象 - 可能是ProfileItem对象或字典
            if hasattr(item, 'item'):  # 如果是ProfileItem对象
                item_name = item.item
                item_content = getattr(item, 'content', '')
                item_keywords = getattr(item, 'keywords', '')
                item_notes = getattr(item, 'notes', '')
            else:  # 如果是字典
                item_name = item.get('item', '')
                item_content = item.get('content', '')
                item_keywords = item.get('keywords', '')
                item_notes = item.get('notes', '')
            
            self.emit_info("start", f"开始为条目 {item_name} 生成搜索查询", {
                "name": name,
                "category": category,
                "item": item_name,
                "has_llm": bool(llm)
            })
            
            if not name or not item_name:
                error_msg = "缺少必要参数：角色名称或条目信息"
                self.emit_info("error", error_msg, {"missing_name": not name, "missing_item": not item_name})
                yield {"success": False, "error": error_msg}
                return
            
            # 设置LLM
            if llm:
                self.set_llm(llm)
            
            if not self.llm:
                error_msg = "LLM未配置，无法生成搜索查询"
                self.emit_info("error", error_msg, {})
                yield {"success": False, "error": error_msg}
                return
            
            # 生成搜索查询 - 传递实际的ProfileItem对象
            queries = await self._generate_search_queries(name, info, category, item, llm)
            
            self.emit_info("complete", f"完成搜索查询生成", {
                "queries_count": len(queries),
                "queries": [q.dict() for q in queries]
            })
            
            yield {
                "success": True,
                "search_queries": queries,
                "current_item": current_item
            }
            
        except Exception as e:
            error_msg = f"搜索扩充失败: {str(e)}"
            self.emit_info("fatal_error", error_msg, {"error": str(e)})
            yield {"success": False, "error": error_msg}
    
    async def _generate_search_queries(self, 
                                     name: str, 
                                     info: str, 
                                     category: str, 
                                     item, 
                                     llm=None) -> List[SearchQuery]:
        """生成多角度搜索查询"""
        
        # 处理item参数 - 可能是ProfileItem对象或字典
        if hasattr(item, 'item'):  # 如果是ProfileItem对象
            item_name = item.item
            item_content = getattr(item, 'content', '')
            item_keywords = getattr(item, 'keywords', '')
            item_notes = getattr(item, 'notes', '')
        else:  # 如果是字典
            item_name = item.get('item', '') if isinstance(item, dict) else str(item)
            item_content = item.get('content', '') if isinstance(item, dict) else ''
            item_keywords = item.get('keywords', '') if isinstance(item, dict) else ''
            item_notes = item.get('notes', '') if isinstance(item, dict) else ''
        
        # 构建系统提示词
        system_prompt = """你是一个专业的信息检索专家，擅长根据人物资料需求生成精准的搜索查询词。

你的任务是：根据提供的角色信息和当前要生成的资料条目，生成3个不同角度的搜索查询词，用于在知识库中检索相关信息。

## 生成规则
1. 必须生成恰好3个不同角度的查询词
2. 每个查询词要从不同维度切入，确保覆盖面广
3. 查询词要具体、精准，避免过于宽泛
4. 优先考虑与角色背景、设定相关的内容
5. 确保查询词能够检索到有用的参考资料

## 三个角度说明
- 角度1：直接相关 - 与条目名称直接相关的查询
- 角度2：背景关联 - 与角色背景、设定相关的查询  
- 角度3：扩展延伸 - 与条目内容相关的扩展查询

## 输出格式
请以JSON格式输出，包含3个查询对象：
```json
{
  "queries": [
    {
      "query": "查询文本1",
      "angle": "直接相关",
      "description": "查询描述1"
    },
    {
      "query": "查询文本2", 
      "angle": "背景关联",
      "description": "查询描述2"
    },
    {
      "query": "查询文本3",
      "angle": "扩展延伸", 
      "description": "查询描述3"
    }
  ]
}
```"""
        
        # 构建用户提示词
        user_prompt = f"""请为以下角色资料条目生成3个不同角度的搜索查询词：

## 角色信息
- 角色名称：{name}
- 基础信息：{info}

## 当前条目
- 所属类别：{category}
- 条目名称：{item_name}"""

        if item_content:
            user_prompt += f"\n- 条目说明：{item_content}"
        
        if item_keywords:
            user_prompt += f"\n- 关键词：{item_keywords}"
        
        if item_notes:
            user_prompt += f"\n- 备注：{item_notes}"

        user_prompt += """

请根据以上信息，生成3个不同角度的搜索查询词，用于在知识库中检索相关参考资料。"""
        
        self.emit_info("llm_start", f"开始LLM生成搜索查询: {item_name}", {
            "category": category,
            "item": item_name,
            "system_prompt_length": len(system_prompt),
            "user_prompt_length": len(user_prompt)
        })
        
        # 构建消息列表
        messages = [
            Message(role=MessageRole.SYSTEM, content=system_prompt),
            Message(role=MessageRole.USER, content=user_prompt)
        ]
        
        # 调用LLM生成
        final_content = ""
        try:
            async for chunk_data in self.llm.stream_generate(
                messages, 
                mode="think",
                return_dict=True
            ):
                content_part = chunk_data.get("content", "")
                final_content += content_part
                
            # 发射LLM生成的原始内容用于调试
            self.emit_info("llm_raw_response", f"LLM原始响应: {item_name}", {
                "category": category,
                "item": item_name,
                "response_length": len(final_content),
                "response_preview": final_content[:200] + "..." if len(final_content) > 200 else final_content
            })
                
        except Exception as e:
            self.emit_info("llm_error", f"LLM调用失败: {str(e)}", {
                "category": category,
                "item": item_name,
                "error": str(e)
            })
            # 如果LLM调用失败，直接返回默认查询
            return self._generate_default_queries(name, info, category, item)
        
        # 解析LLM响应
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r'\{.*\}', final_content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                response_data = json.loads(json_str)
                
                queries = []
                for q_data in response_data.get("queries", []):
                    if not q_data.get("query") or not q_data.get("angle"):
                        continue  # 跳过无效查询
                    
                    query = SearchQuery(
                        query=q_data.get("query", "").strip(),
                        angle=q_data.get("angle", "").strip(),
                        description=q_data.get("description", "").strip()
                    )
                    queries.append(query)
                
                # 验证查询数量
                if len(queries) >= 3:
                    queries = queries[:3]  # 只取前3个
                    self.emit_info("llm_complete", f"搜索查询生成完成: {item_name}", {
                        "category": category,
                        "item": item_name,
                        "queries_count": len(queries),
                        "parsed_successfully": True
                    })
                    return queries
                else:
                    self.emit_info("llm_parse_warning", f"LLM生成的查询数量不足: {len(queries)}", {
                        "category": category,
                        "item": item_name,
                        "queries_count": len(queries),
                        "expected_count": 3
                    })
                    # 补充默认查询
                    default_queries = self._generate_default_queries(name, info, category, item)
                    queries.extend(default_queries[len(queries):])
                    return queries[:3]
            else:
                raise ValueError("未找到有效的JSON响应")
                
        except Exception as e:
            # 如果解析失败，生成默认查询
            self.emit_info("llm_parse_error", f"解析LLM响应失败，使用默认查询: {str(e)}", {
                "category": category,
                "item": item_name,
                "error": str(e),
                "response_length": len(final_content)
            })
            
            return self._generate_default_queries(name, info, category, item)
    
    def _generate_default_queries(self, 
                                name: str, 
                                info: str, 
                                category: str, 
                                item) -> List[SearchQuery]:
        """生成默认的搜索查询（备用方案）"""
        
        # 处理item参数 - 可能是ProfileItem对象或字典
        if hasattr(item, 'item'):  # 如果是ProfileItem对象
            item_name = item.item
            item_content = getattr(item, 'content', '')
            item_keywords = getattr(item, 'keywords', '')
            item_notes = getattr(item, 'notes', '')
        else:  # 如果是字典
            item_name = item.get('item', '') if isinstance(item, dict) else str(item)
            item_content = item.get('content', '') if isinstance(item, dict) else ''
            item_keywords = item.get('keywords', '') if isinstance(item, dict) else ''
            item_notes = item.get('notes', '') if isinstance(item, dict) else ''
        
        # 基础查询
        base_queries = [
            SearchQuery(
                query=f"{name} {item_name}",
                angle="直接相关",
                description=f"直接搜索{name}的{item_name}相关信息"
            ),
            SearchQuery(
                query=f"{name} {category}",
                angle="背景关联", 
                description=f"搜索{name}在{category}方面的背景信息"
            ),
            SearchQuery(
                query=f"{item_name} {category} 设定",
                angle="扩展延伸",
                description=f"搜索{item_name}相关的设定信息"
            )
        ]
        
        # 如果有关键词，使用关键词替换第三个查询
        if item_keywords:
            base_queries[2] = SearchQuery(
                query=f"{name} {item_keywords}",
                angle="扩展延伸",
                description=f"基于关键词{item_keywords}搜索相关信息"
            )
        
        # 如果有具体说明，使用说明替换第二个查询
        if item_content and len(item_content) < 50:  # 只有在说明较短时才使用
            base_queries[1] = SearchQuery(
                query=f"{name} {item_content}",
                angle="背景关联",
                description=f"基于条目说明搜索相关信息"
            )
        
        self.emit_info("default_queries_generated", f"生成默认查询: {item_name}", {
            "category": category,
            "item": item_name,
            "queries_count": len(base_queries),
            "fallback_reason": "LLM解析失败或生成数量不足"
        })
        
        return base_queries

class KnowledgeSearchNode(BaseNode):
    """知识库搜索节点 - 使用多个查询词搜索知识库"""
    
    def __init__(self, 
                 name: str = "knowledge_search",
                 kb: Optional[GlobalKnowledgeBase] = None):
        super().__init__(name=name, node_type=NodeType.CUSTOM, stream=True)
        self.kb = kb
        
        self.emit_info("init", "知识库搜索节点已初始化", {
            "has_kb": bool(kb)
        })
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行知识库搜索 - 调用流式方法获取最终结果"""
        final_result = None
        async for result in self.execute_stream(state):
            final_result = result
        return final_result or {"success": False, "error": "知识库搜索执行失败"}
    
    async def execute_stream(self, state: Dict[str, Any]):
        """流式执行知识库搜索节点"""
        try:
            search_queries = state.get("search_queries", [])
            current_item = state.get("current_item", {})
            request = state.get("request", {})
            collections = request.get("collections", [])
            
            self.emit_info("start", f"开始知识库搜索", {
                "queries_count": len(search_queries),
                "collections_count": len(collections),
                "current_item": current_item.get("item", {}).get("item", "")
            })
            
            if not self.kb:
                error_msg = "知识库未配置，无法进行搜索"
                self.emit_info("error", error_msg, {})
                yield {"success": False, "error": error_msg}
                return
            
            if not search_queries:
                error_msg = "没有搜索查询，无法进行搜索"
                self.emit_info("error", error_msg, {})
                yield {"success": False, "error": error_msg}
                return
            
            # 执行搜索
            search_results = await self._search_knowledge_base(search_queries, collections)
            
            self.emit_info("complete", f"知识库搜索完成", {
                "results_count": len(search_results),
                "collections_searched": len(collections)
            })
            
            yield {
                "success": True,
                "search_results": search_results,
                "current_item": current_item
            }
            
        except Exception as e:
            error_msg = f"知识库搜索失败: {str(e)}"
            self.emit_info("fatal_error", error_msg, {"error": str(e)})
            yield {"success": False, "error": error_msg}
    
    async def _search_knowledge_base(self, 
                                   search_queries: List[SearchQuery], 
                                   collections: List[str]) -> List[Dict[str, Any]]:
        """在知识库中搜索相关信息"""
        all_results = []
        
        for collection in collections:
            for query_obj in search_queries:
                try:
                    self.emit_info("search_start", f"搜索集合 {collection}，查询: {query_obj.query}", {
                        "collection": collection,
                        "query": query_obj.query,
                        "angle": query_obj.angle
                    })
                    
                    results = await self.kb.query_documents(
                        collection_name=collection, 
                        query_text=query_obj.query, 
                        n_results=3  # 每个查询返回3个结果
                    )
                    
                    for result in results:
                        all_results.append({
                            "collection": collection,
                            "query": query_obj.query,
                            "angle": query_obj.angle,
                            "content": result['document'],
                            "score": result.get('distance', 0)
                        })
                        
                    self.emit_info("search_result", f"从 {collection} 获得 {len(results)} 个结果", {
                        "collection": collection,
                        "query": query_obj.query,
                        "results_count": len(results)
                    })
                    
                except Exception as e:
                    self.emit_info("search_error", f"搜索 {collection} 失败: {str(e)}", {
                        "collection": collection,
                        "query": query_obj.query,
                        "error": str(e)
                    })
                    continue
        
        # 去重和排序（基于相似度分数）
        unique_results = []
        seen_contents = set()
        
        for result in all_results:
            content_hash = hash(result['content'][:100])  # 使用前100字符去重
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_results.append(result)
        
        # 按分数排序（如果有分数）
        unique_results.sort(key=lambda x: x.get('score', 0))
        
        return unique_results[:10]  # 最多返回10个结果

class ProfileGeneratorNode(BaseNode):
    """角色资料生成节点 - 仅支持流式调用"""
    
    def __init__(self, 
                 name: str = "profile_generator",
                 llm_config: Optional[LLMConfig] = None,
                 kb: Optional[GlobalKnowledgeBase] = None):
        super().__init__(name=name, node_type=NodeType.CUSTOM, stream=True)
        self.llm_config = llm_config
        self.kb = kb
        self.template = {}
        
        # 发射节点初始化信息
        self.emit_info("init", f"角色资料生成节点已初始化", {
            "has_kb": bool(kb),
            "has_llm_config": bool(llm_config)
        })
    
    async def _load_template(self):
        """加载人物资料需求模板"""
        if self.template:  # 如果已加载，直接返回
            return
            
        try:
            template_file = Path("workspace/input/主角人物资料需求表格.csv")
            if not await aiofiles.os.path.exists(template_file):
                raise TemplateLoadError(f"人物资料需求表格不存在: {template_file}")
            
            async with aiofiles.open(template_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                if not content.strip():
                    raise TemplateLoadError("模板文件为空")
                    
                reader = csv.DictReader(content.splitlines())
                for row in reader:
                    if not row.get('类别'):
                        logger.warning(f"跳过无效行: {row}")
                        continue
                        
                    category = row['类别']
                    if category not in self.template:
                        self.template[category] = []
                    
                    try:
                        item = ProfileItem(
                            item=row.get('条目', ''),
                            content=row.get('内容', ''),
                            keywords=row.get('关键词', ''),
                            notes=row.get('备注', '')
                        )
                        self.template[category].append(item)
                    except Exception as e:
                        logger.warning(f"跳过无效条目 {row}: {e}")
                        continue
            
            if not self.template:
                raise TemplateLoadError("模板文件中没有有效数据")
                
            logger.info(f"已加载人物资料模板，共{len(self.template)}个类别")
            
        except TemplateLoadError:
            raise
        except Exception as e:
            raise TemplateLoadError(f"加载人物资料模板失败: {e}") from e
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行角色资料生成 - 调用流式方法获取最终结果"""
        final_result = None
        async for result in self.execute_stream(state):
            final_result = result
        return final_result or {"success": False, "error": "执行失败"}
    
    async def execute_stream(self, state: Dict[str, Any]):
        """流式执行角色资料生成节点"""
        try:
            # 加载模板
            await self._load_template()
            
            request = state.get("request", {})
            llm = state.get("llm")
            
            name = request.get("name", "")
            info = request.get("info", "")
            categories = request.get("categories", [])
            collections = request.get("collections", [])
            
            self.emit_info("start", f"开始生成角色 {name} 的资料", {
                "name": name,
                "categories_count": len(categories),
                "collections_count": len(collections),
                "has_llm": bool(llm)
            })
            
            if not name or not info:
                error_msg = "缺少必要参数：角色名称和基础信息"
                self.emit_info("error", error_msg, {"missing": ["name" if not name else None, "info" if not info else None]})
                yield {"success": False, "error": error_msg}
                return
            
            # 生成角色资料 - 逐个条目生成
            profile = {}
            total_items = 0
            completed_items = 0
            
            # 先计算总条目数
            for category in categories:
                if category in self.template:
                    total_items += len(self.template[category])
            
            for category_idx, category in enumerate(categories):
                if category not in self.template:
                    self.emit_info("skip", f"跳过未知类别: {category}", {"category": category})
                    continue
                
                items = self.template[category]
                profile[category] = {}
                
                self.emit_info("category_start", f"开始生成类别: {category}", {
                    "category": category,
                    "items_count": len(items),
                    "progress": f"类别 {category_idx+1}/{len(categories)}"
                })
                
                # 逐个生成条目
                for item_idx, item in enumerate(items):
                    try:
                        self.emit_info("item_start", f"开始生成条目: {item.item}", {
                            "category": category,
                            "item": item.item,
                            "progress": f"条目 {completed_items+1}/{total_items}"
                        })
                        
                        # 使用新的搜索和生成流程
                        item_content = await self._generate_single_item_with_search(
                            name, info, category, item, collections, llm
                        )
                        
                        profile[category][item.item] = item_content
                        completed_items += 1
                        
                        self.emit_info("item_complete", f"完成条目: {item.item}", {
                            "category": category,
                            "item": item.item,
                            "content_length": len(item_content),
                            "progress": f"条目 {completed_items}/{total_items}"
                        })
                        
                        # 流式输出进度
                        yield {
                            "success": False,
                            "progress": f"已完成 {completed_items}/{total_items} 个条目",
                            "profile": profile.copy(),
                            "name": name,
                            "current_category": category,
                            "current_item": item.item,
                            "completed_items": completed_items,
                            "total_items": total_items
                        }
                        
                    except Exception as e:
                        error_msg = f"生成条目 {item.item} 失败: {str(e)}"
                        self.emit_info("item_error", error_msg, {
                            "category": category,
                            "item": item.item,
                            "error": str(e)
                        })
                        profile[category][item.item] = f"生成失败: {str(e)}"
                        completed_items += 1
                
                self.emit_info("category_complete", f"完成类别: {category}", {
                    "category": category,
                    "items_generated": len(profile[category]),
                    "progress": f"类别 {category_idx+1}/{len(categories)}"
                })
            
            # 保存结果
            self.emit_info("saving", "开始保存角色资料", {"profile_categories": len(profile)})
            try:
                output_file = await self._save_profile(name, profile)
                self.emit_info("save_success", f"角色资料保存成功: {output_file}", {"file": output_file})
            except Exception as e:
                self.emit_info("save_error", f"保存失败: {str(e)}", {"error": str(e)})
                output_file = ""
            
            # 发射完成信息
            self.emit_info("complete", "角色资料生成完成", {
                "categories_generated": len(profile),
                "items_generated": completed_items,
                "output_file": output_file,
                "success": True
            })
            
            yield {
                "success": True,
                "profile": profile,
                "output_file": output_file,
                "name": name
            }
            
        except Exception as e:
            error_msg = f"角色资料生成失败: {str(e)}"
            self.emit_info("fatal_error", error_msg, {"error": str(e)})
            yield {"success": False, "error": error_msg}
    
    async def _generate_single_item_with_search(self, 
                                              name: str, 
                                              info: str, 
                                              category: str, 
                                              item: ProfileItem, 
                                              collections: List[str], 
                                              llm=None) -> str:
        """使用新的搜索流程生成单个条目的内容"""
        
        # 设置LLM
        if llm:
            self.set_llm(llm)
        
        if not self.llm:
            raise LLMGenerationError("LLM未配置，无法生成角色资料")
        
        # 1. 搜索扩充阶段 - 生成查询词
        self.emit_info("search_expansion_start", f"开始搜索扩充: {item.item}", {
            "category": category,
            "item": item.item
        })
        
        search_expansion_node = SearchExpansionNode(llm_config=self.llm_config)
        search_expansion_node.set_llm(llm)
        
        search_state = {
            "request": {"name": name, "info": info, "collections": collections},
            "current_item": {"category": category, "item": item},
            "llm": llm
        }
        
        search_queries = []
        async for expansion_result in search_expansion_node.execute_stream(search_state):
            if expansion_result.get("success") and "search_queries" in expansion_result:
                search_queries = expansion_result["search_queries"]
                break
        
        if not search_queries:
            # 如果搜索扩充失败，使用原来的简单搜索方法
            self.emit_info("search_expansion_fallback", f"搜索扩充失败，使用简单搜索: {item.item}", {})
            context = await self._gather_item_context(name, info, category, item, collections)
        else:
            # 2. 知识库搜索阶段
            self.emit_info("knowledge_search_start", f"开始知识库搜索: {item.item}", {
                "queries_count": len(search_queries)
            })
            
            knowledge_search_node = KnowledgeSearchNode(kb=self.kb)
            
            search_state.update({
                "search_queries": search_queries
            })
            
            search_results = []
            async for search_result in knowledge_search_node.execute_stream(search_state):
                if search_result.get("success") and "search_results" in search_result:
                    search_results = search_result["search_results"]
                    break
            
            # 3. 整理搜索结果为上下文
            context = self._format_search_results(search_results)
        
        # 4. 生成内容
        return await self._generate_content_with_context(name, info, category, item, context, llm)
    
    def _format_search_results(self, search_results: List[Dict[str, Any]]) -> str:
        """将搜索结果格式化为上下文字符串"""
        if not search_results:
            return ""
        
        context_parts = []
        for result in search_results:
            context_part = f"""来源：{result['collection']}
查询角度：{result['angle']}
内容：{result['content']}"""
            context_parts.append(context_part)
        
        return "\n---\n".join(context_parts)
    
    async def _generate_content_with_context(self, 
                                           name: str, 
                                           info: str, 
                                           category: str, 
                                           item: ProfileItem, 
                                           context: str,
                                           llm=None) -> str:
        """基于上下文生成内容"""
        
        # 构建系统提示词（固定部分）
        system_prompt = """
        你是一位专业角色设定生成专家，负责创建详细、真实的角色资料。请根据提供的基础信息，生成符合以下标准的角色描述：

## 输出要求
- 格式为JSON，使用中文字段名
- 每个条目限制300字以内
- 内容为连贯流畅的描述性文本，不使用列表或表格

## 内容标准
1. 客观具体：提供精确数值和可视化细节，避免抽象修饰词，避免象征，暗示，代表这样的词语描述
2. 现实导向：摒弃游戏化、超自然或特殊设定，塑造符合现实世界的人物
3. 独立完整：不涉及或依赖其他角色（特别是女主角）的描述，不涉及异端组织，代号愚者的内容
4. 逻辑一致：确保各要素之间相互支持，形成统一的人物形象
5. 专业描述：使用专业文案式的客观描述，避免主观评价或分析

请基于提供的资料生成一个立体、可信的角色形象，使读者能清晰想象这个人物在现实中的样子和特质。
输出格式要求：
{
"条目名称": "条目内容"
} 
"""
        
        # 构建用户提示词（动态部分）
        user_prompt = f"""请为角色"{name}"生成"{item.item}"这个条目的详细内容。

## 角色基础信息
{info}

## 所属类别
{category}

## 条目要求
- 条目名称：{item.item}"""

        if item.content:
            user_prompt += f"\n- 条目说明：{item.content}"
        
        if item.keywords:
            user_prompt += f"\n- 关键词：{item.keywords}"
        
        if item.notes:
            user_prompt += f"\n- 备注：{item.notes}"

        if context:
            user_prompt += f"""

## 参考资料
{context}"""
        else:
            user_prompt += """

## 参考资料
无额外参考资料"""

        user_prompt += """

请开始生成该条目的详细内容："""
        
        self.emit_info("llm_start", f"开始LLM生成条目: {item.item}", {
            "category": category,
            "item": item.item,
            "system_prompt_length": len(system_prompt),
            "user_prompt_length": len(user_prompt),
            "context_length": len(context),
            "llm_type": type(self.llm).__name__
        })
        
        # 使用优化的提示词结构调用LLM
        final_content = ""
        think_content = ""
        
        # 构建消息列表
        from core.types import Message, MessageRole
        messages = [
            Message(role=MessageRole.SYSTEM, content=system_prompt),
            Message(role=MessageRole.USER, content=user_prompt)
        ]
        
        # 直接调用LLM的stream_generate方法
        chunk_count = 0
        async for chunk_data in self.llm.stream_generate(
            messages, 
            mode="think",
            return_dict=True
        ):
            chunk_count += 1
            
            think_part = chunk_data.get("think", "")
            content_part = chunk_data.get("content", "")
            
            think_content += think_part
            final_content += content_part
            
            # 发射LLM流式输出信息
            if content_part:
                self.emit_info("llm_streaming", f"LLM生成中: {item.item}", {
                    "category": category,
                    "item": item.item,
                    "chunk_count": chunk_count,
                    "current_content": content_part,
                    "accumulated_content": final_content,
                    "think_content": think_content,
                    "content_length": len(final_content)
                })
        
        self.emit_info("llm_complete", f"LLM生成完成: {item.item}", {
            "category": category,
            "item": item.item,
            "response_length": len(final_content)
        })
        
        # 清理并返回内容
        cleaned_content = final_content.strip()
        if not cleaned_content:
            raise LLMGenerationError(f"LLM未生成有效内容")
        
        return cleaned_content

    async def _gather_item_context(self, 
                                  name: str, 
                                  info: str, 
                                  category: str, 
                                  item: ProfileItem,
                                  collections: List[str]) -> str:
        """为单个条目收集相关上下文信息（原始简单方法，作为备用）"""
        if not self.kb:
            return ""
        
        # 构建更精确的查询文本
        queries = [
            f"{name} {item.item}",
            f"{name} {category} {item.item}",
            f"{item.item} {category}",
        ]
        
        # 如果有关键词，添加关键词查询
        if item.keywords:
            queries.append(f"{name} {item.keywords}")
            queries.append(f"{item.keywords} {category}")
        
        # 如果有具体说明，添加说明查询
        if item.content:
            queries.append(f"{name} {item.content}")
        
        context_list = []
        
        for collection in collections:
            for query in queries:
                try:
                    results = await self.kb.query_documents(
                        collection_name=collection, query_text=query, n_results=2
                    )
                    for result in results:
                        context_list.append(f"来源：{collection}\n内容：{result['document']}\n")
                except Exception:
                    continue
        
        return "\n---\n".join(context_list) if context_list else ""
    
    
    async def _save_profile(self, name: str, data: Dict[str, Any]) -> str:
        """保存生成的角色资料"""
        try:
            if not name:
                raise FileSaveError("角色名称不能为空")
            if not data:
                raise FileSaveError("资料数据不能为空")
                
            # 创建输出目录
            output_dir = Path("workspace/output")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 清理文件名中的非法字符
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"profile_{safe_name}_{timestamp}.json"
            output_file = output_dir / filename
            
            # 构建完整的输出数据
            try:
                output_data = {
                    'name': name,
                    'generated_at': datetime.now().isoformat(),
                    'data': data,
                    'metadata': {
                        'categories': len(data),
                        'fields': sum(len(cat_data) for cat_data in data.values() if isinstance(cat_data, dict))
                    }
                }
            except Exception as e:
                raise FileSaveError(f"构建输出数据失败: {e}") from e
            
            # 保存为JSON文件
            try:
                async with aiofiles.open(output_file, 'w', encoding='utf-8') as f:
                    json_content = json.dumps(output_data, ensure_ascii=False, indent=2)
                    await f.write(json_content)
            except Exception as e:
                raise FileSaveError(f"写入文件失败: {e}") from e
            
            logger.info(f"角色资料已保存: {output_file}")
            return str(output_file)
            
        except FileSaveError:
            raise
        except Exception as e:
            raise FileSaveError(f"保存角色资料失败: {e}") from e

class ProfileWorkflow:
    """角色资料生成工作流"""
    
    def __init__(self, llm_config: Optional[LLMConfig] = None, workspace_dir: str = "./workspace"):
        self.llm_config = llm_config
        self.workspace_dir = workspace_dir
        self.kb = GlobalKnowledgeBase(workspace_dir)
        self.mcp_tools = MCPToolManager()
        self.graph = None
        self.history_file = Path(workspace_dir) / "profile_history.json"
        
        # 加载可用的知识集合
        self.collections = []
        self._load_available_collections()
        
        # 加载历史记录
        self.history = []
    
    async def initialize(self):
        """异步初始化方法"""
        self.history = await self._load_history()
    
    def _load_available_collections(self):
        """加载可用的知识集合"""
        try:
            self.collections = self.kb.list_collections()
            logger.info(f"已加载{len(self.collections)}个知识集合")
        except Exception as e:
            logger.error(f"加载知识集合失败: {e}")
    
    async def _load_history(self) -> List[Dict[str, Any]]:
        """加载角色资料历史记录"""
        try:
            if await aiofiles.os.path.exists(self.history_file):
                async with aiofiles.open(self.history_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                    # 保持最多10条记录
                    return data[-10:] if len(data) > 10 else data
            return []
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}")
            return []
    
    async def _save_history(self, record: Dict[str, Any]):
        """保存角色资料历史记录"""
        try:
            # 添加新记录
            self.history.append(record)
            
            # 保持最多10条记录
            if len(self.history) > 10:
                self.history = self.history[-10:]
            
            # 确保目录存在
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存到文件
            async with aiofiles.open(self.history_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.history, ensure_ascii=False, indent=2))
                
            logger.info(f"已保存历史记录，当前共{len(self.history)}条")
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")
    
    def get_history_records(self) -> List[Dict[str, Any]]:
        """获取历史记录"""
        return self.history.copy()
    
    def get_history_by_name(self, name: str) -> List[Dict[str, Any]]:
        """根据角色名称获取历史记录"""
        return [record for record in self.history 
                if record.get('name', '').strip() == name.strip()]
    
    async def setup_graph(self) -> 'CompiledStateGraph':
        """设置工作流图"""
        if self.graph:
            print("[ProfileWorkflow] 使用已存在的工作流图")
            logger.info("使用已存在的工作流图")
            return self.graph
        
        print("[ProfileWorkflow] 开始创建工作流图...")
        logger.info("开始创建工作流图...")
        
        # 创建节点
        node = ProfileGeneratorNode(
            kb=self.kb,
            llm_config=self.llm_config
        )
        
        print(f"[ProfileWorkflow] 角色资料生成节点创建完成: {node}")
        logger.info(f"角色资料生成节点创建完成: {node}")
        
        # 创建图
        graph = StateGraph()
        graph.add_node("generate_profile", node)
        graph.set_entry_point("generate_profile")
        
        print("[ProfileWorkflow] StateGraph 节点和入口点设置完成")
        logger.info("StateGraph 节点和入口点设置完成")
        
        # 添加条件边来处理结束
        def end_condition(state: Dict[str, Any]) -> str:
            # 生成完成后结束
            print("[ProfileWorkflow] 执行结束条件判断")
            logger.info("执行结束条件判断")
            return "END"
        
        graph.add_conditional_edges("generate_profile", end_condition)
        
        print("[ProfileWorkflow] 条件边设置完成，开始编译图...")
        logger.info("条件边设置完成，开始编译图...")
        
        # 编译图
        self.graph = graph.compile()
        
        print(f"[ProfileWorkflow] 工作流图编译完成: {self.graph}")
        logger.info(f"工作流图编译完成: {self.graph}")
        
        return self.graph
    
    async def generate_character_profile(self, 
                                       character_name: str,
                                       basic_info: str,
                                       selected_categories: Optional[List[str]] = None,
                                       selected_collections: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        生成角色资料
        
        Args:
            character_name: 角色名称
            basic_info: 基础人设信息
            selected_categories: 选中的类别列表，如果为None则生成所有类别
            selected_collections: 选中的知识集合列表
            
        Returns:
            生成结果
        """
        try:
            print(f"[ProfileWorkflow] ===== 开始生成角色资料 =====")
            print(f"[ProfileWorkflow] 角色名称: {character_name}")
            print(f"[ProfileWorkflow] 基础信息长度: {len(basic_info) if basic_info else 0}")
            print(f"[ProfileWorkflow] 选中类别: {selected_categories}")
            print(f"[ProfileWorkflow] 选中知识集合: {selected_collections}")
            
            logger.info("===== 开始生成角色资料 =====")
            logger.info(f"角色名称: {character_name}")
            logger.info(f"基础信息长度: {len(basic_info) if basic_info else 0}")
            logger.info(f"选中类别: {selected_categories}")
            logger.info(f"选中知识集合: {selected_collections}")
            
            # 设置工作流图
            print("[ProfileWorkflow] 正在设置工作流图...")
            logger.info("正在设置工作流图...")
            compiled_graph = await self.setup_graph()
            
            # 创建LLM实例（如果配置可用）
            llm = None
            if self.llm_config:
                print(f"[ProfileWorkflow] 创建LLM实例，配置: {self.llm_config}")
                logger.info(f"创建LLM实例，配置: {self.llm_config}")
                llm = LLMFactory.create(self.llm_config)
                print(f"[ProfileWorkflow] LLM实例创建完成: {llm}")
                logger.info(f"LLM实例创建完成: {llm}")
            else:
                print("[ProfileWorkflow] 警告: 未提供LLM配置")
                logger.warning("未提供LLM配置")
            
            # 准备输入状态 - 使用新的request结构
            initial_state = {
                'request': {
                    'name': character_name,
                    'info': basic_info,
                    'categories': selected_categories or [],
                    'collections': selected_collections or []
                },
                'llm': llm  # 传递LLM对象到状态中
            }
            
            print(f"[ProfileWorkflow] 准备执行工作流，初始状态键: {list(initial_state.keys())}")
            logger.info(f"准备执行工作流，初始状态键: {list(initial_state.keys())}")
            
            # 执行工作流
            print("[ProfileWorkflow] 开始执行工作流图...")
            logger.info("开始执行工作流图...")
            result = await compiled_graph.ainvoke(initial_state)
            
            print(f"[ProfileWorkflow] 工作流执行完成，结果类型: {type(result)}")
            logger.info(f"工作流执行完成，结果类型: {type(result)}")
            
            return result
            
        except Exception as e:
            error_msg = f"角色资料生成失败: {str(e)}"
            print(f"[ProfileWorkflow] 错误: {error_msg}")
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    async def generate_character_profile_stream(self, 
                                              character_name: str,
                                              basic_info: str,
                                              selected_categories: Optional[List[str]] = None,
                                              selected_collections: Optional[List[str]] = None):
        """
        流式生成角色资料
        
        Args:
            character_name: 角色名称
            basic_info: 基础人设信息
            selected_categories: 选中的类别列表，如果为None则生成所有类别
            selected_collections: 选中的知识集合列表
            
        Yields:
            生成过程中的实时结果
        """
        try:
            # 设置工作流图
            compiled_graph = await self.setup_graph()
            
            # 创建LLM实例（如果配置可用）
            llm = None
            if self.llm_config:
                llm = LLMFactory.create(self.llm_config)
            
            # 准备输入状态
            initial_state = {
                'request': {
                    'name': character_name,
                    'info': basic_info,
                    'categories': selected_categories or [],
                    'collections': selected_collections or []
                },
                'llm': llm
            }
            
            # 执行工作流并流式返回结果
            async for result in compiled_graph.astream(initial_state):
                yield result
                
        except Exception as e:
            yield {
                'success': False,
                'error': str(e)
            }
    

    
    async def get_available_categories(self) -> List[str]:
        """获取可用的资料类别"""
        try:
            # 从人物资料需求表格中读取类别
            categories = set()
            template_file = Path("workspace/input/主角人物资料需求表格.csv")
            if await aiofiles.os.path.exists(template_file):
                import csv
                async with aiofiles.open(template_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    reader = csv.DictReader(content.splitlines())
                    for row in reader:
                        category = row.get('类别', '').strip()
                        if category:
                            categories.add(category)
            
            # 转换为列表并排序
            categories_list = sorted(list(categories))
            
            # 如果没有从CSV读取到，使用默认类别
            if not categories_list:
                categories_list = [
                    "基本信息", "外貌特征", "性格特征", "背景故事", 
                    "技能能力", "人际关系", "个人物品", "行为习惯"
                ]
            
            return categories_list
        except Exception as e:
            logger.error(f"获取资料类别失败: {e}")
            return ["基本信息", "外貌特征", "性格特征", "背景故事"]
    
    def get_available_collections(self) -> List[str]:
        """获取可用的知识集合"""
        try:
            collections = self.kb.list_collections()
            return [coll.name for coll in collections]
        except Exception as e:
            logger.error(f"获取知识集合失败: {e}")
            return []
    
    async def import_knowledge_from_file(self, 
                                       collection_name: str, 
                                       file_path: str,
                                       description: str = "") -> bool:
        """
        从文件导入知识到指定集合
        
        Args:
            collection_name: 集合名称
            file_path: 文件路径
            description: 集合描述
            
        Returns:
            是否导入成功
        """
        try:
            # 创建集合（如果不存在）
            await self.kb.create_collection(
                name=collection_name,
                description=description
            )
            
            # 导入文件
            success = await self.kb.import_from_text_file(
                collection_name=collection_name,
                file_path=file_path
            )
            
            if success:
                # 更新可用集合列表
                self._load_available_collections()
            
            return success
            
        except Exception as e:
            logger.error(f"导入知识库失败: {e}")
            return False

# 便捷函数
async def generate_character_profile(name: str,
                                   info: str,
                                   llm_config: Optional[LLMConfig] = None,
                                   categories: Optional[List[str]] = None,
                                   collections: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    便捷的角色资料生成函数
    
    Args:
        name: 角色名称
        info: 基础人设信息
        llm_config: LLM配置
        categories: 选中的类别列表
        collections: 选中的知识集合列表
        
    Returns:
        生成结果
    """
    workflow = ProfileWorkflow(llm_config)
    return await workflow.generate_character_profile(
        character_name=name,
        basic_info=info,
        selected_categories=categories,
        selected_collections=collections
    ) 