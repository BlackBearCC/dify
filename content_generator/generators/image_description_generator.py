"""
图片描述生成器
基于ImageRecognitionWorkflow编号系统的图片描述生成功能
"""

import json
import sqlite3
import csv
import glob
import os
import base64
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from utils.numbering_system import NumberingSystem
from core.llm_client import create_doubao_client
from config import LLM_CONFIG, DEFAULT_LLM_PROVIDER


class ImageDescriptionGenerator:
    """图片描述生成器"""

    def __init__(self):
        self.db_path = Path(__file__).parent.parent / "data" / "image_descriptions.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(exist_ok=True)

        # 创建资源目录结构
        self.resources_dir = Path(__file__).parent.parent / "resources"
        self.images_dir = self.resources_dir / "images"
        self.texts_dir = self.resources_dir / "texts"

        # 创建目录
        self.resources_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
        self.texts_dir.mkdir(exist_ok=True)

        self.numbering = NumberingSystem()
        self.init_db()
        self.init_llm_client()

    def init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS image_descriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numbering_id TEXT NOT NULL,
                    image_name TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category_code TEXT NOT NULL,
                    character TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def init_llm_client(self):
        """初始化LLM客户端"""
        provider = DEFAULT_LLM_PROVIDER
        config = LLM_CONFIG[provider]

        if provider == "doubao":
            # 使用豆包视觉模型
            self.llm_client = create_doubao_client(
                api_key=config["api_key"],
                model="doubao-vision-pro",  # 使用视觉模型
                base_url=config["base_url"]
            )
        else:
            raise ValueError(f"图片描述生成暂不支持的LLM提供商: {provider}")

        print(f"🤖 已初始化LLM客户端: {provider} - doubao-vision-pro")

    def load_system_prompt(self) -> str:
        """加载系统提示词"""
        return """你是一个专业的图片识别助手，擅长分析图片内容并生成准确的标题和详细描述。
请根据提供的图片内容，完成以下任务：
1. 生成一个简短而精确的标题（5-10个字）
2. 提供详细的图片内容描述（100-150字）

输出格式要求：JSON格式，包含以下字段：
- title: 图片标题
- description: 详细描述

请确保输出为严格的JSON格式，禁止输出任何其他内容。
示例：
{
  "title": "公园灰猫",
  "description": "在秋日公园拍摄的照片，画面中一只银灰色短毛猫正蹲坐在人行道上，好奇地用爪子触碰一片枯黄的落叶。背景是公园入口处的绿色拱门和标识牌，周围环绕着多棵落叶树木，树叶呈现金黄色调。阳光透过树叶形成柔和的光影效果，整个场景充满宁静祥和的秋日氛围。猫咪的绿色眼睛和警觉的姿态与周围环境形成了鲜明对比。"
}"""

    def load_image_as_base64(self, image_path: str) -> Dict[str, str]:
        """加载图片并转换为Base64格式"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        with open(image_path, "rb") as img_file:
            img_data = img_file.read()
            base64_img = base64.b64encode(img_data).decode("utf-8")

        # 确定MIME类型
        img_ext = os.path.splitext(image_path)[1].lower()
        if img_ext == ".png":
            mime_type = "image/png"
        elif img_ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif img_ext == ".gif":
            mime_type = "image/gif"
        elif img_ext == ".webp":
            mime_type = "image/webp"
        else:
            mime_type = "image/jpeg"  # 默认

        return {
            "base64_data": base64_img,
            "mime_type": mime_type,
            "size": len(img_data)
        }

    def generate_description(self, image_path: str) -> Dict[str, str]:
        """为单张图片生成描述"""
        try:
            # 加载图片
            image_data = self.load_image_as_base64(image_path)

            # 构建用户消息
            user_message = "请分析这张图片，提供标题和详细描述。"

            # 调用LLM
            response = self.llm_client.call_with_image(
                system_prompt=self.load_system_prompt(),
                user_message=user_message,
                image_base64=image_data["base64_data"],
                image_mime=image_data["mime_type"],
                agent_name="图片描述生成器",
                max_tokens=4096,
                temperature=0.7
            )

            # 检查LLM调用是否成功
            if response.startswith("❌"):
                raise RuntimeError(f"LLM调用失败: {response}")

            # 解析JSON响应
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                return {
                    "title": result.get("title", "无法识别标题"),
                    "description": result.get("description", "无法生成描述")
                }
            else:
                raise ValueError("无法从响应中解析JSON格式")

        except Exception as e:
            return {
                "title": "识别失败",
                "description": f"图片识别过程中出错: {str(e)}"
            }

    def scan_character_images(self, character: str) -> List[str]:
        """扫描指定角色的所有图片"""
        config = self.numbering.get_character_config(character)
        base_path = self.images_dir / character

        # 如果角色目录不存在，创建它
        if not base_path.exists():
            base_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 已创建角色目录: {base_path}")

        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.webp']
        image_paths = []

        # 扫描角色目录下的所有子目录
        for root, dirs, files in os.walk(base_path):
            for ext in image_extensions:
                pattern = os.path.join(root, ext)
                image_paths.extend(glob.glob(pattern))

        return image_paths

    def create_character_directories(self, character: str):
        """为指定角色创建分类目录结构"""
        config = self.numbering.get_character_config(character)
        base_path = self.images_dir / character

        print(f"📁 为 {character} 创建目录结构...")
        created_dirs = []

        for category in config["categories"].keys():
            if category == "通用":
                continue  # 通用分类不创建单独目录

            category_path = base_path / category
            if not category_path.exists():
                category_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(str(category_path))

        if created_dirs:
            print(f"✅ 已创建 {len(created_dirs)} 个分类目录")
            for dir_path in created_dirs:
                print(f"   📂 {dir_path}")
        else:
            print("ℹ️ 所有目录已存在")

        return created_dirs

    def process_images(self, character: str, image_paths: List[str], save_ids: bool = True) -> List[Dict[str, Any]]:
        """批量处理图片"""
        results = []
        total = len(image_paths)

        print(f"🖼️ 开始处理 {total} 张图片...")

        for i, image_path in enumerate(image_paths, 1):
            try:
                print(f"  📸 处理第 {i}/{total} 张: {os.path.basename(image_path)}")

                # 生成描述
                description_result = self.generate_description(image_path)

                # 分类图片并生成编号
                category_code = self.numbering.classify_image_path(image_path, character)
                unique_id = self.numbering.generate_unique_id(category_code)

                # 保存到数据库
                record_id = self.save_description(
                    numbering_id=unique_id,
                    image_name=os.path.basename(image_path),
                    image_path=image_path,
                    title=description_result["title"],
                    description=description_result["description"],
                    category_code=category_code,
                    character=character
                )

                result = {
                    "id": record_id,
                    "numbering_id": unique_id,
                    "image_name": os.path.basename(image_path),
                    "image_path": image_path,
                    "title": description_result["title"],
                    "description": description_result["description"],
                    "category_code": category_code,
                    "character": character
                }

                results.append(result)
                print(f"    ✅ 编号: {unique_id} | 标题: {description_result['title']}")

            except Exception as e:
                print(f"    ❌ 处理失败: {e}")
                continue

        # 保存编号状态
        if save_ids:
            self.numbering.save_id_registry()
            print("✅ 编号状态已保存")
        else:
            print("⚠️ 编号状态未保存（用户选择）")

        return results

    def save_description(self, numbering_id: str, image_name: str, image_path: str,
                        title: str, description: str, category_code: str, character: str) -> int:
        """保存图片描述到数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO image_descriptions
                (numbering_id, image_name, image_path, title, description, category_code, character)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (numbering_id, image_name, image_path, title, description, category_code, character))
            return cursor.lastrowid

    def export_to_csv(self, results: List[Dict[str, Any]], character: str) -> str:
        """导出结果到CSV文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"image_descriptions_{character}_{timestamp}.csv"
        filepath = self.output_dir / filename

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['序号ID', '图片名称', '图片路径', '图片标题', '图片描述', '分类代码', '角色']
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for result in results:
                writer.writerow({
                    '序号ID': result['numbering_id'],
                    '图片名称': result['image_name'],
                    '图片路径': result['image_path'],
                    '图片标题': result['title'],
                    '图片描述': result['description'],
                    '分类代码': result['category_code'],
                    '角色': result['character']
                })

        return str(filepath)

    def show_recent_descriptions(self):
        """显示最近生成的图片描述"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT character, image_name, title, created_at
                FROM image_descriptions
                ORDER BY created_at DESC
                LIMIT 10
            """)
            descriptions = cursor.fetchall()

        if descriptions:
            print("\n📚 最近生成的图片描述:")
            for i, (character, image_name, title, created_at) in enumerate(descriptions, 1):
                print(f"{i:2d}. [{character}] {image_name} - {title} ({created_at})")
        else:
            print("\n暂无生成记录")

    def show_category_status(self, character: str):
        """显示指定角色的分类编号状态"""
        status = self.numbering.get_category_status(character)
        config = self.numbering.get_character_config(character)

        print(f"\n📊 {character} 编号状态:")
        for category, info in status.items():
            if info["code"] in [code for code in config["categories"].values()]:
                print(f"  📝 {category} ({info['code']}): 下一个编号 {info['next_id']}")

    def run(self):
        """运行图片描述生成器"""
        print("\n🖼️ 图片描述生成器")
        print("-" * 40)

        # 显示最近记录
        self.show_recent_descriptions()

        # 选择角色
        characters = self.numbering.get_available_characters()
        print("\n👤 选择角色:")
        for i, character in enumerate(characters, 1):
            print(f"{i}. {character}")

        try:
            choice = int(input(f"请选择角色 (1-{len(characters)}): "))
            if not 1 <= choice <= len(characters):
                raise ValueError()
        except ValueError:
            print("❌ 无效选择")
            return

        character = characters[choice - 1]
        print(f"✅ 已选择角色: {character}")

        # 显示和管理目录结构
        print(f"\n📂 资源目录结构:")
        print(f"   📁 图片目录: {self.images_dir}")
        print(f"   📁 文本目录: {self.texts_dir}")
        print(f"   📁 角色目录: {self.images_dir / character}")

        # 询问是否创建目录结构
        create_dirs = input("\n是否创建/检查角色分类目录结构? (Y/n): ").strip().lower()
        if create_dirs not in ['n', 'no', '否']:
            self.create_character_directories(character)

        # 显示编号状态
        self.show_category_status(character)

        # 询问是否要重置编号
        reset_choice = input("\n是否要重新设置某个分类的起始编号? (y/N): ").strip().lower()
        if reset_choice in ['y', 'yes', '是']:
            config = self.numbering.get_character_config(character)
            categories_list = list(config['categories'].items())

            print("\n📋 请选择要重设编号的分类:")
            for i, (category, code) in enumerate(categories_list, 1):
                current_count = self.numbering.registry["category_counters"].get(code, 0)
                print(f"  {i}. {category} ({code}) - 当前计数: {current_count}")

            try:
                category_choice = int(input(f"请选择分类 (1-{len(categories_list)}): "))
                if 1 <= category_choice <= len(categories_list):
                    selected_category, selected_code = categories_list[category_choice - 1]
                    current_count = self.numbering.registry["category_counters"].get(selected_code, 0)

                    new_count = int(input(f"请输入新的起始计数 (当前: {current_count}): "))
                    if new_count >= 0:
                        self.numbering.reset_category_counter(selected_code, new_count)
                        self.numbering.save_id_registry()
                        next_id = f"99{selected_code}{new_count + 1:04d}"
                        print(f"✅ 已更新 {selected_category} 的计数为 {new_count}")
                        print(f"📝 下一个分配的编号将是: {next_id}")
            except ValueError:
                print("❌ 输入错误，跳过重设编号")

        # 扫描图片
        image_paths = self.scan_character_images(character)
        if not image_paths:
            print(f"\n⚠️ 在 {self.images_dir / character} 中未找到图片文件")
            print(f"💡 请将图片文件放在相应的分类目录中:")
            config = self.numbering.get_character_config(character)
            for category in config["categories"].keys():
                if category != "通用":
                    print(f"   📂 {self.images_dir / character / category}")
            print(f"   📂 {self.images_dir / character} (通用分类)")
            return

        print(f"🔍 发现 {len(image_paths)} 张图片")

        # 显示找到的图片分布
        category_count = {}
        for img_path in image_paths:
            category_code = self.numbering.classify_image_path(img_path, character)
            category_name = None
            config = self.numbering.get_character_config(character)
            for cat_name, cat_code in config["categories"].items():
                if cat_code == category_code:
                    category_name = cat_name
                    break
            category_name = category_name or f"未知({category_code})"
            category_count[category_name] = category_count.get(category_name, 0) + 1

        print("\n📊 图片分类分布:")
        for category, count in category_count.items():
            print(f"   📝 {category}: {count} 张")

        # 询问是否保存编号
        save_ids = True
        save_choice = input("\n是否保存编号到ID注册表? (Y/n): ").strip().lower()
        if save_choice in ['n', 'no', '否']:
            save_ids = False
            print("⚠️ 已禁用编号保存")

        # 确认处理
        confirm = input(f"\n是否开始处理这 {len(image_paths)} 张图片? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes', '是']:
            print("👋 已取消处理")
            return

        # 开始处理
        results = self.process_images(character, image_paths, save_ids)

        if results:
            # 导出到CSV
            csv_path = self.export_to_csv(results, character)
            print(f"\n✅ 成功处理 {len(results)} 张图片!")
            print(f"📄 结果已导出到: {csv_path}")

            # 显示部分结果
            print("\n📋 处理结果预览:")
            for i, result in enumerate(results[:5], 1):
                print(f"{i}. [{result['numbering_id']}] {result['image_name']} - {result['title']}")

            if len(results) > 5:
                print(f"   ... 还有 {len(results) - 5} 条记录")
        else:
            print("❌ 没有成功处理任何图片")

        input("\n按回车键返回主菜单...")