# -*- coding: utf-8 -*-
"""
简化版Claude问答机器人 - 直接问答，无复杂处理
"""

import requests
import json
import sys
import io

# 设置控制台输出编码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class SimpleClaude:
    def __init__(self):
        self.api_key = "sk-3fVR10ti8431mVtlvzadAoWENLj9WvJerfcfdsDDH7pJWBu7"
        self.base_url = "https://clubcdn.383338.xyz"
        self.model = "claude-sonnet-4-20250514"

        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def ask(self, question: str) -> str:
        """直接问答"""
        print(f"🤖 调用模型: {self.model}")

        url = f"{self.base_url}/v1/messages"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 1000
        }

        # 尝试不同的认证方式
        auth_methods = [
            {"x-api-key": self.api_key, "Content-Type": "application/json"},
            {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            {"x-api-key": self.api_key, "Content-Type": "application/json", "User-Agent": "claude-code/1.0.88"}
        ]

        for i, headers in enumerate(auth_methods, 1):
            print(f"📡 尝试认证方式 {i}...")
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=60)

                if response.status_code == 200:
                    result = response.json()
                    if "content" in result and isinstance(result["content"], list):
                        return result["content"][0].get("text", "")
                    return result.get("content", "")
                else:
                    print(f"   状态码: {response.status_code}")

            except Exception as e:
                print(f"   失败: {str(e)}")
                continue

        return "所有认证方式都失败了"

def main():
    bot = SimpleClaude()

    if len(sys.argv) > 1:
        # 命令行模式
        question = " ".join(sys.argv[1:])
        answer = bot.ask(question)
        print(answer)
    else:
        # 交互模式
        print("简单Claude问答 (输入quit退出)")
        while True:
            question = input("\n问题: ").strip()
            if question.lower() == 'quit':
                break
            if question:
                answer = bot.ask(question)
                print(f"\n回答: {answer}")

if __name__ == "__main__":
    main()
