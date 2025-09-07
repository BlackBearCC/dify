# -*- coding: utf-8 -*-
"""
技术分析师
专注于技术指标和价格走势分析
"""

from typing import Dict, Any
from .base_analyst import BaseAnalyst
from .prompt_manager import PromptManager
from ..config import Settings


class TechnicalAnalyst(BaseAnalyst):
    """技术分析师"""
    
    def __init__(self, settings: Settings, llm_client):
        """
        初始化技术分析师
        
        Args:
            settings: 系统配置
            llm_client: LLM客户端
        """
        super().__init__(
            name="技术分析师",
            model_config=settings.api.technical_analyst,
            settings=settings
        )
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
    
    def get_prompt_template(self) -> str:
        """
        获取技术分析师的提示模板
        
        Returns:
            str: 提示模板
        """
        return self.prompt_manager.get_technical_analysis_prompt()
    
    def analyze(self, context: Dict[str, Any]) -> str:
        """
        执行技术分析
        
        Args:
            context: 分析上下文
            
        Returns:
            str: 技术分析结果
        """
        try:
            symbol = context.get('symbol', 'UNKNOWN')
            indicators = context.get('indicators', {})
            market_data = context.get('market_data')
            
            # 格式化分析上下文
            formatted_context = self.format_analysis_context(symbol, indicators, market_data)
            
            # 构建提示 - 使用原始prompt格式
            prompt_template = self.get_prompt_template()
            
            # 格式化技术数据为原始prompt需要的格式
            kline_data_str = self._format_kline_data_for_prompt(context.get('kline_data', []))
            
            prompt = prompt_template.format(
                symbol=symbol,
                interval=self.settings.kline.default_period,
                data=kline_data_str
            )
            
            # 调用LLM进行分析
            if self.llm_client:
                response = self.llm_client.call(prompt, agent_name='技术分析师')
                return f"📈 {self.name}分析报告\n\n{response}"
            else:
                return f"❌ {self.name}: LLM客户端未初始化"
                
        except Exception as e:
            return f"❌ {self.name}分析失败: {str(e)}"
    
    def check_trading_signals(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查交易信号
        
        Args:
            indicators: 技术指标数据
            
        Returns:
            Dict[str, Any]: 交易信号分析结果
        """
        signals = {
            'strength': 'neutral',  # strong_buy, buy, neutral, sell, strong_sell
            'confidence': 0.5,
            'reasons': []
        }
        
        try:
            score = 0
            max_score = 0
            
            # RSI信号
            if 'rsi' in indicators:
                rsi_data = indicators['rsi']
                max_score += 2
                
                if rsi_data.get('is_extreme_oversold'):
                    score += 2
                    signals['reasons'].append("RSI极度超卖")
                elif rsi_data.get('is_oversold'):
                    score += 1
                    signals['reasons'].append("RSI超卖")
                elif rsi_data.get('is_extreme_overbought'):
                    score -= 2
                    signals['reasons'].append("RSI极度超买")
                elif rsi_data.get('is_overbought'):
                    score -= 1
                    signals['reasons'].append("RSI超买")
            
            # MACD信号
            if 'macd' in indicators:
                macd_data = indicators['macd']
                max_score += 1
                
                if macd_data.get('is_bullish_crossover'):
                    score += 1
                    signals['reasons'].append("MACD金叉")
                elif macd_data.get('is_bearish_crossover'):
                    score -= 1
                    signals['reasons'].append("MACD死叉")
            
            # 移动平均线信号
            if 'moving_averages' in indicators:
                ma_data = indicators['moving_averages']
                max_score += 1
                
                above_count = sum([
                    ma_data.get('price_above_ma_20', False),
                    ma_data.get('price_above_ma_50', False),
                    ma_data.get('price_above_ma_200', False)
                ])
                
                if above_count >= 2:
                    score += 1
                    signals['reasons'].append(f"价格高于{above_count}/3条MA")
                elif above_count <= 1:
                    score -= 1
                    signals['reasons'].append(f"价格低于{3-above_count}/3条MA")
            
            # 计算信号强度
            if max_score > 0:
                normalized_score = score / max_score
                signals['confidence'] = abs(normalized_score)
                
                if normalized_score >= 0.7:
                    signals['strength'] = 'strong_buy'
                elif normalized_score >= 0.3:
                    signals['strength'] = 'buy'
                elif normalized_score <= -0.7:
                    signals['strength'] = 'strong_sell'
                elif normalized_score <= -0.3:
                    signals['strength'] = 'sell'
                else:
                    signals['strength'] = 'neutral'
            
        except Exception as e:
            signals['reasons'].append(f"信号分析异常: {e}")
        
        return signals
    
    def _format_kline_data_for_prompt(self, kline_data: list) -> str:
        """
        格式化K线数据为prompt需要的格式
        
        Args:
            kline_data: K线数据列表
            
        Returns:
            str: 格式化的K线数据字符串
        """
        if not kline_data:
            return "无K线数据"
        
        # 取最近10个数据点
        recent_data = kline_data[-10:] if len(kline_data) >= 10 else kline_data
        
        lines = []
        for kline in recent_data:
            try:
                timestamp = kline.get('timestamp', 0)
                line = (f"时间:{timestamp} | "
                       f"开盘:{kline.get('open', 0):.4f} | "
                       f"最高:{kline.get('high', 0):.4f} | "
                       f"最低:{kline.get('low', 0):.4f} | "
                       f"收盘:{kline.get('close', 0):.4f} | "
                       f"成交量:{kline.get('volume', 0):.0f}")
                lines.append(line)
            except Exception as e:
                print(f"❌ 格式化K线数据失败: {e}")
        
        return '\n'.join(lines)