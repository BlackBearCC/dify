# -*- coding: utf-8 -*-
"""
数据收集器
统一管理所有数据源的数据采集
"""

import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from .binance_client import BinanceClient
from .coingecko_client import CoinGeckoClient
from .financial_data_client import FinancialDataClient
from ..config import Settings
from ..database import DatabaseManager, MarketData


class DataCollector:
    """数据收集器"""
    
    def __init__(self, settings: Settings, db_manager: DatabaseManager):
        """
        初始化数据收集器
        
        Args:
            settings: 系统配置对象
            db_manager: 数据库管理器
        """
        self.settings = settings
        self.db_manager = db_manager
        self.binance_client = BinanceClient(settings)
        self.coingecko_client = CoinGeckoClient(settings)
        self.financial_data_client = FinancialDataClient(settings)
        
        # 数据缓存
        self.kline_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.last_fetch_time: Dict[str, float] = {}
    
    def collect_kline_data(self, symbols: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        收集K线数据
        
        Args:
            symbols: 交易对符号列表
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: 各币种的K线数据
        """
        results = {}
        current_time = time.time()
        
        for symbol in symbols:
            # 检查是否需要刷新缓存
            last_fetch = self.last_fetch_time.get(symbol, 0)
            if current_time - last_fetch >= self.settings.kline.fetch_interval:
                print(f"🔄 获取 {symbol.replace('USDT', '')} K线数据...", end='', flush=True)
                
                klines = self.binance_client.get_kline_data(
                    symbol=symbol,
                    interval=self.settings.kline.default_period,
                    limit=self.settings.kline.history_length
                )
                
                if klines:
                    self.kline_cache[symbol] = klines
                    self.last_fetch_time[symbol] = current_time
                    print(" ✅", flush=True)
                else:
                    print(" ❌", flush=True)
            
            # 返回缓存的数据
            results[symbol] = self.kline_cache.get(symbol, [])
        
        return results
    
    def collect_market_stats(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        收集市场统计数据
        
        Args:
            symbols: 交易对符号列表
            
        Returns:
            Dict[str, Optional[Dict[str, Any]]]: 各币种的市场统计数据
        """
        results = {}
        
        for symbol in symbols:
            stats = self.binance_client.get_24hr_stats(symbol)
            results[symbol] = stats
            
            if stats:
                print(f"📊 {symbol.replace('USDT', '')}: ${stats['last_price']:.4f} ({stats['price_change_percent']:+.2f}%)")
        
        return results
    
    def collect_global_market_data(self) -> Optional[Dict[str, Any]]:
        """
        收集全球市场数据
        
        Returns:
            Optional[Dict[str, Any]]: 全球市场数据
        """
        print("🌍 获取全球市场数据...")
        return self.coingecko_client.get_global_market_data()
    
    def collect_trending_data(self) -> Optional[List[Dict[str, Any]]]:
        """
        收集热门币种数据
        
        Returns:
            Optional[List[Dict[str, Any]]]: 热门币种数据
        """
        print("🔥 获取热门币种数据...")
        return self.coingecko_client.get_trending_coins()
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        获取当前价格
        
        Args:
            symbol: 交易对符号
            
        Returns:
            Optional[float]: 当前价格
        """
        return self.binance_client.get_ticker_price(symbol)
    
    def save_market_data_to_db(self, symbol: str, market_data: MarketData) -> bool:
        """
        保存市场数据到数据库
        
        Args:
            symbol: 交易对符号
            market_data: 市场数据对象
            
        Returns:
            bool: 保存是否成功
        """
        return self.db_manager.save_market_data(market_data)
    
    def get_latest_kline_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取最新的K线数据
        
        Args:
            symbol: 交易对符号
            
        Returns:
            Optional[Dict[str, Any]]: 最新K线数据
        """
        klines = self.kline_cache.get(symbol, [])
        return klines[0] if klines else None
    
    def collect_comprehensive_macro_data(self) -> Optional[Dict[str, Any]]:
        """
        收集完整宏观数据：ETF资金流向、美股指数、黄金价格
        
        Returns:
            Optional[Dict[str, Any]]: 完整宏观数据
        """
        print("🌍 [数据收集器] 收集完整宏观经济数据...")
        return self.financial_data_client.get_comprehensive_macro_data()
    
    def collect_bitcoin_etf_flows(self) -> Optional[Dict[str, Any]]:
        """收集比特币ETF资金流向数据"""
        return self.financial_data_client.get_bitcoin_etf_flows()
    
    def collect_us_stock_indices(self) -> Optional[Dict[str, Any]]:
        """收集美股主要指数数据"""
        return self.financial_data_client.get_us_stock_indices()
    
    def collect_gold_price_data(self) -> Optional[Dict[str, Any]]:
        """收集黄金价格数据"""
        return self.financial_data_client.get_gold_price_data()
    
    def test_all_connections(self) -> Dict[str, bool]:
        """
        测试所有数据源连接
        
        Returns:
            Dict[str, bool]: 各数据源的连接状态
        """
        print("🔍 测试数据源连接...")
        
        # 测试基础数据源
        results = {
            'binance': self.binance_client.test_connectivity(),
            'coingecko': self.coingecko_client.test_connectivity()
        }
        
        # 测试金融数据源
        financial_results = self.financial_data_client.test_connectivity()
        results.update(financial_results)
        
        for source, status in results.items():
            status_text = "✅ 正常" if status else "❌ 异常"
            print(f"  {source.title()}: {status_text}")
        
        return results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        return {
            'cached_symbols': list(self.kline_cache.keys()),
            'cache_count': len(self.kline_cache),
            'last_fetch_times': dict(self.last_fetch_time)
        }
    
    def clear_cache(self, symbol: Optional[str] = None):
        """
        清理缓存
        
        Args:
            symbol: 要清理的交易对符号，为None时清理所有缓存
        """
        if symbol:
            self.kline_cache.pop(symbol, None)
            self.last_fetch_time.pop(symbol, None)
            print(f"🧹 已清理 {symbol} 缓存")
        else:
            self.kline_cache.clear()
            self.last_fetch_time.clear()
            print("🧹 已清理所有缓存")