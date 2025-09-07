# -*- coding: utf-8 -*-
"""
RSI 相对强弱指数计算器
"""

import numpy as np
from typing import List, Optional


class RSI:
    """RSI计算器"""
    
    def __init__(self, period: int = 14):
        """
        初始化RSI计算器
        
        Args:
            period: RSI计算周期
        """
        self.period = period
    
    def calculate(self, prices: List[float]) -> List[Optional[float]]:
        """
        计算RSI值
        
        Args:
            prices: 价格列表（通常是收盘价）
            
        Returns:
            List[Optional[float]]: RSI值列表，前period-1个值为None
        """
        if len(prices) < self.period + 1:
            return [None] * len(prices)
        
        prices_array = np.array(prices)
        deltas = np.diff(prices_array)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # 计算初始平均增益和平均损失
        avg_gain = np.mean(gains[:self.period])
        avg_loss = np.mean(losses[:self.period])
        
        rsi_values = [None] * self.period
        
        # 计算第一个RSI值
        if avg_loss != 0:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 100
        rsi_values.append(rsi)
        
        # 计算后续RSI值
        for i in range(self.period + 1, len(prices)):
            gain = gains[i - 1] if i - 1 < len(gains) else 0
            loss = losses[i - 1] if i - 1 < len(losses) else 0
            
            # 使用EMA方式平滑
            avg_gain = ((avg_gain * (self.period - 1)) + gain) / self.period
            avg_loss = ((avg_loss * (self.period - 1)) + loss) / self.period
            
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100
            
            rsi_values.append(rsi)
        
        return rsi_values
    
    def get_latest(self, prices: List[float]) -> Optional[float]:
        """
        获取最新RSI值
        
        Args:
            prices: 价格列表
            
        Returns:
            Optional[float]: 最新RSI值
        """
        rsi_values = self.calculate(prices)
        return rsi_values[-1] if rsi_values else None
    
    def is_overbought(self, rsi_value: float, threshold: float = 70) -> bool:
        """
        判断是否超买
        
        Args:
            rsi_value: RSI值
            threshold: 超买阈值
            
        Returns:
            bool: 是否超买
        """
        return rsi_value > threshold
    
    def is_oversold(self, rsi_value: float, threshold: float = 30) -> bool:
        """
        判断是否超卖
        
        Args:
            rsi_value: RSI值
            threshold: 超卖阈值
            
        Returns:
            bool: 是否超卖
        """
        return rsi_value < threshold