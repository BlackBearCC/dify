# -*- coding: utf-8 -*-
"""
MACD 指标计算器
"""

import numpy as np
from typing import List, Optional, Tuple


class MACD:
    """MACD计算器"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        初始化MACD计算器
        
        Args:
            fast_period: 快线EMA周期
            slow_period: 慢线EMA周期  
            signal_period: 信号线EMA周期
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def _calculate_ema(self, prices: List[float], period: int) -> List[Optional[float]]:
        """
        计算指数移动平均线
        
        Args:
            prices: 价格列表
            period: 周期
            
        Returns:
            List[Optional[float]]: EMA值列表
        """
        if len(prices) < period:
            return [None] * len(prices)
        
        ema_values = [None] * (period - 1)
        
        # 第一个EMA值使用简单平均
        first_ema = np.mean(prices[:period])
        ema_values.append(first_ema)
        
        # 计算平滑因子
        multiplier = 2 / (period + 1)
        
        # 计算后续EMA值
        for i in range(period, len(prices)):
            ema = (prices[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)
        
        return ema_values
    
    def calculate(self, prices: List[float]) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
        """
        计算MACD指标
        
        Args:
            prices: 价格列表
            
        Returns:
            Tuple: (MACD线, 信号线, 柱状图)
        """
        # 计算快线和慢线EMA
        fast_ema = self._calculate_ema(prices, self.fast_period)
        slow_ema = self._calculate_ema(prices, self.slow_period)
        
        # 计算MACD线
        macd_line = []
        for i in range(len(prices)):
            if fast_ema[i] is not None and slow_ema[i] is not None:
                macd_line.append(fast_ema[i] - slow_ema[i])
            else:
                macd_line.append(None)
        
        # 计算信号线（MACD线的EMA）
        macd_values_for_signal = [x for x in macd_line if x is not None]
        if len(macd_values_for_signal) >= self.signal_period:
            signal_ema = self._calculate_ema(macd_values_for_signal, self.signal_period)
            
            # 对齐信号线数组
            signal_line = [None] * (len(macd_line) - len(signal_ema)) + signal_ema
        else:
            signal_line = [None] * len(macd_line)
        
        # 计算柱状图
        histogram = []
        for i in range(len(macd_line)):
            if macd_line[i] is not None and signal_line[i] is not None:
                histogram.append(macd_line[i] - signal_line[i])
            else:
                histogram.append(None)
        
        return macd_line, signal_line, histogram
    
    def get_latest(self, prices: List[float]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        获取最新MACD值
        
        Args:
            prices: 价格列表
            
        Returns:
            Tuple: (最新MACD线, 最新信号线, 最新柱状图)
        """
        macd_line, signal_line, histogram = self.calculate(prices)
        
        return (
            macd_line[-1] if macd_line else None,
            signal_line[-1] if signal_line else None,
            histogram[-1] if histogram else None
        )
    
    def is_bullish_crossover(self, macd_line: List[Optional[float]], signal_line: List[Optional[float]]) -> bool:
        """
        判断是否为金叉（MACD线上穿信号线）
        
        Args:
            macd_line: MACD线数据
            signal_line: 信号线数据
            
        Returns:
            bool: 是否为金叉
        """
        if len(macd_line) < 2 or len(signal_line) < 2:
            return False
        
        # 检查最近两个点
        curr_macd, curr_signal = macd_line[-1], signal_line[-1]
        prev_macd, prev_signal = macd_line[-2], signal_line[-2]
        
        if all(x is not None for x in [curr_macd, curr_signal, prev_macd, prev_signal]):
            return prev_macd <= prev_signal and curr_macd > curr_signal
        
        return False
    
    def is_bearish_crossover(self, macd_line: List[Optional[float]], signal_line: List[Optional[float]]) -> bool:
        """
        判断是否为死叉（MACD线下穿信号线）
        
        Args:
            macd_line: MACD线数据
            signal_line: 信号线数据
            
        Returns:
            bool: 是否为死叉
        """
        if len(macd_line) < 2 or len(signal_line) < 2:
            return False
        
        # 检查最近两个点
        curr_macd, curr_signal = macd_line[-1], signal_line[-1]
        prev_macd, prev_signal = macd_line[-2], signal_line[-2]
        
        if all(x is not None for x in [curr_macd, curr_signal, prev_macd, prev_signal]):
            return prev_macd >= prev_signal and curr_macd < curr_signal
        
        return False