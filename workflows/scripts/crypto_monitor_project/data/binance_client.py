# -*- coding: utf-8 -*-
"""
币安API客户端
负责从币安获取K线和市场数据
"""

import os
import requests
from typing import List, Dict, Any, Optional

try:
    from ..config import Settings
except ImportError:
    from config.settings import Settings


class BinanceClient:
    """币安API客户端 - 使用直接requests调用以提高稳定性"""
    
    def __init__(self, settings: Settings):
        """初始化币安客户端"""
        self.settings = settings
        
        # API密钥配置（公开数据不需要API key）
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET') 
        self.testnet = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
        
        # 多API端点容错机制 - 来自成功运行的crypto_bot.py
        self.api_endpoints = [
            "https://api.binance.com/api/v3",
            "https://api.binance.us/api/v3",
            "https://api1.binance.com/api/v3", 
            "https://api2.binance.com/api/v3"
        ]
        
        # 测试连接找到可用端点
        self.working_endpoint = None
        self._find_working_endpoint()
        
        if not self.working_endpoint:
            print("❌ 所有Binance端点均连接失败")
            raise Exception("无法连接到任何Binance API端点")
    
    def _find_working_endpoint(self):
        """寻找可用的API端点"""
        for endpoint in self.api_endpoints:
            try:
                # 使用简单的ping测试端点
                response = requests.get(f"{endpoint}/ping", timeout=15)
                if response.status_code == 200:
                    self.working_endpoint = endpoint
                    print(f"✅ 币安客户端初始化成功 - 使用端点: {endpoint}")
                    return
            except Exception as e:
                print(f"❌ {endpoint} 连接失败: {e}")
                continue
        
    def get_kline_data(self, symbol: str, interval: str = "15m", limit: int = 100) -> List[Dict[str, Any]]:
        """获取K线数据 - 使用requests直接调用"""
        if not self.working_endpoint:
            raise Exception("没有可用的API端点")
        
        # 尝试从可用端点获取数据，如果失败则尝试其他端点
        for endpoint in [self.working_endpoint] + [ep for ep in self.api_endpoints if ep != self.working_endpoint]:
            try:
                params = {
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit
                }
                response = requests.get(f"{endpoint}/klines", params=params, timeout=15)
                if response.status_code == 200:
                    raw_klines = response.json()
                    print(f"✅ 成功从 {endpoint} 获取{symbol}数据")
                    
                    # 转换数据格式
                    klines = []
                    for item in raw_klines:
                        kline = {
                            'timestamp': int(item[0]),
                            'open': float(item[1]),
                            'high': float(item[2]),
                            'low': float(item[3]),
                            'close': float(item[4]),
                            'volume': float(item[5]),
                            'close_time': int(item[6]),
                            'quote_volume': float(item[7]),
                            'count': int(item[8])
                        }
                        klines.append(kline)
                    
                    # 更新工作端点
                    self.working_endpoint = endpoint
                    return klines
                    
            except Exception as e:
                print(f"❌ API {endpoint}/klines 连接失败: {e}")
                continue
        
        raise Exception("所有API端点均无法获取K线数据")
    
    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        if not self.working_endpoint:
            return None
            
        for endpoint in [self.working_endpoint] + [ep for ep in self.api_endpoints if ep != self.working_endpoint]:
            try:
                params = {'symbol': symbol}
                response = requests.get(f"{endpoint}/ticker/price", params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    self.working_endpoint = endpoint
                    return float(data['price'])
            except Exception as e:
                print(f"❌ 从{endpoint}获取{symbol}价格失败: {e}")
                continue
        
        print(f"❌ 获取{symbol}价格失败：所有端点均不可用")
        return None
    
    def get_24hr_stats(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取24小时统计数据"""
        if not self.working_endpoint:
            return None
            
        for endpoint in [self.working_endpoint] + [ep for ep in self.api_endpoints if ep != self.working_endpoint]:
            try:
                params = {'symbol': symbol}
                response = requests.get(f"{endpoint}/ticker/24hr", params=params, timeout=15)
                if response.status_code == 200:
                    ticker = response.json()
                    self.working_endpoint = endpoint
                    return {
                        'symbol': ticker['symbol'],
                        'price_change': float(ticker['priceChange']),
                        'price_change_percent': float(ticker['priceChangePercent']),
                        'weighted_avg_price': float(ticker['weightedAvgPrice']),
                        'prev_close_price': float(ticker['prevClosePrice']),
                        'last_price': float(ticker['lastPrice']),
                        'bid_price': float(ticker['bidPrice']),
                        'ask_price': float(ticker['askPrice']),
                        'open_price': float(ticker['openPrice']),
                        'high_price': float(ticker['highPrice']),
                        'low_price': float(ticker['lowPrice']),
                        'volume': float(ticker['volume']),
                        'quote_volume': float(ticker['quoteVolume']),
                        'open_time': int(ticker['openTime']),
                        'close_time': int(ticker['closeTime']),
                        'count': int(ticker['count'])
                    }
            except Exception as e:
                print(f"❌ 从{endpoint}获取{symbol} 24小时统计失败: {e}")
                continue
                
        print(f"❌ 获取{symbol} 24小时统计失败：所有端点均不可用")
        return None
    
    def get_orderbook(self, symbol: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """获取订单簿数据"""
        if not self.working_endpoint:
            return None
            
        for endpoint in [self.working_endpoint] + [ep for ep in self.api_endpoints if ep != self.working_endpoint]:
            try:
                params = {'symbol': symbol, 'limit': limit}
                response = requests.get(f"{endpoint}/depth", params=params, timeout=15)
                if response.status_code == 200:
                    orderbook = response.json()
                    self.working_endpoint = endpoint
                    return {
                        'last_update_id': orderbook['lastUpdateId'],
                        'bids': [[float(price), float(qty)] for price, qty in orderbook['bids']],
                        'asks': [[float(price), float(qty)] for price, qty in orderbook['asks']]
                    }
            except Exception as e:
                print(f"❌ 从{endpoint}获取{symbol}订单簿失败: {e}")
                continue
                
        print(f"❌ 获取{symbol}订单簿失败：所有端点均不可用")
        return None
    
    def test_connectivity(self) -> bool:
        """测试API连通性"""
        if not self.working_endpoint:
            return False
            
        try:
            response = requests.get(f"{self.working_endpoint}/ping", timeout=15)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ 币安API连接测试失败: {e}")
            return False