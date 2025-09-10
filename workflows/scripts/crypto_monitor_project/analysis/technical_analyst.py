# -*- coding: utf-8 -*-
"""
技术分析师
专注于技术指标和价格走势分析
"""

from typing import Dict, Any, List
import pandas as pd
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
    
    def analyze_kline_data(self, symbol: str, kline_data: List[Dict[str, Any]]) -> str:
        """
        技术分析 - 分离系统提示词与实时数据
        
        Args:
            symbol: 币种符号
            kline_data: K线数据列表
            
        Returns:
            str: 技术分析结果
        """
        try:
            # 1. 获取系统提示词
            system_prompt = self.get_prompt_template()
            
            # 2. 数据验证
            if not kline_data:
                raise Exception(f"无法获取{symbol}的K线数据")

            # 3. 计算技术指标
            df = pd.DataFrame(kline_data)
            if len(df) < 50:
                raise Exception(f"数据不足，仅有{len(df)}条数据")

            closes = df['close'].astype(float)
            df['sma_20'] = closes.rolling(window=20).mean()
            df['sma_50'] = closes.rolling(window=50).mean()
            df['rsi'] = self._calculate_rsi(closes)
            df['macd'], df['macd_signal'] = self._calculate_macd(closes)

            # 4. 构建用户消息
            recent_data = df.dropna().tail(10)
            user_message = self._format_technical_data_message(recent_data, symbol)
            
            # 5. 调用LLM（分离模式）
            if self.llm_client:
                if hasattr(self.llm_client, 'call'):
                    return self.llm_client.call(system_prompt, user_message=user_message, agent_name='技术分析师')
                else:
                    # 兼容旧接口
                    full_prompt = f"{system_prompt}\n\n{user_message}"
                    return self.llm_client(full_prompt)
            else:
                return "❌ 技术分析师: LLM客户端未初始化"
                
        except Exception as e:
            return f"❌ 技术分析失败: {str(e)}"
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """计算MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        return macd_line, signal_line
    
    def _format_technical_data_message(self, data_df: pd.DataFrame, symbol: str) -> str:
        """格式化技术分析数据为用户消息"""
        message_parts = [
            f"请分析{symbol}的{self.settings.kline.default_period}K线数据：\n",
            "最近10个周期的技术指标数据：",
            "时间戳(time)、开盘价(open)、最高价(high)、最低价(low)、收盘价(close)、成交量(volume)",
            "20期简单移动平均线(sma_20)、50期简单移动平均线(sma_50)",
            "相对强弱指数RSI(rsi)、MACD线(macd)、MACD信号线(macd_signal)\n"
        ]
        
        # 添加具体的数据行
        for _, row in data_df.iterrows():
            line = (f"时间:{row['timestamp']} | "
                   f"开盘:{row['open']:.4f} | "
                   f"最高:{row['high']:.4f} | "
                   f"最低:{row['low']:.4f} | "
                   f"收盘:{row['close']:.4f} | "
                   f"成交量:{row['volume']:.0f} | "
                   f"SMA20:{row.get('sma_20', 'N/A')} | "
                   f"SMA50:{row.get('sma_50', 'N/A')} | "
                   f"RSI:{row.get('rsi', 'N/A')} | "
                   f"MACD:{row.get('macd', 'N/A')} | "
                   f"信号线:{row.get('macd_signal', 'N/A')}")
            message_parts.append(line)
            
        message_parts.append("\n请保持简洁专业，重点关注15分钟级别的短期走势。")
        return "\n".join(message_parts)
    
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
    
    def analyze_crypto_technical(self, symbol: str) -> str:
        """
        为crypto_monitor_project提供的技术分析接口
        兼容原crypto_bot的调用方式
        
        Args:
            symbol: 币种符号
            
        Returns:
            str: 技术分析结果
        """
        try:
            # 模拟调用分析接口，实际应该通过data_service获取数据
            context = {
                'symbol': symbol,
                'indicators': {},
                'market_data': {},
                'kline_data': []
            }
            
            # 直接返回简化的分析结果，避免循环调用
            return f"📈 {symbol}技术分析 - 分析功能正在完善中，请使用完整分析流程"
            
        except Exception as e:
            return f"❌ {symbol}技术分析失败: {e}"