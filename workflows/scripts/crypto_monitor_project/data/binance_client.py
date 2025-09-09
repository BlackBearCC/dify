# -*- coding: utf-8 -*-
"""
币安API客户端
负责从币安获取K线和市场数据
"""

import os
from typing import List, Dict, Any, Optional
from binance.client import Client

from ..config import Settings


class BinanceClient:
    """币安API客户端"""
    
    def __init__(self, settings: Settings):
        """初始化币安客户端"""
        self.settings = settings
        
        # API密钥配置 - 公开数据不需要API key
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET') 
        testnet = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
        
        # 如果没有配置API密钥，使用公开客户端（仅限公开数据）
        if not api_key or not api_secret:
            print("⚠️ 未配置Binance API密钥，仅能获取公开市场数据")
            api_key = None
            api_secret = None
        
        # 多API端点容错机制
        self.api_endpoints = [
            "https://api.binance.com",
            "https://api.binance.us", 
            "https://api1.binance.com",
            "https://api2.binance.com"
        ]
        
        # 尝试初始化客户端
        self.client = None
        for endpoint in self.api_endpoints:
            try:
                print(f"🔍 尝试连接: {endpoint}")
                if testnet:
                    self.client = Client(api_key, api_secret, testnet=True, requests_params={'timeout': 60})
                else:
                    # 为不同端点创建客户端
                    self.client = Client(api_key, api_secret, testnet=False, requests_params={'timeout': 60})
                    # 修改base_url
                    self.client.API_URL = endpoint + '/api'
                    self.client.FUTURES_URL = endpoint + '/fapi'
                    
                # 测试连接
                self.client.ping()
                print(f"✅ 币安客户端初始化完成 - 使用端点: {endpoint}")
                break
                
            except Exception as e:
                print(f"❌ {endpoint} 连接失败: {e}")
                self.client = None
                continue
        
        if not self.client:
            print("❌ 所有Binance端点均连接失败")
            raise Exception("无法连接到任何Binance API端点")
        
    def get_kline_data(self, symbol: str, interval: str = "15m", limit: int = 100) -> List[Dict[str, Any]]:
        """获取K线数据"""
        raw_klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        
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
        
        return klines
    
    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            print(f"❌ 获取{symbol}价格失败: {e}")
            return None
    
    def get_24hr_stats(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取24小时统计数据"""
        try:
            ticker = self.client.get_ticker(symbol=symbol)
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
            print(f"❌ 获取{symbol} 24小时统计失败: {e}")
            return None
    
    def get_orderbook(self, symbol: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """获取订单簿数据"""
        try:
            orderbook = self.client.get_order_book(symbol=symbol, limit=limit)
            return {
                'last_update_id': orderbook['lastUpdateId'],
                'bids': [[float(price), float(qty)] for price, qty in orderbook['bids']],
                'asks': [[float(price), float(qty)] for price, qty in orderbook['asks']]
            }
        except Exception as e:
            print(f"❌ 获取{symbol}订单簿失败: {e}")
            return None
    
    def test_connectivity(self) -> bool:
        """测试API连通性"""
        try:
            self.client.ping()
            return True
        except Exception as e:
            print(f"❌ 币安API连接测试失败: {e}")
            return False