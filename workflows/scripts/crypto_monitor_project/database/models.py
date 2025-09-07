# -*- coding: utf-8 -*-
"""
数据模型定义
定义数据库中使用的数据结构
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class MarketData:
    """市场数据模型"""
    symbol: str
    timestamp: int
    price: float
    rsi: Optional[float] = None
    macd: Optional[float] = None
    volume: float = 0.0
    ma_20: Optional[float] = None
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None


@dataclass
class AnalysisRecord:
    """分析记录模型"""
    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    data_type: str = ""
    agent_name: str = ""
    symbol: str = ""
    content: str = ""
    summary: str = ""
    status: str = "pending"
    metadata: Optional[str] = None


@dataclass
class TriggerEvent:
    """触发事件模型"""
    id: Optional[str] = None
    symbol: str = ""
    event_type: str = ""
    timestamp: Optional[datetime] = None
    data: Optional[str] = None
    status: str = "pending"