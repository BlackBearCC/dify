"""
话题生成器
基于AI角色人设生成不重复的话题内容
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
import sys
import os
import re

# 添加core模块到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

from core.llm_client import create_doubao_client, create_claude_client, create_deepseek_client, LLMProvider
from config import LLM_CONFIG, DEFAULT_LLM_PROVIDER, GENERATION_CONFIG, TOPIC_CATEGORIES


class JSONExtractor:
    """JSON提取器 - 通用的JSON解析工具"""
    
    @staticmethod
    def extract_json_array(text: str) -> list:
        """提取JSON数组"""
        json_match = re.search(r'\[.*?\]', text, re.DOTALL)
        if not json_match:
            raise ValueError("未找到JSON数组格式")
        
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON数组解析失败: {e}")
    
    @staticmethod
    def extract_json_object(text: str) -> dict:
        """提取JSON对象"""
        json_match = re.search(r'\{.*?\}', text, re.DOTALL)
        if not json_match:
            raise ValueError("未找到JSON对象格式")
        
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON对象解析失败: {e}")
    
    @staticmethod
    def extract_field_from_json(text: str, field: str):
        """从JSON对象中提取指定字段"""
        json_obj = JSONExtractor.extract_json_object(text)
        if field not in json_obj:
            raise KeyError(f"JSON中未找到字段: {field}")
        return json_obj[field]


class TopicGenerator:
    """话题生成器"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent.parent / "data" / "topics.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self.personas_path = Path(__file__).parent.parent / "personas"
        self.personas_path.mkdir(exist_ok=True)
        self.prompts_path = Path(__file__).parent.parent / "prompts"
        self.prompts_path.mkdir(exist_ok=True)
        self.init_db()
        self.init_llm_client()
        
    def init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    keywords TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
    def init_llm_client(self):
        """初始化LLM客户端"""
        provider = DEFAULT_LLM_PROVIDER
        config = LLM_CONFIG[provider]
        
        # 根据配置创建对应的客户端
        if provider == "doubao":
            self.llm_client = create_doubao_client(
                api_key=config["api_key"],
                model=config["model"],
                base_url=config["base_url"]
            )
        elif provider == "claude":
            self.llm_client = create_claude_client(
                api_key=config["api_key"],
                model=config["model"],
                base_url=config["base_url"]
            )
        elif provider == "deepseek":
            self.llm_client = create_deepseek_client(
                api_key=config["api_key"],
                model=config["model"],
                base_url=config["base_url"]
            )
        else:
            raise ValueError(f"不支持的LLM提供商: {provider}")
            
        print(f"🤖 已初始化LLM客户端: {provider} - {config['model']}")
        
    def load_prompt_template(self, template_name: str) -> str:
        """加载提示词模板"""
        template_path = self.prompts_path / f"{template_name}.txt"
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            print(f"⚠️ 提示词模板文件未找到: {template_path}")
            return ""
        except Exception as e:
            print(f"⚠️ 加载提示词模板错误: {e}")
            return ""
            
    def get_categories(self):
        """获取话题分类"""
        return TOPIC_CATEGORIES
        
    def get_personas(self):
        """获取可用的角色人设"""
        personas = {}
        if self.personas_path.exists():
            for i, persona_file in enumerate(self.personas_path.glob("*.txt"), 1):
                personas[str(i)] = {
                    "name": persona_file.stem,
                    "path": persona_file
                }
        return personas
        
    def load_persona(self, persona_path):
        """加载角色人设内容"""
        try:
            with open(persona_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            return ""
        
    def select_persona(self):
        """选择角色人设"""
        personas = self.get_personas()
        
        if not personas:
            print("📁 未找到角色人设文件")
            return input("请手动输入角色特质: ").strip() or "客观专业的知识分享者"
            
        print("\n👤 选择角色人设:")
        print("0. 手动输入")
        for key, value in personas.items():
            print(f"{key}. {value['name']}")
            
        choice = input("请选择 (0-{}): ".format(len(personas))).strip()
        
        if choice == "0":
            return input("请手动输入角色特质: ").strip() or "客观专业的知识分享者"
        elif choice in personas:
            persona_content = self.load_persona(personas[choice]['path'])
            print(f"✅ 已加载角色: {personas[choice]['name']}")
            return persona_content
        else:
            print("❌ 无效选择，使用默认角色")
            return "客观专业的知识分享者"
        
    def generate_titles(self, category, count, persona):
        """生成话题标题"""
        system_prompt = self.load_prompt_template("topic_title_generation_system")
        if not system_prompt:
            raise ValueError("系统提示词加载失败")
        
        # 组装用户消息，包含变量替换
        user_message = f"""请根据以下信息生成{count}个话题标题：

角色人设：
{persona}

话题分类：{category['name']}
关键词：{', '.join(category['keywords'])}
生成数量：{count}个

请严格按照JSON数组格式输出标题列表：
["标题1", "标题2", "标题3", ...]"""
        
        print(f"🤖 正在生成{count}个{category['name']}标题...")
        title_config = GENERATION_CONFIG["title_generation"]
        response = self.llm_client.call(
            system_prompt_or_full_prompt=system_prompt,
            user_message=user_message,
            agent_name="话题标题生成器",
            max_tokens=title_config["max_tokens"],
            temperature=title_config["temperature"],
            stream=title_config["stream"]
        )
        
        # 检查LLM调用是否成功
        if response.startswith("❌"):
            raise RuntimeError(f"LLM调用失败: {response}")
        
        # 使用通用JSON提取器解析标题数组
        titles = JSONExtractor.extract_json_array(response)
        
        # 验证返回的标题数量
        if not isinstance(titles, list) or len(titles) < count:
            raise ValueError(f"生成的标题数量不足，期望{count}个，实际{len(titles)}个")
            
        return titles[:count]
        
    def generate_content(self, title, category, persona):
        """为标题生成详细内容"""
        system_prompt = self.load_prompt_template("topic_content_generation_system")
        if not system_prompt:
            raise ValueError("内容生成系统提示词加载失败")
        
        # 组装用户消息，包含变量替换
        user_message = f"""请根据上述要求，为给定的话题标题"{title}"生成详细内容。

重点关注：
- 内容与标题的高度匹配性
- 角色专业知识的体现  
- 内容的深度和价值

**AI角色人设：**
{persona}

**当前生成任务：**
- 话题标题：{title}
- 话题类型：{category['name']}
- 关键词范围：{', '.join(category['keywords'])}"""
        
        print(f"📝 正在为'{title}'生成内容...")
        content_config = GENERATION_CONFIG["content_generation"]
        response = self.llm_client.call(
            system_prompt_or_full_prompt=system_prompt,
            user_message=user_message,
            agent_name="内容生成器",
            max_tokens=content_config["max_tokens"],
            temperature=content_config["temperature"],
            stream=content_config["stream"]
        )
        
        # 检查LLM调用是否成功
        if response.startswith("❌"):
            raise RuntimeError(f"LLM调用失败: {response}")
        
        # 使用通用JSON提取器解析内容
        return JSONExtractor.extract_field_from_json(response, 'topic_content')
        
    def save_topic(self, category, title, content, keywords=""):
        """保存话题到数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO topics (category, title, content, keywords) VALUES (?, ?, ?, ?)",
                (category, title, content, keywords)
            )
            return cursor.lastrowid
            
    def show_recent_topics(self):
        """显示最近生成的话题"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT category, title, created_at FROM topics ORDER BY created_at DESC LIMIT 10"
            )
            topics = cursor.fetchall()
            
        if topics:
            print("\n📚 最近生成的话题:")
            for i, (category, title, created_at) in enumerate(topics, 1):
                print(f"{i:2d}. [{category}] {title} ({created_at})")
        else:
            print("\n暂无生成记录")
            
    def run(self):
        """运行话题生成器"""
        print("\n🎯 话题生成器")
        print("-" * 40)
        
        # 显示最近话题
        self.show_recent_topics()
        
        # 选择分类
        categories = self.get_categories()
        print("\n📂 选择话题分类:")
        for key, value in categories.items():
            print(f"{key}. {value['name']}")
            
        category_choice = input("请选择分类 (1-6): ").strip()
        if category_choice not in categories:
            print("❌ 无效分类")
            return
            
        category = categories[category_choice]
        
        # 设置生成数量
        try:
            count = int(input("生成数量 (1-10): "))
            if not 1 <= count <= 10:
                raise ValueError()
        except ValueError:
            print("❌ 无效数量")
            return
            
        # 设置角色人设
        persona = self.select_persona()
        
        print(f"\n🚀 开始生成 {count} 个 {category['name']} 话题...")
        
        # 生成标题
        titles = self.generate_titles(category, count, persona)
        
        # 为每个标题生成内容并保存
        generated = []
        for i, title in enumerate(titles, 1):
            print(f"  📝 生成第 {i} 个话题: {title}")
            content = self.generate_content(title, category, persona)
            keywords = " ".join(category['keywords'])
            
            topic_id = self.save_topic(category['name'], title, content, keywords)
            generated.append({
                'id': topic_id,
                'title': title,
                'content': content
            })
            
        # 显示生成结果
        print(f"\n✅ 成功生成 {len(generated)} 个话题!")
        for topic in generated:
            print(f"\n📌 {topic['title']}")
            print(f"   {topic['content'][:100]}...")
            
        input("\n按回车键返回主菜单...")