# -*- coding: utf-8 -*-
"""
配置文件 - 内容生成器
"""

import os

# LLM配置
LLM_CONFIG = {
    # 豆包API配置
    "doubao": {
        "api_key": os.environ.get("DOUBAO_API_KEY", "b633a622-b5d0-4f16-a8a9-616239cf15d1"),
        "model": "doubao-1.6",
        "base_url": None  # 使用默认URL
    },
    
    # Claude API配置
    "claude": {
        "api_key": os.environ.get("CLAUDE_API_KEY", "your-claude-api-key-here"),
        "model": "claude-sonnet-4-20250514",
        "base_url": None  # 使用默认URL
    },
    
    # DeepSeek API配置
    "deepseek": {
        "api_key": os.environ.get("DEEPSEEK_API_KEY", "your-deepseek-api-key-here"),
        "model": "deepseek-V3",
        "base_url": None  # 使用默认URL
    }
}

# 默认使用的LLM提供商
DEFAULT_LLM_PROVIDER = "doubao"

# 生成参数配置
GENERATION_CONFIG = {
    "title_generation": {
        "max_tokens": 1000,
        "temperature": 0.8,
        "stream": False
    },
    "content_generation": {
        "max_tokens": 1500,
        "temperature": 0.7,
        "stream": False
    }
}

# 话题分类配置
TOPIC_CATEGORIES = {
    "1": {"name": "娱乐八卦", "keywords": ["明星", "娱乐圈", "影视"]},
    "2": {"name": "科技数码", "keywords": ["科技", "数码", "AI"]},
    "3": {"name": "生活时尚", "keywords": ["生活", "时尚", "穿搭"]},
    "4": {"name": "美食旅游", "keywords": ["美食", "旅游", "餐厅"]},
    "5": {"name": "体育健身", "keywords": ["体育", "健身", "运动"]},
    "6": {"name": "教育学习", "keywords": ["教育", "学习", "知识"]},
}