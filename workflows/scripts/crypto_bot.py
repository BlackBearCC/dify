# -*- coding: utf-8 -*-
"""
加密货币分析机器人 - 结合Binance数据和Claude AI分析
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
    current_dir = Path(__file__).parent
    env_paths = [
        current_dir / '.env',
        current_dir.parent.parent / '.env',
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
                        value = value.strip().strip('"\'')
                        os.environ[key] = value
            return True
    return False

# 加载环境变量
load_env_file()

class CryptoBot:
    def __init__(self):
        # Claude API配置
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        self.claude_base_url = os.getenv('CLAUDE_BASE_URL', 'https://clubcdn.383338.xyz')
        self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')
        print("🚀 加密货币分析机器人已启动")

    def get_crypto_data(self, symbol="BTCUSDT", interval='1h', limit=24):
        """获取加密货币实时数据"""
        # 尝试多个Binance API源
        api_sources = [
            f"https://api.binance.com/api/v3/klines",
            f"https://api.binance.us/api/v3/klines",
            f"https://api1.binance.com/api/v3/klines",
            f"https://api2.binance.com/api/v3/klines"
        ]

        for api_url in api_sources:
            try:
                params = {
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit
                }
                response = requests.get(api_url, params=params, timeout=15)

                if response.status_code == 200:
                    klines = response.json()
                    print(f"✅ 成功从 {api_url} 获取数据")

                    # 简单数据处理
                    data = []
                    for kline in klines:
                        data.append({
                            'time': int(kline[0]),
                            'open': float(kline[1]),
                            'high': float(kline[2]),
                            'low': float(kline[3]),
                            'close': float(kline[4]),
                            'volume': float(kline[5])
                        })
                    return data
                else:
                    print(f"❌ API {api_url} 返回错误: {response.status_code}")

            except Exception as e:
                print(f"❌ API {api_url} 连接失败: {e}")
                continue

        print("❌ 所有API源都无法访问，请检查网络连接")
        return None

    def get_market_summary(self, symbol="BTCUSDT"):
        """获取市场概要信息"""
        data = self.get_crypto_data(symbol, interval='1h', limit=24)
        if data is None or len(data) == 0:
            return "❌ 无法获取市场数据，请检查网络连接"

        current_price = data[-1]['close']
        price_24h_ago = data[0]['close']
        change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100

        high_24h = max([candle['high'] for candle in data])
        low_24h = min([candle['low'] for candle in data])
        volume_24h = sum([candle['volume'] for candle in data])

        # 计算简单移动平均
        recent_closes = [candle['close'] for candle in data]
        sma_10 = sum(recent_closes[-10:]) / min(10, len(recent_closes))
        sma_20 = sum(recent_closes[-20:]) / min(20, len(recent_closes))

        summary = f"""📈 {symbol} 市场数据摘要:
💰 当前价格: ${current_price:,.2f}
📊 24h变化: {change_24h:+.2f}%
🔺 24h最高: ${high_24h:,.2f}
🔻 24h最低: ${low_24h:,.2f}
📦 24h交易量: {volume_24h:,.0f}
📉 10期均线: ${sma_10:,.2f}
📉 20期均线: ${sma_20:,.2f}"""
        print(summary)
        return summary

    def ask_claude_with_data(self, question: str, symbol="BTCUSDT") -> str:
        """结合市场数据询问Claude"""
        # 获取市场数据
        market_data = self.get_market_summary(symbol)

        # 构建包含数据的prompt
        enhanced_question = f"""
作为加密货币分析专家，请基于以下最新市场数据回答问题：

{market_data}

用户问题: {question}

请提供专业的分析和见解。
"""

        print(f"🤖 调用模型: {self.claude_model}")
        print(f"📊 分析币种: {symbol}")

        url = f"{self.claude_base_url}/v1/messages"
        payload = {
            "model": self.claude_model,
            "messages": [{"role": "user", "content": enhanced_question}],
            "max_tokens": 1000,
            "stream": True
        }

        headers = {
            "x-api-key": self.claude_api_key,
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60, stream=True)

        full_response = ""
        buffer = ""

        for chunk in response:
            if chunk:
                buffer += chunk.decode('utf-8', errors='ignore')

                # 处理完整的行
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()

                    if line.startswith('data: '):
                        data_text = line[6:]
                        if data_text.strip() == '[DONE]':
                            break

                        try:
                            data = json.loads(data_text)
                            if data.get('type') == 'content_block_delta':
                                if 'delta' in data and data['delta'].get('type') == 'text_delta':
                                    chunk_text = data['delta']['text']
                                    print(chunk_text, end='', flush=True)
                                    full_response += chunk_text
                        except json.JSONDecodeError:
                            continue

        print()
        return full_response

def main():
    bot = CryptoBot()

    if len(sys.argv) > 1:
        # 命令行模式
        if len(sys.argv) == 2:
            # 只有一个参数，检查是否是代币名
            token = sys.argv[1].upper()
            if token in ['BTC', 'ETH', 'XRP', 'BNB', 'ADA', 'SOL', 'DOGE', 'MATIC', 'DOT', 'AVAX', 'SHIB', 'LTC', 'UNI', 'LINK', 'TRX']:
                symbol = token + 'USDT'
                question = f"{token}日内走势如何？15分钟走势分析"
                bot.ask_claude_with_data(question, symbol)
            else:
                question = sys.argv[1]
                bot.ask_claude_with_data(question)
        else:
            # 多个参数
            question = " ".join(sys.argv[1:])
            # 检查是否指定了特定币种
            if len(sys.argv) > 2 and sys.argv[1].upper().endswith('USDT'):
                symbol = sys.argv[1].upper()
                question = " ".join(sys.argv[2:])
                bot.ask_claude_with_data(question, symbol)
            else:
                bot.ask_claude_with_data(question)
    else:
        # 交互模式
        print("🚀 加密货币分析机器人 (输入quit退出)")
        print("💡 用法示例:")
        print("   - 输入代币名: 'BTC' 或 'ETH' (自动分析日内和15分钟走势)")
        print("   - 指定交易对: 'ETHUSDT 以太坊今天走势如何?'")
        print("   - 直接提问: '比特币适合长期持有吗?'")

        while True:
            user_input = input("\n❓ 问题: ").strip()
            if user_input.lower() == 'quit':
                break
            if user_input:
                # 解析输入，检查是否包含币种
                parts = user_input.split(' ', 1)

                # 检查是否是单独的代币名（如 BTC, ETH等）
                if len(parts) == 1 and parts[0].upper() in ['BTC', 'ETH', 'XRP', 'BNB', 'ADA', 'SOL', 'DOGE', 'MATIC', 'DOT', 'AVAX', 'SHIB', 'LTC', 'UNI', 'LINK', 'TRX']:
                    symbol = parts[0].upper() + 'USDT'
                    question = f"{parts[0].upper()}日内走势如何？15分钟走势分析"
                    bot.ask_claude_with_data(question, symbol)
                elif len(parts) > 1 and parts[0].upper().endswith('USDT'):
                    # 指定了完整交易对
                    symbol = parts[0].upper()
                    question = parts[1]
                    bot.ask_claude_with_data(question, symbol)
                else:
                    # 普通问题，使用默认币种
                    bot.ask_claude_with_data(user_input)

if __name__ == "__main__":
    main()
