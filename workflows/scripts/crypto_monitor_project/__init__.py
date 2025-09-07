# -*- coding: utf-8 -*-
"""
加密货币监控系统 - 模块化版本
重构版本，将原单体文件拆分为多个专业模块
"""

from .config import ConfigManager, Settings
from .database import DatabaseManager, MarketData, AnalysisRecord, TriggerEvent
from .data import DataCollector, BinanceClient, CoinGeckoClient
from .core import IndicatorCalculator, RSI, MACD, MovingAverage, MasterBrain
from .trading import TradingClient, PortfolioManager
from .integrations import TelegramIntegration
from .crypto_monitor_controller import CryptoMonitorController

__version__ = "2.0.0"
__author__ = "Crypto Monitor Team"

__all__ = [
    # 配置管理
    'ConfigManager', 'Settings',
    
    # 数据库
    'DatabaseManager', 'MarketData', 'AnalysisRecord', 'TriggerEvent',
    
    # 数据采集
    'DataCollector', 'BinanceClient', 'CoinGeckoClient',
    
    # 技术指标与智能主脑
    'IndicatorCalculator', 'RSI', 'MACD', 'MovingAverage', 'MasterBrain',
    
    # 交易管理
    'TradingClient', 'PortfolioManager',
    
    # 外部集成
    'TelegramIntegration',
    
    # 主控制器
    'CryptoMonitorController'
]