# -*- coding: utf-8 -*-
"""
简化版Claude问答机器人 - 直接问答，无复杂处理
"""

import requests
import json
import sys
import io
import os
import time
from typing import Optional
from pathlib import Path

# 设置控制台输出编码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def load_env_file():
    """加载.env文件"""
    # 查找.env文件的位置
    current_dir = Path(__file__).parent
    env_paths = [
        current_dir / '.env',  # 当前目录
        current_dir.parent.parent / '.env',  # 项目根目录
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            print(f"🔧 加载环境配置: {env_path}")
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')  # 移除引号
                        os.environ[key] = value
            return True
    return False

# 加载环境变量
load_env_file()

class SimpleClaude:
    def __init__(self):
        self.api_key = os.getenv('CLAUDE_API_KEY')
        self.base_url = os.getenv('CLAUDE_BASE_URL', 'https://clubcdn.383338.xyz')
        self.model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')

    def ask(self, question: str) -> str:
        """直接问答 - 流式输出"""
        print(f"🤖 调用模型: {self.model}")

        url = f"{self.base_url}/v1/messages"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 1000,
            "stream": True
        }

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60, stream=True)
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line_text = line.decode('utf-8')
                if line_text.startswith('data: '):
                    data_text = line_text[6:]
                    if data_text.strip() == '[DONE]':
                        break
                    
                    data = json.loads(data_text)
                    if 'delta' in data and 'text' in data['delta']:
                        chunk_text = data['delta']['text']
                        print(chunk_text, end='', flush=True)
                        full_response += chunk_text
        
        print()  # 换行
        return full_response

def main():
    bot = SimpleClaude()

    if len(sys.argv) > 1:
        # 命令行模式
        question = " ".join(sys.argv[1:])
        bot.ask(question)
    else:
        # 交互模式
        print("简单Claude问答 (输入quit退出)")
        while True:
            question = input("\n问题: ").strip()
            if question.lower() == 'quit':
                break
            if question:
                bot.ask(question)

if __name__ == "__main__":
    main()
