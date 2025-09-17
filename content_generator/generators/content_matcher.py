"""
通用内容匹配生成器
基于内容描述生成相关查询词条的工具
"""

import json
import sqlite3
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.llm_client import create_claude_client, create_doubao_client, create_deepseek_client
from config import LLM_CONFIG, DEFAULT_LLM_PROVIDER


class ContentMatcher:
    """通用内容匹配生成器"""

    def __init__(self):
        self.db_path = Path(__file__).parent.parent / "data" / "content_matches.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(exist_ok=True)

        # 创建资源目录结构
        self.resources_dir = Path(__file__).parent.parent / "resources"
        self.csv_dir = self.resources_dir / "csv"

        # 创建目录
        self.resources_dir.mkdir(exist_ok=True)
        self.csv_dir.mkdir(exist_ok=True)

        self.init_db()
        self.init_llm_client()

    def init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_content TEXT NOT NULL,
                    query_terms TEXT NOT NULL,
                    match_type TEXT DEFAULT 'general',
                    generation_type TEXT DEFAULT 'query',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 检查是否需要添加新列（兼容旧数据库）
            cursor = conn.execute("PRAGMA table_info(content_matches)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'generation_type' not in columns:
                conn.execute("ALTER TABLE content_matches ADD COLUMN generation_type TEXT DEFAULT 'query'")
                print("📊 数据库已升级，添加生成类型字段")

    def init_llm_client(self):
        """初始化LLM客户端"""
        provider = "deepseek"  # 指定使用deepseek模型
        config = LLM_CONFIG[provider]

        if provider == "claude":
            self.llm_client = create_claude_client(
                api_key=config["api_key"],
                model=config.get("model", "claude-sonnet-4-20250514"),
                base_url=config.get("base_url")
            )
        elif provider == "doubao":
            self.llm_client = create_doubao_client(
                api_key=config["api_key"],
                model=config.get("model", "doubao-1.6"),
                base_url=config.get("base_url")
            )
        elif provider == "deepseek":
            self.llm_client = create_deepseek_client(
                api_key=config["api_key"],
                model=config.get("model", "deepseek-V3"),
                base_url=config.get("base_url")
            )
        else:
            raise ValueError(f"不支持的LLM提供商: {provider}")

        print(f"🤖 已初始化LLM客户端: {provider}")

#     def load_system_prompt(self) -> str:
#         """加载系统提示词"""
#         return """你是一个向量搜索查询扩展专家。基于向量搜索的语义相似性原理，为给定内容生成能够触发语义匹配的多样化查询词汇。

# 核心策略（基于搜索引擎查询扩展理论）：
# 1. 【直接描述】- 内容的直观描述词汇
# 2. 【情感触发】- 什么情感状态会让用户想要这个内容（开心、难过、想念、感动等）
# 3. 【场景需求】- 什么聊天场景会用到（安慰别人、表达爱意、庆祝、道歉等）
# 4. 【关系表达】- 适用于什么关系（恋人、朋友、家人、同事等）
# 5. 【行为动机】- 用户想表达什么行为（关怀、支持、祝福、感谢等）
# 6. 【语气风格】- 不同的表达风格（温柔、俏皮、正式、幽默等）

# 查询扩展核心思维：
# - 用户在什么心情下会搜索这个内容？
# - 用户想对谁表达什么时会用到？
# - 什么情况下用户需要这种表达方式？
# - 这个内容能解决用户什么沟通需求？

# 要求：
# - 生成15个高质量且多样化的查询词汇和短句
# - 用 | 分隔
# - 包含单词、短语、情绪、意图、简短句子
# - 避免重复和相似表达，确保多样性
# - 每个词汇都要从不同角度触发

# 示例：
# 输入：两只小熊抱在一起
# 输出：抱抱|拥抱|想你了|安慰|温暖|关怀|亲密|爱你|想念|孤独|需要陪伴|心情不好|想要安慰别人的时候|感觉需要一个温暖的拥抱|想对喜欢的人表达关爱"""

    def load_system_prompt(self) -> str:
        """加载系统提示词"""
        return """你是一个向量搜索辅助专家。你的任务是分析给定的内容描述，理解用户在什么情况下会想要搜索到这个内容，然后生成相应的查询词条。

核心原则：
1. 从用户需求角度思考：用户表达什么情绪、需求、场景时会需要这个内容？
2. 生成触发场景词条：不是简单的同义词替换，而是能触发使用这个内容的场景词汇
3. 理解情感表达需求：分析内容承载的情感，生成对应的情感表达词条
4. 考虑使用语境：什么样的对话、聊天场景会需要这个内容？

要求：
- 每个词条用 | 分隔
- 生成30个触发词条，禁止重复
- 词条可以是词、短语、句子，要自然、符合用户表达习惯
- 重点关注情感表达、需求场景、使用情境
- 禁止过多描述主体名词和动词，重要的是情绪和意图
- 输出应为 描述|名词|动词|其他词句...

输出格式：直接输出用|分隔的词条列表，不要其他解释。

示例：
输入：一只黑猫竖着两个大拇指表示很赞
输出：竖着两个大拇指赞|点赞|赞同|支持|认可|好评|棒|厉害|优秀|不错|满意|推荐|称赞

输入：白色仓鼠露出惊讶表情
输出：仓鼠惊讶表情|惊讶|震惊|意外|不敢相信|吃惊|诧异|惊奇|疑惑|困惑|疑问|什么|真的吗|表示疑问

输入：两只小熊抱在一起
输出：小熊抱在一起甜蜜爱意|抱抱|拥抱|想你了|安慰|温暖|关怀|亲密|爱你|想念|孤独|需要陪伴|心情不好|想要安慰别人的时候|感觉需要一个温暖的拥抱|想对喜欢的人表达关爱"""

    def load_response_prompt(self) -> str:
        """加载表情包响应词生成提示词"""
        return """你是一个对话响应分析专家。你的任务是分析给定的表情包内容，理解当别人说什么话时，我会用这个表情包来回复。

核心思维 - 反向生成逻辑：
1. 【触发对话】- 什么样的具体话语会让人想用这个表情回复？
2. 【情感触发】- 这个表情是对什么情感状态的回应？
3. 【日常对话】- 在什么聊天情况下会用这个表情？
4. 【回应逻辑】- 别人表达什么时，这个表情是合适的回复？

反向生成原则：
- 思考：别人说X，我回复这个表情包
- 生成真实的对话句子和触发词语
- 考虑表情包的回应功能和社交意义
- 重点是能触发使用这个表情作为回复的具体话语

要求：
- 生成30个触发响应的话语、词语和短句
- 用 | 分隔
- 包含完整的对话句子、单个词语、短语
- 不要引号包裹，要自然真实的表达
- 避免描述表情本身，重点是触发它的对话内容
- 涵盖日常聊天的各种场景

输出格式：直接输出用|分隔的响应触发词列表，不要其他解释。

示例：
输入：一只黑猫竖着两个大拇指表示很赞
输出：我升职了|考试通过了|好消息|成功了|完成任务了|取得成就|获得奖励|做得很好|表现优秀|得到认可|赢了比赛|解决问题了|克服困难了|达成目标|实现梦想|收到好评|被表扬了|获得成功|值得庆祝|应该鼓励|太棒了|厉害|牛逼|给力|6666|awesome|great|干得好|不错|满意

输入：白色仓鼠露出惊讶表情
输出：没想到啊|真的假的|不可能吧|怎么会这样|太神奇了|意外|突然|震惊|吃惊|惊讶|诧异|没想到|出人意料|令人震惊|不敢相信|太离谱了|这也行|什么情况|咋回事|怎么回事|发生什么了|真的吗|不会吧|哇|我去|卧槽|天哪|我的天|太夸张了|绝了

输入：小猫咪在思考
输出：不知道怎么办|有个问题|帮我想想|怎么选择|纠结|困惑|不理解|求建议|需要帮助|想不通|搞不明白|犹豫|拿不定主意|要考虑一下|让我想想|这怎么办|怎么处理|该选哪个|不确定|疑问|为什么|怎么回事|什么意思|不懂|难题|选择困难|纠结死了|头疼|麻烦了"""

    def generate_response_terms(self, content: str) -> List[str]:
        """为内容生成响应触发词条（反向生成）"""
        try:
            # 构建用户消息
            user_message = f"请为以下表情包内容生成响应触发词条：\n\n{content}"

            # 调用LLM
            response = self.llm_client.call(
                system_prompt_or_full_prompt=self.load_response_prompt(),
                user_message=user_message,
                agent_name="表情包响应生成器",
                max_tokens=2048,
                temperature=0.8
            )

            # 检查LLM调用是否成功
            if response.startswith("❌"):
                raise RuntimeError(f"LLM调用失败: {response}")

            # 清理和分割响应
            cleaned_response = response.strip()
            # 移除可能的引号或其他包装字符
            cleaned_response = re.sub(r'^["\']|["\']$', '', cleaned_response)

            # 按|分割并清理每个词条
            terms = [term.strip() for term in cleaned_response.split('|') if term.strip()]

            if not terms:
                raise ValueError("未能生成有效的响应触发词条")

            return terms

        except Exception as e:
            print(f"❌ 生成响应触发词条失败: {e}")
            return [content]  # 返回原内容作为备选

    def generate_query_terms(self, content: str) -> List[str]:

            # 调用LLM
            response = self.llm_client.call(
                system_prompt_or_full_prompt=self.load_system_prompt(),
                user_message=user_message,
                agent_name="内容匹配生成器",
                max_tokens=2048,
                temperature=0.8
            )

            # 检查LLM调用是否成功
            if response.startswith("❌"):
                raise RuntimeError(f"LLM调用失败: {response}")

            # 清理和分割响应
            cleaned_response = response.strip()
            # 移除可能的引号或其他包装字符
            cleaned_response = re.sub(r'^["\']|["\']$', '', cleaned_response)

            # 按|分割并清理每个词条
            terms = [term.strip() for term in cleaned_response.split('|') if term.strip()]

            if not terms:
                raise ValueError("未能生成有效的查询词条")

            return terms



    def save_content_match(self, original_content: str, query_terms: List[str],
                          match_type: str = "general", generation_type: str = "query") -> int:
        """保存内容匹配到数据库"""
        terms_text = " | ".join(query_terms)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO content_matches (original_content, query_terms, match_type, generation_type)
                VALUES (?, ?, ?, ?)
            """, (original_content, terms_text, match_type, generation_type))
            return cursor.lastrowid

    def batch_generate_matches(self, content_list: List[str],
                              match_type: str = "general", generation_type: str = "query") -> List[Dict[str, Any]]:
        """批量生成内容匹配"""
        results = []
        total = len(content_list)

        generation_name = "查询词条" if generation_type == "query" else "响应词条"
        print(f"🔄 开始批量处理 {total} 个内容，生成{generation_name}...")

        for i, content in enumerate(content_list, 1):
            try:
                print(f"  📝 处理第 {i}/{total} 个: {content[:50]}...")

                # 根据生成类型选择不同的生成方法
                if generation_type == "query":
                    query_terms = self.generate_query_terms(content)
                else:  # response
                    query_terms = self.generate_response_terms(content)

                # 保存到数据库
                record_id = self.save_content_match(content, query_terms, match_type, generation_type)

                result = {
                    "id": record_id,
                    "original_content": content,
                    "query_terms": query_terms,
                    "match_type": match_type,
                    "generation_type": generation_type
                }

                results.append(result)
                print(f"    ✅ 生成 {len(query_terms)} 个{generation_name}")

            except Exception as e:
                print(f"    ❌ 处理失败: {e}")
                continue

        return results

    def batch_generate_responses(self, content_list: List[str],
                               match_type: str = "response") -> List[Dict[str, Any]]:
        """批量生成响应词条（反向生成）"""
        return self.batch_generate_matches(content_list, match_type, "response")

    def export_to_csv(self, results: List[Dict[str, Any]],
                     match_type: str = "general") -> str:
        """导出结果到CSV文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 根据生成类型确定文件名
        if results and 'generation_type' in results[0]:
            generation_type = results[0]['generation_type']
            type_name = "query" if generation_type == "query" else "response"
        else:
            type_name = "query"

        filename = f"content_matches_{type_name}_{match_type}_{timestamp}.csv"
        filepath = self.output_dir / filename

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['序号', '原始内容', '生成词条', '匹配类型', '生成类型']
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for result in results:
                generation_type = result.get('generation_type', 'query')
                type_display = "查询词条" if generation_type == "query" else "响应词条"

                writer.writerow({
                    '序号': result['id'],
                    '原始内容': result['original_content'],
                    '生成词条': ' | '.join(result['query_terms']),
                    '匹配类型': result['match_type'],
                    '生成类型': type_display
                })

        return str(filepath)

    def list_csv_files(self) -> List[Path]:
        """列出CSV目录下的所有CSV文件"""
        csv_files = []
        if self.csv_dir.exists():
            csv_files = list(self.csv_dir.glob("*.csv"))
        return sorted(csv_files)

    def get_csv_columns(self, csv_path: Path) -> List[str]:
        """获取CSV文件的列名"""
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                header = next(reader, [])
                return [col.strip() for col in header if col.strip()]
        except Exception as e:
            print(f"❌ 读取CSV文件列名失败: {e}")
            return []

    def preview_csv_data(self, csv_path: Path, column: str, limit: int = 5) -> List[str]:
        """预览CSV文件指定列的数据"""
        data = []
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= limit:
                        break
                    if column in row and row[column].strip():
                        data.append(row[column].strip())
        except Exception as e:
            print(f"❌ 预览CSV数据失败: {e}")
        return data

    def load_from_csv(self, csv_path: str, content_column: str = "原始内容") -> List[str]:
        """从CSV文件加载内容列表"""
        contents = []

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if content_column in row and row[content_column].strip():
                        contents.append(row[content_column].strip())
        except Exception as e:
            print(f"❌ 读取CSV文件失败: {e}")
            return []

        return contents

    def show_recent_matches(self):
        """显示最近生成的匹配记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT original_content, query_terms, match_type, generation_type, created_at
                FROM content_matches
                ORDER BY created_at DESC
                LIMIT 10
            """)
            matches = cursor.fetchall()

        if matches:
            print("\n📚 最近生成的匹配记录:")
            for i, (content, terms, match_type, generation_type, created_at) in enumerate(matches, 1):
                content_preview = content[:40] + "..." if len(content) > 40 else content
                terms_preview = terms[:60] + "..." if len(terms) > 60 else terms

                # 显示生成类型
                type_display = "查询词条" if generation_type == "query" else "响应词条"
                print(f"{i:2d}. [{match_type}|{type_display}] {content_preview}")
                print(f"     → {terms_preview} ({created_at})")
        else:
            print("\n暂无匹配记录")

    def run(self):
        """运行内容匹配生成器"""
        print("\n🎯 通用内容匹配生成器")
        print("-" * 40)

        # 显示最近记录
        self.show_recent_matches()

        print("\n📋 选择操作模式:")
        print("1. 单个查询词生成")
        print("2. 批量查询词生成")
        print("3. 单个响应词生成 (反向)")
        print("4. 批量响应词生成 (反向)")
        print("5. 从resources/csv目录选择文件")
        print("6. 手动输入CSV文件路径")

        try:
            choice = int(input("请选择操作模式 (1-6): "))
        except ValueError:
            print("❌ 无效选择")
            return

        if choice == 1:
            # 单个查询词生成
            content = input("\n请输入要匹配的内容: ").strip()
            if not content:
                print("❌ 内容不能为空")
                return

            match_type = input("请输入匹配类型 (默认: general): ").strip() or "general"

            print(f"\n🔄 正在生成查询词条...")
            query_terms = self.generate_query_terms(content)

            if query_terms:
                # 保存到数据库
                record_id = self.save_content_match(content, query_terms, match_type, "query")

                print(f"\n✅ 成功生成 {len(query_terms)} 个查询词条:")
                for i, term in enumerate(query_terms, 1):
                    print(f"  {i:2d}. {term}")

                print(f"\n📝 记录已保存 (ID: {record_id})")
            else:
                print("❌ 查询词条生成失败")

        elif choice == 2:
            # 批量查询词生成
            print("\n请输入要匹配的内容列表 (每行一个，空行结束):")
            content_list = []
            while True:
                line = input().strip()
                if not line:
                    break
                content_list.append(line)

            if not content_list:
                print("❌ 没有输入任何内容")
                return

            match_type = input("请输入匹配类型 (默认: general): ").strip() or "general"

            # 确认处理
            confirm = input(f"\n是否开始处理这 {len(content_list)} 个内容生成查询词条? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes', '是']:
                print("👋 已取消处理")
                return

            # 批量处理
            results = self.batch_generate_matches(content_list, match_type, "query")

            if results:
                # 导出到CSV
                csv_path = self.export_to_csv(results, match_type)
                print(f"\n✅ 成功处理 {len(results)} 个内容!")
                print(f"📄 结果已导出到: {csv_path}")

                # 显示部分结果
                print("\n📋 处理结果预览:")
                for i, result in enumerate(results[:3], 1):
                    content_preview = result['original_content'][:40] + "..." if len(result['original_content']) > 40 else result['original_content']
                    print(f"{i}. {content_preview}")
                    print(f"   → {' | '.join(result['query_terms'][:5])}{'...' if len(result['query_terms']) > 5 else ''}")

                if len(results) > 3:
                    print(f"   ... 还有 {len(results) - 3} 条记录")
            else:
                print("❌ 没有成功处理任何内容")

        elif choice == 3:
            # 单个响应词生成
            content = input("\n请输入表情包内容描述: ").strip()
            if not content:
                print("❌ 内容不能为空")
                return

            match_type = input("请输入匹配类型 (默认: response): ").strip() or "response"

            print(f"\n🔄 正在生成响应触发词条...")
            response_terms = self.generate_response_terms(content)

            if response_terms:
                # 保存到数据库
                record_id = self.save_content_match(content, response_terms, match_type, "response")

                print(f"\n✅ 成功生成 {len(response_terms)} 个响应触发词条:")
                for i, term in enumerate(response_terms, 1):
                    print(f"  {i:2d}. {term}")

                print(f"\n📝 记录已保存 (ID: {record_id})")
            else:
                print("❌ 响应触发词条生成失败")

        elif choice == 4:
            # 批量响应词生成
            print("\n请输入表情包内容描述列表 (每行一个，空行结束):")
            content_list = []
            while True:
                line = input().strip()
                if not line:
                    break
                content_list.append(line)

            if not content_list:
                print("❌ 没有输入任何内容")
                return

            match_type = input("请输入匹配类型 (默认: response): ").strip() or "response"

            # 确认处理
            confirm = input(f"\n是否开始处理这 {len(content_list)} 个内容生成响应词条? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes', '是']:
                print("👋 已取消处理")
                return

            # 批量处理
            results = self.batch_generate_responses(content_list, match_type)

            if results:
                # 导出到CSV
                csv_path = self.export_to_csv(results, match_type)
                print(f"\n✅ 成功处理 {len(results)} 个内容!")
                print(f"📄 结果已导出到: {csv_path}")

                # 显示部分结果
                print("\n📋 处理结果预览:")
                for i, result in enumerate(results[:3], 1):
                    content_preview = result['original_content'][:40] + "..." if len(result['original_content']) > 40 else result['original_content']
                    print(f"{i}. {content_preview}")
                    print(f"   → {' | '.join(result['query_terms'][:5])}{'...' if len(result['query_terms']) > 5 else ''}")

                if len(results) > 3:
                    print(f"   ... 还有 {len(results) - 3} 条记录")
            else:
                print("❌ 没有成功处理任何内容")

        elif choice == 5:
            # 从resources/csv目录选择文件
            csv_files = self.list_csv_files()
            if not csv_files:
                print(f"❌ 在 {self.csv_dir} 中未找到CSV文件")
                print(f"💡 请将CSV文件放在: {self.csv_dir}")
                return

            print(f"\n📁 在 {self.csv_dir} 中找到以下CSV文件:")
            for i, csv_file in enumerate(csv_files, 1):
                print(f"{i:2d}. {csv_file.name}")

            try:
                file_choice = int(input(f"\n请选择CSV文件 (1-{len(csv_files)}): "))
                if not 1 <= file_choice <= len(csv_files):
                    raise ValueError()
            except ValueError:
                print("❌ 无效选择")
                return

            selected_csv = csv_files[file_choice - 1]
            print(f"✅ 已选择: {selected_csv.name}")

            # 获取CSV列名
            columns = self.get_csv_columns(selected_csv)
            if not columns:
                print("❌ 无法读取CSV文件列名")
                return

            print(f"\n📋 CSV文件包含以下列:")
            for i, column in enumerate(columns, 1):
                print(f"{i:2d}. {column}")

            try:
                col_choice = int(input(f"\n请选择内容列 (1-{len(columns)}): "))
                if not 1 <= col_choice <= len(columns):
                    raise ValueError()
            except ValueError:
                print("❌ 无效选择")
                return

            selected_column = columns[col_choice - 1]
            print(f"✅ 已选择列: {selected_column}")

            # 预览数据
            preview_data = self.preview_csv_data(selected_csv, selected_column)
            if preview_data:
                print(f"\n👀 数据预览 (前{len(preview_data)}条):")
                for i, item in enumerate(preview_data, 1):
                    item_preview = item[:60] + "..." if len(item) > 60 else item
                    print(f"  {i}. {item_preview}")

            # 选择生成类型
            print("\n🎯 选择生成类型:")
            print("1. 查询词条生成 (正向)")
            print("2. 响应词条生成 (反向)")

            try:
                gen_choice = int(input("请选择生成类型 (1-2): "))
                if gen_choice == 1:
                    generation_type = "query"
                    default_match_type = "general"
                elif gen_choice == 2:
                    generation_type = "response"
                    default_match_type = "response"
                else:
                    raise ValueError()
            except ValueError:
                print("❌ 无效选择")
                return

            match_type = input(f"\n请输入匹配类型 (默认: {default_match_type}): ").strip() or default_match_type

            # 加载完整内容
            content_list = self.load_from_csv(str(selected_csv), selected_column)
            if not content_list:
                print("❌ 未能从CSV文件加载任何内容")
                return

            print(f"📊 从CSV文件加载了 {len(content_list)} 个内容")

            # 确认处理
            confirm = input(f"\n是否开始处理这 {len(content_list)} 个内容? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes', '是']:
                print("👋 已取消处理")
                return

            # 批量处理
            results = self.batch_generate_matches(content_list, match_type, generation_type)

            if results:
                # 导出到CSV
                output_csv_path = self.export_to_csv(results, match_type)
                print(f"\n✅ 成功处理 {len(results)} 个内容!")
                print(f"📄 结果已导出到: {output_csv_path}")
            else:
                print("❌ 没有成功处理任何内容")

        elif choice == 6:
            # 手动输入CSV文件路径
            csv_path = input("\n请输入CSV文件路径: ").strip()
            if not csv_path or not Path(csv_path).exists():
                print("❌ 文件不存在")
                return

            csv_file = Path(csv_path)
            print(f"✅ 已选择: {csv_file.name}")

            # 获取CSV列名
            columns = self.get_csv_columns(csv_file)
            if not columns:
                print("❌ 无法读取CSV文件列名")
                return

            print(f"\n📋 CSV文件包含以下列:")
            for i, column in enumerate(columns, 1):
                print(f"{i:2d}. {column}")

            try:
                col_choice = int(input(f"\n请选择内容列 (1-{len(columns)}): "))
                if not 1 <= col_choice <= len(columns):
                    raise ValueError()
            except ValueError:
                print("❌ 无效选择")
                return

            selected_column = columns[col_choice - 1]
            print(f"✅ 已选择列: {selected_column}")

            # 选择生成类型
            print("\n🎯 选择生成类型:")
            print("1. 查询词条生成 (正向)")
            print("2. 响应词条生成 (反向)")

            try:
                gen_choice = int(input("请选择生成类型 (1-2): "))
                if gen_choice == 1:
                    generation_type = "query"
                    default_match_type = "general"
                elif gen_choice == 2:
                    generation_type = "response"
                    default_match_type = "response"
                else:
                    raise ValueError()
            except ValueError:
                print("❌ 无效选择")
                return

            match_type = input(f"\n请输入匹配类型 (默认: {default_match_type}): ").strip() or default_match_type

            # 加载完整内容
            content_list = self.load_from_csv(str(csv_file), selected_column)
            if not content_list:
                print("❌ 未能从CSV文件加载任何内容")
                return

            print(f"📊 从CSV文件加载了 {len(content_list)} 个内容")

            # 确认处理
            generation_name = "查询词条" if generation_type == "query" else "响应词条"
            confirm = input(f"\n是否开始处理这 {len(content_list)} 个内容生成{generation_name}? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes', '是']:
                print("👋 已取消处理")
                return

            # 批量处理
            results = self.batch_generate_matches(content_list, match_type, generation_type)

            if results:
                # 导出到CSV
                output_csv_path = self.export_to_csv(results, match_type)
                print(f"\n✅ 成功处理 {len(results)} 个内容!")
                print(f"📄 结果已导出到: {output_csv_path}")
            else:
                print("❌ 没有成功处理任何内容")

        else:
            print("❌ 无效选择")

        input("\n按回车键返回主菜单...")