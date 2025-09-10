"""批量故事生成工作流 - 仅CSV保存版
基于方知衡世界观，按照指定类别批量生成故事文本。
"""

import asyncio
import os
import json
import logging
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.graph import StateGraph
from core.base import BaseNode
from core.types import Message, MessageRole

logger = logging.getLogger(__name__)


class StoryBatchWorkflow:
    """故事生成工作流（批量，CSV持久化）"""

    def __init__(self, llm=None):
        self.llm = llm
        self.graph: Optional[StateGraph] = None

        # 默认配置
        self.current_config: Dict[str, Any] = {
            "batch_size": 20,  # 每批生成故事数量
            "total_target": 200,  # 总故事数量
            "story_categories": [
                "日常", "校园", "科幻", "悬疑", "奇幻", "爱情"
            ],
            "csv_output": {
                "enabled": True,
                "output_dir": "workspace/story_output",
                "filename": "stories_batch_output.csv",
                "encoding": "utf-8-sig",
            },
        }

    # ---------------------------------------------------------------------
    # 图创建
    # ---------------------------------------------------------------------
    async def create_story_graph(self) -> StateGraph:
        """创建故事生成状态图"""
        self.graph = StateGraph(name="story_batch_generation")

        planning_node = StoryPlanningNode()
        generate_node = StoryGenerateNode()
        csv_save_node = StoryCSVSaveNode()

        self.graph.add_node("story_planning", planning_node)
        self.graph.add_node("story_generate", generate_node)
        self.graph.add_node("csv_save", csv_save_node)

        self.graph.add_edge("story_planning", "story_generate")
        self.graph.add_edge("story_generate", "csv_save")

        # 循环条件边：如果未完成，则继续生成下一批
        def loop_condition(state: Dict[str, Any]):
            if state.get("generation_complete", False):
                return "__end__"
            return "story_generate"

        self.graph.add_conditional_edges("csv_save", loop_condition)

        self.graph.set_entry_point("story_planning")
        return self.graph

    # ---------------------------------------------------------------------
    # 工作流执行
    # ---------------------------------------------------------------------
    async def execute(self, config: Optional[Dict[str, Any]] = None):
        """直接执行工作流并返回最终状态"""
        cfg = self.current_config.copy()
        if config:
            cfg.update(config)

        initial_state = {
            "config": cfg,
            "batch_size": cfg.get("batch_size"),
            "total_target": cfg.get("total_target"),
            "story_categories": cfg.get("story_categories"),
            "llm": self.llm,
            "current_batch_index": 0,
        }

        if not self.graph:
            await self.create_story_graph()
        compiled_graph = self.graph.compile()
        final_state = await compiled_graph.invoke(initial_state)
        return final_state

    async def execute_stream(self, config: Optional[Dict[str, Any]] = None):
        """流式执行，yield 每个执行事件"""
        cfg = self.current_config.copy()
        if config:
            cfg.update(config)
        state = {
            "config": cfg,
            "batch_size": cfg.get("batch_size"),
            "total_target": cfg.get("total_target"),
            "story_categories": cfg.get("story_categories"),
            "llm": self.llm,
            "current_batch_index": 0,
        }
        if not self.graph:
            await self.create_story_graph()
        compiled_graph = self.graph.compile()
        async for event in compiled_graph.stream(state):
            yield event


# -------------------------------------------------------------------------
# Nodes
# -------------------------------------------------------------------------
class StoryPlanningNode(BaseNode):
    """规划故事类别及批次"""

    def __init__(self):
        super().__init__(name="story_planning", stream=False)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        batch_size = input_data.get("batch_size", 20)
        total_target = input_data.get("total_target", 200)
        categories = input_data.get("story_categories", [])

        total_batches = (total_target + batch_size - 1) // batch_size

        plan = {
            "total_batches": total_batches,
            "batch_size": batch_size,
            "batch_categories": [],
        }

        # 简单循环分配类别
        for idx in range(total_batches):
            plan["batch_categories"].append(
                categories[idx % len(categories)]
            )

        out = input_data.copy()
        out["plan"] = plan
        out["current_batch_index"] = 0
        return out


