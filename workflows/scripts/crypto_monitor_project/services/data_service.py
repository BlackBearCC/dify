# -*- coding: utf-8 -*-
"""
数据服务 - 统一的数据收集和预处理接口
封装DataCollector，提供数据验证和预处理功能
"""

from typing import Dict, List, Any, Optional
from ..config import Settings
from ..database import DatabaseManager
from ..data import DataCollector


class DataService:
    """数据服务 - 单一职责：数据收集、验证和预处理"""
    
    def __init__(self, settings: Settings, db_manager: DatabaseManager):
        """
        初始化数据服务
        
        Args:
            settings: 系统配置
            db_manager: 数据库管理器
        """
        self.settings = settings
        self.db_manager = db_manager
        
        # 初始化数据收集器
        self.data_collector = DataCollector(settings, db_manager)
    
    def collect_kline_data(self, symbols: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        收集K线数据并进行验证
        
        Args:
            symbols: 币种列表
            
        Returns:
            Dict: 币种对应的K线数据
        """
        print(f"📊 收集K线数据: {', '.join([s.replace('USDT', '') for s in symbols])}")
        
        try:
            kline_data = self.data_collector.collect_kline_data(symbols)
            
            # 数据验证
            validated_data = {}
            for symbol, data in kline_data.items():
                if self._validate_kline_data(symbol, data):
                    validated_data[symbol] = data
                else:
                    print(f"⚠️ {symbol} K线数据验证失败")
            
            return validated_data
            
        except Exception as e:
            print(f"❌ 收集K线数据失败: {e}")
            return {}
    
    def _validate_kline_data(self, symbol: str, data: List[Dict[str, Any]]) -> bool:
        """
        验证K线数据的完整性和有效性
        
        Args:
            symbol: 币种符号
            data: K线数据列表
            
        Returns:
            bool: 数据是否有效
        """
        if not data:
            return False
        
        if len(data) < self.settings.kline.history_length:
            print(f"⚠️ {symbol} K线数据不足: {len(data)}/{self.settings.kline.history_length}")
            
        # 检查必要字段
        required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for item in data[-5:]:  # 检查最后5条数据
            for field in required_fields:
                if field not in item or item[field] is None:
                    print(f"❌ {symbol} K线数据缺失字段: {field}")
                    return False
        
        return True
    
    def collect_market_sentiment_data(self) -> Dict[str, Any]:
        """
        收集市场情绪相关数据
        
        Returns:
            Dict: 市场情绪数据
        """
        try:
            # 收集全局市场数据
            global_data = self.data_collector.collect_global_market_data()
            
            # 收集恐贪指数数据
            fear_greed_data = self.data_collector.collect_fear_greed_index()
            
            # 收集热门币种数据
            trending_data = self.data_collector.collect_trending_data()
            
            # 收集主流币种表现数据
            major_coins_performance = self.data_collector.collect_major_coins_performance()
            
            # 收集主要币种价格数据
            major_coins_data = self._collect_major_coins_data()
            
            return {
                'global_data': global_data,
                'fear_greed_index': fear_greed_data,
                'trending_data': trending_data,
                'major_coins_performance': major_coins_performance,
                'major_coins_data': major_coins_data,
                'timestamp': self._get_current_timestamp()
            }
            
        except Exception as e:
            print(f"❌ 收集市场情绪数据失败: {e}")
            return {}
    
    def _collect_major_coins_data(self) -> Dict[str, float]:
        """收集主要币种的当前价格数据"""
        major_symbols = (self.settings.monitor.primary_symbols or []) + (self.settings.monitor.secondary_symbols or [])
        prices = {}
        
        for symbol in major_symbols:
            try:
                price = self.data_collector.get_current_price(symbol)
                if price:
                    prices[symbol] = price
            except Exception as e:
                print(f"⚠️ 获取{symbol}价格失败: {e}")
        
        return prices
    
    def collect_comprehensive_macro_data(self) -> Dict[str, Any]:
        """
        收集完整的宏观数据
        
        Returns:
            Dict: 宏观数据
        """
        try:
            return self.data_collector.collect_comprehensive_macro_data()
        except Exception as e:
            print(f"❌ 收集宏观数据失败: {e}")
            return {}
    
    def collect_fundamental_data(self, symbol: str) -> Dict[str, Any]:
        """
        收集基本面数据
        
        Args:
            symbol: 币种符号
            
        Returns:
            Dict: 基本面数据
        """
        try:
            current_price = self.data_collector.get_current_price(symbol)
            stats = self.data_collector.binance_client.get_24hr_stats(symbol)
            
            fundamental_data = {
                'symbol': symbol,
                'current_price': current_price,
                'price_stats': stats,
                'timestamp': self._get_current_timestamp()
            }
            
            return fundamental_data
            
        except Exception as e:
            print(f"❌ 收集{symbol}基本面数据失败: {e}")
            return {}
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        获取币种当前价格
        
        Args:
            symbol: 币种符号
            
        Returns:
            Optional[float]: 当前价格
        """
        try:
            return self.data_collector.get_current_price(symbol)
        except Exception as e:
            print(f"❌ 获取{symbol}价格失败: {e}")
            return None
    
    def test_all_connections(self) -> Dict[str, bool]:
        """
        测试所有数据源连接
        
        Returns:
            Dict: 连接状态
        """
        return self.data_collector.test_all_connections()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict: 缓存统计
        """
        try:
            return self.data_collector.get_cache_stats()
        except Exception:
            return {}
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        标准化交易对符号 - 支持BTC -> BTCUSDT转换
        
        Args:
            symbol: 原始符号
            
        Returns:
            str: 标准化后的符号
        """
        symbol = symbol.upper().strip()
        
        # 如果已经是完整格式，直接返回
        if symbol.endswith('USDT'):
            return symbol
        
        # 如果是缩写格式，添加USDT后缀
        return f"{symbol}USDT"
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        验证币种符号是否在监控列表中
        
        Args:
            symbol: 币种符号
            
        Returns:
            bool: 是否有效
        """
        normalized_symbol = self.normalize_symbol(symbol)
        all_symbols = (self.settings.monitor.primary_symbols or []) + (self.settings.monitor.secondary_symbols or [])
        return normalized_symbol in all_symbols
    
    def get_available_symbols(self) -> List[str]:
        """
        获取可用的监控币种列表
        
        Returns:
            List[str]: 币种列表（简化格式，如BTC, ETH）
        """
        all_symbols = (self.settings.monitor.primary_symbols or []) + (self.settings.monitor.secondary_symbols or [])
        return [s.replace('USDT', '') for s in all_symbols]
    
    def _get_current_timestamp(self) -> int:
        """获取当前时间戳"""
        from datetime import datetime
        return int(datetime.now().timestamp())