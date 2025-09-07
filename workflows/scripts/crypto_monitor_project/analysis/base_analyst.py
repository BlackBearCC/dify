# -*- coding: utf-8 -*-
"""
基础分析师类
定义所有分析师的通用接口和方法
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from ..config import Settings, ModelConfig


class BaseAnalyst(ABC):
    """基础分析师抽象类"""
    
    def __init__(self, name: str, model_config: ModelConfig, settings: Settings):
        """
        初始化基础分析师
        
        Args:
            name: 分析师名称
            model_config: 模型配置
            settings: 系统配置
        """
        self.name = name
        self.model_config = model_config
        self.settings = settings
        self.llm_client = None  # 将在子类中初始化
    
    @abstractmethod
    def get_prompt_template(self) -> str:
        """
        获取分析师专用的提示模板
        
        Returns:
            str: 提示模板
        """
        pass
    
    @abstractmethod
    def analyze(self, context: Dict[str, Any]) -> str:
        """
        执行分析
        
        Args:
            context: 分析上下文数据
            
        Returns:
            str: 分析结果
        """
        pass
    
    def format_analysis_context(self, symbol: str, indicators: Dict[str, Any], 
                              market_data: Optional[Dict[str, Any]] = None) -> str:
        """
        格式化分析上下文
        
        Args:
            symbol: 交易对符号
            indicators: 技术指标数据
            market_data: 市场数据
            
        Returns:
            str: 格式化的上下文字符串
        """
        context_parts = [
            f"=== {symbol.replace('USDT', '')} 市场分析数据 ===",
            ""
        ]
        
        # 价格信息
        if 'price' in indicators:
            price_data = indicators['price']
            context_parts.extend([
                "📊 价格信息:",
                f"  当前价格: ${price_data.get('current', 0):.4f}",
                f"  24H最高: ${price_data.get('high_24h', 0):.4f}",
                f"  24H最低: ${price_data.get('low_24h', 0):.4f}",
                ""
            ])
        
        # RSI指标
        if 'rsi' in indicators:
            rsi_data = indicators['rsi']
            rsi_value = rsi_data.get('value')
            if rsi_value is not None:
                status_flags = []
                if rsi_data.get('is_extreme_overbought'):
                    status_flags.append("极度超买")
                elif rsi_data.get('is_extreme_oversold'):
                    status_flags.append("极度超卖")
                elif rsi_data.get('is_overbought'):
                    status_flags.append("超买")
                elif rsi_data.get('is_oversold'):
                    status_flags.append("超卖")
                
                status_text = f" ({', '.join(status_flags)})" if status_flags else ""
                context_parts.extend([
                    "📈 RSI指标:",
                    f"  RSI值: {rsi_value:.1f}{status_text}",
                    ""
                ])
        
        # MACD指标
        if 'macd' in indicators:
            macd_data = indicators['macd']
            context_parts.append("📊 MACD指标:")
            
            macd_line = macd_data.get('macd_line')
            signal_line = macd_data.get('signal_line')
            if macd_line is not None and signal_line is not None:
                trend = "看涨" if macd_line > signal_line else "看跌"
                context_parts.append(f"  MACD线: {macd_line:.6f}")
                context_parts.append(f"  信号线: {signal_line:.6f}")
                context_parts.append(f"  趋势: {trend}")
            
            if macd_data.get('is_bullish_crossover'):
                context_parts.append("  ⚡ 金叉信号")
            elif macd_data.get('is_bearish_crossover'):
                context_parts.append("  ⚡ 死叉信号")
            
            context_parts.append("")
        
        # 移动平均线
        if 'moving_averages' in indicators:
            ma_data = indicators['moving_averages']
            context_parts.append("📉 移动平均线:")
            
            for period, key in [("MA20", "ma_20"), ("MA50", "ma_50"), ("MA200", "ma_200")]:
                ma_value = ma_data.get(key)
                if ma_value is not None:
                    above_key = f"price_above_{key}"
                    position = "上方" if ma_data.get(above_key) else "下方"
                    context_parts.append(f"  {period}: ${ma_value:.4f} (价格在{position})")
            
            context_parts.append("")
        
        # 市场数据
        if market_data:
            context_parts.extend([
                "🌍 市场数据:",
                f"  全球市值: ${market_data.get('total_market_cap_usd', 0):,.0f}",
                f"  24H成交量: ${market_data.get('total_volume_24h_usd', 0):,.0f}",
                ""
            ])
        
        return '\n'.join(context_parts)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            Dict[str, Any]: 模型信息
        """
        return {
            'name': self.name,
            'provider': self.model_config.provider,
            'model': self.model_config.model,
            'max_tokens': self.model_config.max_tokens,
            'temperature': self.model_config.temperature
        }