#!/usr/bin/env python3
"""
内容生成器 - 主启动器
支持话题生成、图片描述、笑话生成、记忆生成等功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from generators.topic_generator import TopicGenerator
from generators.image_description_generator import ImageDescriptionGenerator
from generators.content_matcher import ContentMatcher
from db_viewer import DatabaseViewer


def show_menu():
    """显示主菜单"""
    print("\n" + "="*50)
    print("         📝 内容生成器")
    print("="*50)
    print("1. 话题生成 (支持1-99个话题，2-20并发)")
    print("2. 图片描述生成 (基于ImageRecognitionWorkflow编号系统)")
    print("3. 内容匹配生成 (将内容转换为查询词条)")
    print("4. 笑话生成 (开发中)")
    print("5. 记忆生成 (开发中)")
    print("8. 数据库查看工具")
    print("0. 退出")
    print("="*50)


def main():
    """主函数"""
    generators = {
        '1': TopicGenerator(),
        '2': ImageDescriptionGenerator(),
        '3': ContentMatcher(),
    }
    
    db_viewer = DatabaseViewer()
    
    while True:
        show_menu()
        choice = input("请选择功能 (0-8): ").strip()
        
        if choice == '0':
            print("再见！")
            break
        elif choice in generators:
            try:
                generators[choice].run()
            except KeyboardInterrupt:
                print("\n操作已取消")
            except Exception as e:
                print(f"❌ 执行出错: {e}")
        elif choice == '8':
            try:
                db_viewer.show_all_topics()
                input("\n按回车键返回主菜单...")
            except Exception as e:
                print(f"❌ 数据库查看出错: {e}")
        else:
            print("❌ 无效选择，请重试")


if __name__ == "__main__":
    main()