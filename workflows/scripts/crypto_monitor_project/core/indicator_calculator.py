# -*- coding: utf-8 -*-
"""
技术指标计算器
统一管理所有技术指标的计算
"""

from typing import List, Dict, Any, Optional
from .rsi import RSI
from .macd import MACD
from .moving_average import MovingAverage
from ..config import Settings


class IndicatorCalculator:
    """技术指标计算器"""
    
    def __init__(self, settings: Settings):
        """
        初始化技术指标计算器
        
        Args:
            settings: 系统配置对象
        """
        self.settings = settings
        
        # 初始化各个指标计算器
        self.rsi = RSI(period=settings.indicators.rsi_period)
        self.macd = MACD(
            fast_period=settings.indicators.macd_fast,
            slow_period=settings.indicators.macd_slow,
            signal_period=settings.indicators.macd_signal
        )
        self.ma = MovingAverage()
    
    def calculate_all_indicators(self, kline_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算所有技术指标
        
        Args:
            kline_data: K线数据列表
            
        Returns:
            Dict[str, Any]: 技术指标结果
        """
        if not kline_data:
            return {}
        
        # 提取收盘价
        closes = [float(kline['close']) for kline in kline_data]
        
        results = {}
        
        try:
            # 计算RSI
            rsi_values = self.rsi.calculate(closes)
            latest_rsi = rsi_values[-1] if rsi_values else None
            results['rsi'] = {
                'value': latest_rsi,
                'is_overbought': self.rsi.is_overbought(latest_rsi, self.settings.indicators.rsi_overbought) if latest_rsi else False,
                'is_oversold': self.rsi.is_oversold(latest_rsi, self.settings.indicators.rsi_oversold) if latest_rsi else False,
                'is_extreme_overbought': latest_rsi > self.settings.indicators.rsi_extreme_overbought if latest_rsi else False,
                'is_extreme_oversold': latest_rsi < self.settings.indicators.rsi_extreme_oversold if latest_rsi else False
            }
            
            # 计算MACD
            macd_line, signal_line, histogram = self.macd.calculate(closes)
            latest_macd, latest_signal, latest_histogram = (
                macd_line[-1] if macd_line else None,
                signal_line[-1] if signal_line else None,
                histogram[-1] if histogram else None
            )
            
            results['macd'] = {
                'macd_line': latest_macd,
                'signal_line': latest_signal,
                'histogram': latest_histogram,
                'is_bullish_crossover': self.macd.is_bullish_crossover(macd_line, signal_line),
                'is_bearish_crossover': self.macd.is_bearish_crossover(macd_line, signal_line)
            }
            
            # 计算移动平均线
            ma_20 = self.ma.get_latest_sma(closes, self.settings.indicators.ma_short)
            ma_50 = self.ma.get_latest_sma(closes, self.settings.indicators.ma_medium)
            ma_200 = self.ma.get_latest_sma(closes, self.settings.indicators.ma_long)
            
            current_price = closes[-1]
            
            results['moving_averages'] = {
                'ma_20': ma_20,
                'ma_50': ma_50,
                'ma_200': ma_200,
                'price_above_ma_20': self.ma.is_price_above_ma(current_price, ma_20),
                'price_above_ma_50': self.ma.is_price_above_ma(current_price, ma_50),
                'price_above_ma_200': self.ma.is_price_above_ma(current_price, ma_200)
            }
            
            # 价格信息
            results['price'] = {
                'current': current_price,
                'high_24h': max(closes) if closes else 0,
                'low_24h': min(closes) if closes else 0
            }
            
        except Exception as e:
            print(f"❌ 技术指标计算失败: {e}")
            results['error'] = str(e)
        
        return results
    
    def check_special_conditions(self, symbol: str, indicators: Dict[str, Any]) -> List[str]:
        """
        检查特殊触发条件
        
        Args:
            symbol: 交易对符号
            indicators: 技术指标数据
            
        Returns:
            List[str]: 触发的特殊条件列表
        """
        conditions = []
        
        try:
            # 检查RSI极值
            if self.settings.triggers.rsi_extreme_detection:
                rsi_data = indicators.get('rsi', {})
                if rsi_data.get('is_extreme_overbought'):
                    conditions.append(f"RSI极值超买({rsi_data.get('value', 0):.1f})")
                elif rsi_data.get('is_extreme_oversold'):
                    conditions.append(f"RSI极值超卖({rsi_data.get('value', 0):.1f})")
            
            # 检查MACD金叉死叉
            macd_data = indicators.get('macd', {})
            if macd_data.get('is_bullish_crossover'):
                conditions.append("MACD金叉")
            elif macd_data.get('is_bearish_crossover'):
                conditions.append("MACD死叉")
            
            # 检查移动平均线
            ma_data = indicators.get('moving_averages', {})
            if ma_data.get('price_above_ma_200') and not ma_data.get('price_above_ma_50'):
                conditions.append("价格突破MA50")
            elif not ma_data.get('price_above_ma_200') and ma_data.get('price_above_ma_50'):
                conditions.append("价格跌破MA200")
            
        except Exception as e:
            print(f"❌ 特殊条件检查失败: {e}")
        
        return conditions
    
    def format_indicators_summary(self, symbol: str, indicators: Dict[str, Any]) -> str:
        """
        格式化指标摘要
        
        Args:
            symbol: 交易对符号
            indicators: 技术指标数据
            
        Returns:
            str: 格式化的摘要文本
        """
        try:
            price_data = indicators.get('price', {})
            rsi_data = indicators.get('rsi', {})
            macd_data = indicators.get('macd', {})
            ma_data = indicators.get('moving_averages', {})
            
            summary_lines = [
                f"📊 {symbol.replace('USDT', '')} 技术指标摘要",
                f"💰 当前价格: ${price_data.get('current', 0):.4f}",
            ]
            
            # RSI信息
            rsi_value = rsi_data.get('value')
            if rsi_value is not None:
                rsi_status = ""
                if rsi_data.get('is_extreme_overbought'):
                    rsi_status = " (极度超买)"
                elif rsi_data.get('is_extreme_oversold'):
                    rsi_status = " (极度超卖)"
                elif rsi_data.get('is_overbought'):
                    rsi_status = " (超买)"
                elif rsi_data.get('is_oversold'):
                    rsi_status = " (超卖)"
                
                summary_lines.append(f"📈 RSI: {rsi_value:.1f}{rsi_status}")
            
            # MACD信息
            macd_value = macd_data.get('macd_line')
            signal_value = macd_data.get('signal_line')
            if macd_value is not None and signal_value is not None:
                trend = "看涨" if macd_value > signal_value else "看跌"
                summary_lines.append(f"📊 MACD: {macd_value:.6f} ({trend})")
            
            # MA信息
            ma_20 = ma_data.get('ma_20')
            if ma_20 is not None:
                position = "上方" if ma_data.get('price_above_ma_20') else "下方"
                summary_lines.append(f"📉 MA20: ${ma_20:.4f} (价格在{position})")
            
            return '\n'.join(summary_lines)
            
        except Exception as e:
            return f"❌ 指标摘要生成失败: {e}"