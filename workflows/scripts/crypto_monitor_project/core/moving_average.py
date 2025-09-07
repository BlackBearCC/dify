# -*- coding: utf-8 -*-
"""
移动平均线计算器
"""

import numpy as np
from typing import List, Optional


class MovingAverage:
    """移动平均线计算器"""
    
    def __init__(self):
        """初始化移动平均线计算器"""
        pass
    
    def sma(self, prices: List[float], period: int) -> List[Optional[float]]:
        """
        计算简单移动平均线(SMA)
        
        Args:
            prices: 价格列表
            period: 周期
            
        Returns:
            List[Optional[float]]: SMA值列表
        """
        if len(prices) < period:
            return [None] * len(prices)
        
        sma_values = [None] * (period - 1)
        
        for i in range(period - 1, len(prices)):
            sma = np.mean(prices[i - period + 1:i + 1])
            sma_values.append(sma)
        
        return sma_values
    
    def ema(self, prices: List[float], period: int) -> List[Optional[float]]:
        """
        计算指数移动平均线(EMA)
        
        Args:
            prices: 价格列表
            period: 周期
            
        Returns:
            List[Optional[float]]: EMA值列表
        """
        if len(prices) < period:
            return [None] * len(prices)
        
        ema_values = [None] * (period - 1)
        
        # 第一个EMA值使用SMA
        first_ema = np.mean(prices[:period])
        ema_values.append(first_ema)
        
        # 计算平滑因子
        multiplier = 2 / (period + 1)
        
        # 计算后续EMA值
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)
        
        return ema_values
    
    def get_latest_sma(self, prices: List[float], period: int) -> Optional[float]:
        """
        获取最新SMA值
        
        Args:
            prices: 价格列表
            period: 周期
            
        Returns:
            Optional[float]: 最新SMA值
        """
        sma_values = self.sma(prices, period)
        return sma_values[-1] if sma_values else None
    
    def get_latest_ema(self, prices: List[float], period: int) -> Optional[float]:
        """
        获取最新EMA值
        
        Args:
            prices: 价格列表
            period: 周期
            
        Returns:
            Optional[float]: 最新EMA值
        """
        ema_values = self.ema(prices, period)
        return ema_values[-1] if ema_values else None
    
    def is_price_above_ma(self, current_price: float, ma_value: Optional[float]) -> bool:
        """
        判断价格是否高于移动平均线
        
        Args:
            current_price: 当前价格
            ma_value: 移动平均线值
            
        Returns:
            bool: 价格是否高于MA
        """
        return ma_value is not None and current_price > ma_value
    
    def is_golden_cross(self, short_ma: List[Optional[float]], long_ma: List[Optional[float]]) -> bool:
        """
        判断是否为金叉（短期MA上穿长期MA）
        
        Args:
            short_ma: 短期移动平均线
            long_ma: 长期移动平均线
            
        Returns:
            bool: 是否为金叉
        """
        if len(short_ma) < 2 or len(long_ma) < 2:
            return False
        
        # 检查最近两个点
        curr_short, curr_long = short_ma[-1], long_ma[-1]
        prev_short, prev_long = short_ma[-2], long_ma[-2]
        
        if all(x is not None for x in [curr_short, curr_long, prev_short, prev_long]):
            return prev_short <= prev_long and curr_short > curr_long
        
        return False
    
    def is_death_cross(self, short_ma: List[Optional[float]], long_ma: List[Optional[float]]) -> bool:
        """
        判断是否为死叉（短期MA下穿长期MA）
        
        Args:
            short_ma: 短期移动平均线
            long_ma: 长期移动平均线
            
        Returns:
            bool: 是否为死叉
        """
        if len(short_ma) < 2 or len(long_ma) < 2:
            return False
        
        # 检查最近两个点
        curr_short, curr_long = short_ma[-1], long_ma[-1]
        prev_short, prev_long = short_ma[-2], long_ma[-2]
        
        if all(x is not None for x in [curr_short, curr_long, prev_short, prev_long]):
            return prev_short >= prev_long and curr_short < curr_long
        
        return False