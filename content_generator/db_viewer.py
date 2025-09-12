# -*- coding: utf-8 -*-
"""
SQLite数据库查看工具
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

class DatabaseViewer:
    """数据库查看器"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent / "data" / "topics.db"
        
    def show_all_topics(self):
        """显示所有话题"""
        if not self.db_path.exists():
            print("❌ 数据库文件不存在")
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, category, title, content, keywords, created_at 
                    FROM topics 
                    ORDER BY created_at DESC
                """)
                topics = cursor.fetchall()
                
            if not topics:
                print("📂 数据库为空")
                return
                
            print(f"\n📚 数据库中共有 {len(topics)} 条记录:\n")
            print("="*80)
            
            for topic in topics:
                id, category, title, content, keywords, created_at = topic
                print(f"ID: {id}")
                print(f"分类: {category}")
                print(f"标题: {title}")
                print(f"关键词: {keywords}")
                print(f"创建时间: {created_at}")
                print(f"内容预览: {content[:100]}...")
                print("-"*80)
                
        except Exception as e:
            print(f"❌ 数据库查询错误: {e}")
    
    def show_topic_by_id(self, topic_id: int):
        """显示指定ID的话题详情"""
        if not self.db_path.exists():
            print("❌ 数据库文件不存在")
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, category, title, content, keywords, created_at 
                    FROM topics 
                    WHERE id = ?
                """, (topic_id,))
                topic = cursor.fetchone()
                
            if not topic:
                print(f"❌ 未找到ID为 {topic_id} 的话题")
                return
                
            id, category, title, content, keywords, created_at = topic
            print(f"\n📖 话题详情 (ID: {id})")
            print("="*80)
            print(f"分类: {category}")
            print(f"标题: {title}")
            print(f"关键词: {keywords}")
            print(f"创建时间: {created_at}")
            print(f"\n内容:")
            print("-"*40)
            print(content)
            print("="*80)
                
        except Exception as e:
            print(f"❌ 数据库查询错误: {e}")
    
    def show_statistics(self):
        """显示数据库统计信息"""
        if not self.db_path.exists():
            print("❌ 数据库文件不存在")
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 总数统计
                total = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
                
                # 分类统计
                categories = conn.execute("""
                    SELECT category, COUNT(*) 
                    FROM topics 
                    GROUP BY category 
                    ORDER BY COUNT(*) DESC
                """).fetchall()
                
                # 最新记录
                latest = conn.execute("""
                    SELECT created_at 
                    FROM topics 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """).fetchone()
                
            print(f"\n📊 数据库统计信息:")
            print("="*50)
            print(f"总话题数: {total}")
            print(f"最新记录: {latest[0] if latest else '无'}")
            print(f"\n分类统计:")
            for category, count in categories:
                print(f"  {category}: {count} 条")
            print("="*50)
                
        except Exception as e:
            print(f"❌ 数据库查询错误: {e}")
    
    def export_to_json(self, output_file: str = "topics_export.json"):
        """导出数据库到JSON文件"""
        if not self.db_path.exists():
            print("❌ 数据库文件不存在")
            return
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, category, title, content, keywords, created_at 
                    FROM topics 
                    ORDER BY created_at DESC
                """)
                topics = cursor.fetchall()
                
            # 转换为字典列表
            topics_data = []
            for topic in topics:
                topics_data.append({
                    "id": topic[0],
                    "category": topic[1],
                    "title": topic[2],
                    "content": topic[3],
                    "keywords": topic[4],
                    "created_at": topic[5]
                })
            
            # 导出到JSON文件
            output_path = Path(__file__).parent / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(topics_data, f, ensure_ascii=False, indent=2)
                
            print(f"✅ 成功导出 {len(topics_data)} 条记录到 {output_path}")
                
        except Exception as e:
            print(f"❌ 导出失败: {e}")

def main():
    """主函数"""
    viewer = DatabaseViewer()
    
    while True:
        print("\n" + "="*50)
        print("         📊 数据库查看工具")
        print("="*50)
        print("1. 显示所有话题")
        print("2. 显示指定话题详情")
        print("3. 显示统计信息")
        print("4. 导出到JSON文件")
        print("0. 退出")
        print("-"*50)
        
        choice = input("请选择操作 (0-4): ").strip()
        
        if choice == "0":
            print("👋 再见!")
            break
        elif choice == "1":
            viewer.show_all_topics()
        elif choice == "2":
            try:
                topic_id = int(input("请输入话题ID: "))
                viewer.show_topic_by_id(topic_id)
            except ValueError:
                print("❌ 请输入有效的数字ID")
        elif choice == "3":
            viewer.show_statistics()
        elif choice == "4":
            output_file = input("输出文件名 (默认: topics_export.json): ").strip()
            if not output_file:
                output_file = "topics_export.json"
            viewer.export_to_json(output_file)
        else:
            print("❌ 无效选择")
        
        if choice != "0":
            input("\n按回车键继续...")

if __name__ == "__main__":
    main()