# -*- coding: utf-8 -*-
"""
加密货币分析机器人 - 结合Binance数据和Claude AI分析

更新日志:
- 2025-09-01: 重构市场情绪分析，使用CoinGecko全球市场数据和恐贪指数替代NFT数据
  * 集成Alternative.me恐贪指数API，直接获取市场心理状态指标
  * 获取CoinGecko全球市场数据(总市值、交易量、BTC/ETH主导率、市值变化)
  * 添加热门搜索趋势分析，反映用户兴趣和投资情绪
  * 获取主流币种详细表现数据，提供更准确的市场情绪评估
- 2025-09-01: 新增交易员代理，制定具体交易策略(观望/多空/仓位/杠杆/止损止盈)
- 2025-09-01: 优化流式输出，实现打字机效果(10ms逐字符输出)，去除重复的完整结果打印
- 2025-09-01: 修复LLM调用问题，优化流式输出处理和错误处理机制
- 2025-09-01: 实现多代理架构分析系统，包含5个专业代理：
  * 技术分析师：K线数据+技术指标分析(RSI、MACD、均线)
  * 市场分析师：全球市场数据+恐贪指数+搜索趋势分析
  * 基本面分析师：市场数据+基本面分析
  * 首席分析师：整合所有代理报告，提供综合建议
  * 交易员：制定具体交易策略(1000美金本金，最高100倍杠杆)
- 2025-09-01: 恢复K线数据LLM分析功能，新增RSI、MACD技术指标计算
- 2025-09-01: 优化流式输出和错误处理
- 2025-09-01: 增加代币名快捷分析功能
"""

import requests
import json
import sys
import io
import os
import time
import threading
import logging
import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime, timedelta
from scipy.signal import find_peaks

try:
    from binance.client import Client
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    print("⚠️ 未安装python-binance库，交易功能将不可用")

try:
    import tensorflow as tf
    from sklearn.preprocessing import MinMaxScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("⚠️ 未安装机器学习库，预测功能将不可用")

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

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('crypto_bot.log'),
        logging.StreamHandler()
    ]
)