class StoryGenerateNode(BaseNode):
    """生成故事文本"""

    def __init__(self):
        super().__init__(name="story_generate", stream=False)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        llm = input_data.get("llm")
        plan = input_data.get("plan", {})
        current_index = input_data.get("current_batch_index", 0)
        batch_size = input_data.get("batch_size", 20)

        if current_index >= plan.get("total_batches", 0):
            # 所有批次完成
            out = input_data.copy()
            out["generation_complete"] = True
            return out

        category = plan.get("batch_categories", [])[current_index]

        prompt = self._build_prompt(batch_size, category)

        stories: List[Dict[str, str]] = []

        if llm:
            try:
                messages = [Message(role=MessageRole.USER, content=prompt)]
                content = ""
                async for chunk in llm.stream_generate(messages, return_dict=True):
                    content += chunk.get("content", "")
                json_str = self._extract_json_from_content(content)
                from parsers.json_parser import JSONParser
                parser = JSONParser()
                parsed = parser.parse(json_str)
                stories = parsed.get("stories", []) if parsed else []
            except Exception as e:
                logger.error(f"LLM生成失败: {e}")
        # 如果llm不可用或生成失败，生成占位数据
        if not stories:
            stories = [
                {
                    "标题": f"示例故事_{current_index}_{i}",
                    "内容": f"这是类别{category}的示例故事正文_{i}。"
                }
                for i in range(batch_size)
            ]

        out = input_data.copy()
        out["generated_stories"] = stories
        out["current_batch_index"] = current_index + 1
        return out

    @staticmethod
    def _build_prompt(batch_size: int, category: str) -> str:
        return f"""
请创作 {batch_size} 篇类别为"{category}"的原创短篇故事，每篇 200-400 字，并提供一个简洁标题。

输出格式（严格遵守）：
```json
{{
  "stories": [
    {{ "标题": "...", "内容": "..." }},
    ... 共 {batch_size} 项 ...
  ]
}}
```"""

    @staticmethod
    def _extract_json_from_content(content: str) -> str:
        import re
        pattern = r"```json\s*(.*?)\s*```"
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()
        # Fallback
        pattern2 = r"\{.*\}"
        matches2 = re.findall(pattern2, content, re.DOTALL)
        return matches2[0].strip() if matches2 else content.strip()


class StoryCSVSaveNode(BaseNode):
    """保存故事到CSV（追加模式）"""

    def __init__(self):
        super().__init__(name="csv_save", stream=False)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        stories: List[Dict[str, str]] = input_data.get("generated_stories", [])
        cfg = input_data.get("config", {})
        batch_idx = input_data.get("current_batch_index", 1)

        if not stories:
            return input_data  # 无数据可保存

        csv_cfg = cfg.get("csv_output", {})
        out_dir = csv_cfg.get("output_dir", "workspace/story_output")
        filename = csv_cfg.get("filename", "stories_batch_output.csv")
        encoding = csv_cfg.get("encoding", "utf-8-sig")

        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, filename)

        write_header = not os.path.exists(path)
        import csv
        with open(path, "a", newline="", encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=["批次", "标题", "内容", "类别", "生成时间"])
            if write_header:
                writer.writeheader()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for st in stories:
                writer.writerow({
                    "批次": f"第{batch_idx}批",
                    "标题": st.get("标题", ""),
                    "内容": st.get("内容", ""),
                    "类别": cfg.get("story_categories", [])[ (batch_idx -1) % len(cfg.get("story_categories", [])) ],
                    "生成时间": timestamp,
                })

        logger.info(f"✅ 已保存 {len(stories)} 篇故事到 {path}")

        out = input_data.copy()
        out["csv_path"] = path
        return out


# -------------------------------------------------------------------------
# 测试运行
# -------------------------------------------------------------------------
if __name__ == "__main__":
    async def _test():
        print("🚀 开始批量故事生成测试 ...")
        
        workflow = StoryBatchWorkflow(llm=None)  # 无LLM，用示例数据
        result = await workflow.execute({
            "total_target": 60,
            "batch_size": 15,
            "story_categories": ["日常", "奇幻", "悬疑"],
        })
        print("🎉 完成! 最终状态键:", list(result.keys()))
        print("CSV路径:", result.get("csv_path"))
    asyncio.run(_test()) 