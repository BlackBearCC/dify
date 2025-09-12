# 内容生成器

一个简洁的Python内容生成工具集，支持多种类型的内容生成。

## 功能特点

- 🎯 **话题生成**: 基于AI角色人设生成不重复的话题内容
- 🖼️ **图片描述生成**: (开发中)
- 😄 **笑话生成**: (开发中) 
- 🧠 **记忆生成**: (开发中)
- 💾 **SQLite存储**: 自动保存生成的内容
- 🚀 **交互式界面**: 简洁的命令行交互

## 快速开始

```bash
cd content_generator
python main.py
```

## 项目结构

```
content_generator/
├── main.py                 # 主启动器
├── generators/            # 生成器模块
│   ├── __init__.py
│   ├── topic_generator.py # 话题生成器
│   └── [其他生成器...]
├── data/                  # 数据存储
│   └── topics.db         # SQLite数据库
└── README.md
```

## 话题生成器

支持以下分类:
- 娱乐八卦
- 科技数码  
- 生活时尚
- 美食旅游
- 体育健身
- 教育学习

## 扩展开发

添加新的生成器:
1. 在 `generators/` 目录下创建新模块
2. 实现 `run()` 方法
3. 在 `main.py` 中注册

## 依赖

- Python 3.7+
- sqlite3 (内置)
- requests (用于API调用)