class CryptoBot:
    def __init__(self):
        # Claude API配置
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        self.claude_base_url = os.getenv('CLAUDE_BASE_URL', 'https://clubcdn.383338.xyz')
        self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')

        # CoinGecko API配置
        self.coingecko_api_key = "CG-SJ8bSJ7VmR2KH16w3UtgcYPa"
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"

        # Binance API配置
        self.binance_api_key = os.getenv('BINANCE_API_KEY')
        self.binance_api_secret = os.getenv('BINANCE_API_SECRET')
        self.binance_testnet = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
        self.binance_client = None

        # 初始化Binance客户端
        self._init_binance_client()

        print("🚀 加密货币分析机器人已启动")

    def _init_binance_client(self):
        """初始化Binance客户端"""
        if not BINANCE_AVAILABLE:
            print("⚠️ Binance功能不可用：请安装python-binance库")
            return

        if not self.binance_api_key or not self.binance_api_secret:
            print("⚠️ Binance功能不可用：未配置API密钥")
            return

        try:
            self.binance_client = Client(
                self.binance_api_key,
                self.binance_api_secret,
                testnet=self.binance_testnet
            )
            # 测试连接
            self.binance_client.ping()
            print("✅ Binance客户端初始化成功")
        except Exception as e:
            print(f"❌ Binance客户端初始化失败: {e}")
            self.binance_client = None

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

    def get_trending_coins(self):
        """获取热门币种信息"""
        try:
            # CoinGecko API v3 热门币种端点
            url = f"{self.coingecko_base_url}/search/trending"
            headers = {
                "x_cg_demo_api_key": self.coingecko_api_key
            }

            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                trending_data = response.json()
                print(f"✅ 成功获取热门币种数据")

                trending_summary = "🔥 热门币种:\n"

                # 热门搜索币种
                if 'coins' in trending_data:
                    trending_summary += "\n📈 热门搜索:\n"
                    for i, coin in enumerate(trending_data['coins'][:5], 1):
                        item = coin.get('item', {})
                        name = item.get('name', '未知')
                        symbol = item.get('symbol', '未知')
                        rank = item.get('market_cap_rank', 'N/A')
                        trending_summary += f"{i}. {name} ({symbol.upper()}) - 市值排名: {rank}\n"

                # 热门NFT
                if 'nfts' in trending_data and trending_data['nfts']:
                    trending_summary += "\n🎨 热门NFT:\n"
                    for i, nft in enumerate(trending_data['nfts'][:3], 1):
                        name = nft.get('name', '未知')
                        trending_summary += f"{i}. {name}\n"

                print(trending_summary)
                return trending_summary
            else:
                print(f"❌ 热门币种API返回错误: {response.status_code}")
                return ""

        except Exception as e:
            print(f"❌ 获取热门币种失败: {e}")
            return ""

    def _call_claude_api(self, prompt: str, agent_name: str) -> str:
        """调用Claude API的通用方法"""
        print(f"🤖 [{agent_name}] 调用模型: {self.claude_model}")

        if not self.claude_api_key:
            error_msg = f"❌ [{agent_name}] 未配置Claude API密钥"
            print(error_msg)
            return error_msg

        url = f"{self.claude_base_url}/v1/messages"
        payload = {
            "model": self.claude_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "stream": True
        }

        headers = {
            "x-api-key": self.claude_api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60, stream=True)

            if response.status_code != 200:
                error_msg = f"❌ [{agent_name}] API请求失败: {response.status_code} - {response.text}"
                print(error_msg)
                return error_msg

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
                                        # 打字机效果：逐字符输出
                                        for char in chunk_text:
                                            print(char, end='', flush=True)
                                            time.sleep(0.01)  # 10ms延迟，打字机效果
                                        full_response += chunk_text
                                elif data.get('type') == 'content_block_start':
                                    continue
                                elif data.get('type') == 'message_start':
                                    continue
                            except json.JSONDecodeError:
                                continue
                            except Exception as e:
                                print(f"⚠️ [{agent_name}] 处理数据错误: {e}")
                                continue

            print()  # 换行

            if not full_response.strip():
                error_msg = f"❌ [{agent_name}] 未收到有效响应内容"
                print(error_msg)
                return error_msg

            return full_response.strip()

        except requests.exceptions.Timeout:
            error_msg = f"❌ [{agent_name}] 请求超时"
            print(error_msg)
            return error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"❌ [{agent_name}] 网络请求错误: {e}"
            print(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"❌ [{agent_name}] 未知错误: {e}"
            print(error_msg)
            return error_msg

    def analyze_kline_data(self, symbol="BTCUSDT", interval='15m', limit=100) -> str:
        """K线数据技术分析代理"""
        # 获取K线数据
        kline_data = self.get_crypto_data(symbol, interval, limit)
        if not kline_data:
            error_msg = f"❌ [技术分析师] 无法获取{symbol}的K线数据"
            print(error_msg)
            return error_msg

        try:
            # 准备技术分析数据
            df = pd.DataFrame(kline_data)

            # 确保有足够的数据进行计算
            if len(df) < 50:
                limit = 100  # 增加数据量
                kline_data = self.get_crypto_data(symbol, interval, limit)
                df = pd.DataFrame(kline_data)

            # 计算技术指标
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['rsi'] = self._calculate_rsi(df['close'])
            df['macd'], df['macd_signal'] = self._calculate_macd(df['close'])

            # 获取最近10个有效数据点
            recent_data = df.dropna().tail(10)
            if recent_data.empty:
                error_msg = f"❌ [技术分析师] 计算技术指标失败，数据不足"
                print(error_msg)
                return error_msg

            # 转换为字典格式，处理NaN值
            recent_dict = []
            for _, row in recent_data.iterrows():
                row_dict = {}
                for col in row.index:
                    value = row[col]
                    if pd.isna(value):
                        row_dict[col] = None
                    elif isinstance(value, (int, float)):
                        row_dict[col] = round(float(value), 4)
                    else:
                        row_dict[col] = value
                recent_dict.append(row_dict)

            # 构建技术分析prompt
            prompt = f"""
你是专业的技术分析师，请分析{symbol}的{interval}K线数据：

最近10个周期的技术指标数据：
时间戳(time)、开盘价(open)、最高价(high)、最低价(low)、收盘价(close)、成交量(volume)
20期简单移动平均线(sma_20)、50期简单移动平均线(sma_50)
相对强弱指数RSI(rsi)、MACD线(macd)、MACD信号线(macd_signal)

{json.dumps(recent_dict, indent=2, ensure_ascii=False)}

请提供：
1. 趋势分析（短期、中期）
2. 支撑阻力位识别
3. 技术指标解读（RSI、MACD、均线）
4. 交易建议（入场点位、止损止盈）

请保持简洁专业，重点关注15分钟级别的短期走势。
"""
            return self._call_claude_api(prompt, "技术分析师")

        except Exception as e:
            error_msg = f"❌ [技术分析师] 数据处理错误: {e}"
            print(error_msg)
            return error_msg

    def analyze_market_sentiment(self) -> str:
        """市场情绪分析代理 - 基于CoinGecko全球市场数据和恐贪指数分析整体市场情绪"""
        try:
            print("🔍 获取全球市场数据...")
            sentiment_data = {}

            # 1. 获取CoinGecko全球市场数据
            try:
                global_url = f"{self.coingecko_base_url}/global"
                headers = {"x_cg_demo_api_key": self.coingecko_api_key}
                response = requests.get(global_url, headers=headers, timeout=15)

                if response.status_code == 200:
                    global_data = response.json()
                    if 'data' in global_data:
                        data = global_data['data']
                        sentiment_data['global_market'] = {
                            'total_market_cap_usd': data.get('total_market_cap', {}).get('usd', 0),
                            'total_volume_24h_usd': data.get('total_volume', {}).get('usd', 0),
                            'market_cap_change_24h': data.get('market_cap_change_percentage_24h_usd', 0),
                            'btc_dominance': data.get('market_cap_percentage', {}).get('btc', 0),
                            'eth_dominance': data.get('market_cap_percentage', {}).get('eth', 0),
                            'active_cryptocurrencies': data.get('active_cryptocurrencies', 0)
                        }
                        print("✅ 获取全球市场数据成功")
                    else:
                        print("❌ 全球市场数据格式异常")
                else:
                    print(f"❌ 全球市场数据API返回错误: {response.status_code}")
            except Exception as e:
                print(f"❌ 获取全球市场数据失败: {e}")

            # 2. 获取热门搜索趋势（用户兴趣指标）
            try:
                trending_url = f"{self.coingecko_base_url}/search/trending"
                headers = {"x_cg_demo_api_key": self.coingecko_api_key}
                response = requests.get(trending_url, headers=headers, timeout=15)

                if response.status_code == 200:
                    trending_data = response.json()
                    if 'coins' in trending_data:
                        trending_coins = []
                        for coin in trending_data['coins'][:5]:
                            item = coin.get('item', {})
                            trending_coins.append({
                                'name': item.get('name', '未知'),
                                'symbol': item.get('symbol', '未知').upper(),
                                'market_cap_rank': item.get('market_cap_rank', 'N/A'),
                                'score': item.get('score', 0)
                            })
                        sentiment_data['trending_coins'] = trending_coins
                        print("✅ 获取热门搜索数据成功")
            except Exception as e:
                print(f"❌ 获取热门搜索数据失败: {e}")

            # 3. 获取恐贪指数（Alternative.me API）
            try:
                fng_url = "https://api.alternative.me/fng/"
                response = requests.get(fng_url, timeout=10)

                if response.status_code == 200:
                    fng_data = response.json()
                    if 'data' in fng_data and len(fng_data['data']) > 0:
                        latest_fng = fng_data['data'][0]
                        sentiment_data['fear_greed_index'] = {
                            'value': int(latest_fng.get('value', 0)),
                            'classification': latest_fng.get('value_classification', '未知'),
                            'timestamp': latest_fng.get('timestamp', '未知'),
                            'time_until_update': latest_fng.get('time_until_update', '未知')
                        }
                        print(f"✅ 获取恐贪指数成功: {sentiment_data['fear_greed_index']['value']} ({sentiment_data['fear_greed_index']['classification']})")
                    else:
                        print("❌ 恐贪指数数据格式异常")
                else:
                    print(f"❌ 恐贪指数API返回错误: {response.status_code}")
            except Exception as e:
                print(f"❌ 获取恐贪指数失败: {e}")

            # 4. 获取主流币种表现（作为补充数据）
            try:
                major_coins = ['bitcoin', 'ethereum', 'ripple', 'binancecoin', 'cardano', 'solana']
                market_url = f"{self.coingecko_base_url}/coins/markets"
                params = {
                    'vs_currency': 'usd',
                    'ids': ','.join(major_coins),
                    'order': 'market_cap_desc',
                    'per_page': 6,
                    'page': 1,
                    'sparkline': 'false',
                    'price_change_percentage': '24h'
                }
                headers = {"x_cg_demo_api_key": self.coingecko_api_key}
                response = requests.get(market_url, headers=headers, params=params, timeout=15)

                if response.status_code == 200:
                    coins_data = response.json()
                    if isinstance(coins_data, list) and len(coins_data) > 0:
                        major_performance = []
                        for coin in coins_data:
                            major_performance.append({
                                'name': coin.get('name', '未知'),
                                'symbol': coin.get('symbol', '未知').upper(),
                                'current_price': coin.get('current_price', 0),
                                'price_change_24h': coin.get('price_change_percentage_24h', 0),
                                'market_cap': coin.get('market_cap', 0),
                                'total_volume': coin.get('total_volume', 0)
                            })
                        sentiment_data['major_coins_performance'] = major_performance
                        print("✅ 获取主流币种表现数据成功")
                    else:
                        print("❌ 主流币种数据格式异常")
                else:
                    print(f"❌ 主流币种API返回错误: {response.status_code}")
            except Exception as e:
                print(f"❌ 获取主流币种表现失败: {e}")

            if not sentiment_data:
                return "❌ 无法获取任何市场情绪数据"

            # 构建综合市场情绪分析prompt
            prompt = f"""
你是专业的市场情绪分析师，请基于以下多维度数据分析当前加密货币市场情绪：

=== 全球市场数据 ===
{json.dumps(sentiment_data.get('global_market', {}), indent=2, ensure_ascii=False)}

=== 恐贪指数 ===
{json.dumps(sentiment_data.get('fear_greed_index', {}), indent=2, ensure_ascii=False)}

=== 热门搜索趋势 ===
{json.dumps(sentiment_data.get('trending_coins', []), indent=2, ensure_ascii=False)}

=== 主流币种表现 ===
{json.dumps(sentiment_data.get('major_coins_performance', []), indent=2, ensure_ascii=False)}

请基于以上数据分析：
1. 当前市场情绪状态（极度恐慌/恐慌/谨慎/中性/乐观/贪婪/极度贪婪）
2. 恐贪指数的含义和市场心理状态
3. BTC/ETH主导地位变化对情绪的影响
4. 热门搜索趋势反映的投资者兴趣
5. 全球市值变化和资金流向分析
6. 短期情绪变化预期和关键转折点

请提供客观专业的市场情绪评估，重点关注多个指标之间的相互验证。
"""
            return self._call_claude_api(prompt, "市场分析师")

        except Exception as e:
            error_msg = f"❌ [市场分析师] 情绪分析失败: {e}"
            print(error_msg)
            return error_msg

    def analyze_fundamental_data(self, symbol="BTCUSDT") -> str:
        """基本面分析代理"""
        # 获取基本市场数据
        market_data = self.get_market_summary(symbol)

        prompt = f"""
你是基本面分析专家，请基于以下市场数据进行基本面分析：

{market_data}

请分析：
1. 价格走势的基本面逻辑
2. 交易量变化的意义
3. 市值排名变化趋势
4. 长期投资价值评估

保持理性客观的分析视角。
"""
        return self._call_claude_api(prompt, "基本面分析师")

    def _calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        exp1 = prices.ewm(span=fast).mean()
        exp2 = prices.ewm(span=slow).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=signal).mean()
        return macd, macd_signal

    def ask_claude_with_data(self, question: str, symbol="BTCUSDT") -> str:
        """多代理架构分析 - 结合各个专业代理的分析结果"""
        print(f"🚀 启动多代理分析架构")
        print(f"📊 分析币种: {symbol}")
        print("="*80)

        # 代理1: K线技术分析
        print("📈 [技术分析师] 开始分析...")
        kline_analysis = self.analyze_kline_data(symbol)
        print("\n" + "="*80)

        # 代理2: 市场情绪分析
        print("🔥 [市场分析师] 开始分析...")
        sentiment_analysis = self.analyze_market_sentiment()
        print("\n" + "="*80)

        # 代理3: 基本面分析
        print("📊 [基本面分析师] 开始分析...")
        fundamental_analysis = self.analyze_fundamental_data(symbol)
        print("\n" + "="*80)

        # 代理4: 综合分析师 - 整合所有分析结果
        print("🎯 [首席分析师] 开始整合分析...")
        integration_prompt = f"""
你是首席分析师，请整合以下三个专业代理的分析报告，回答用户问题：

=== 技术分析师报告 ===
{kline_analysis}

=== 市场分析师报告 ===
{sentiment_analysis}

=== 基本面分析师报告 ===
{fundamental_analysis}

=== 用户问题 ===
{question}

请基于以上专业分析，提供综合性的见解和建议。注意平衡各方观点，给出客观专业的结论。
"""

        final_analysis = self._call_claude_api(integration_prompt, "首席分析师")
        print("\n" + "="*80)

        # 代理5: 交易员 - 做出具体交易决策
        print("💰 [交易员] 制定交易策略...")
        trading_prompt = f"""
你是专业交易员，基于以上所有分析师的报告，请制定具体的交易策略：

=== 综合分析报告 ===
{final_analysis}

=== 交易参数 ===
- 初始资金: 1000美金
- 最高杠杆: 100倍
- 交易标的: {symbol}

请提供：
1. 交易决策：观望/做多/做空
2. 入场点位（具体价格）
3. 仓位大小（占总资金百分比）
4. 杠杆倍数（1-100倍）
5. 止损位置
6. 止盈目标
7. 风险控制说明

请给出明确的交易计划，不要模糊建议。
"""

        trading_decision = self._call_claude_api(trading_prompt, "交易员")

        return trading_decision

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
