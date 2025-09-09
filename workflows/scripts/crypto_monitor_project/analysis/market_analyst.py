# -*- coding: utf-8 -*-
"""
市场分析师
专注于市场情绪和整体趋势分析
"""

from typing import Dict, Any
from .base_analyst import BaseAnalyst
from .prompt_manager import PromptManager
from ..config import Settings


class MarketAnalyst(BaseAnalyst):
    """市场分析师"""
    
    def __init__(self, settings: Settings, llm_client):
        """
        初始化市场分析师
        
        Args:
            settings: 系统配置
            llm_client: LLM客户端
        """
        super().__init__(
            name="市场分析师",
            model_config=settings.api.market_analyst,
            settings=settings
        )
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
    
    def get_prompt_template(self) -> str:
        """
        获取市场分析师的提示模板
        
        Returns:
            str: 提示模板
        """
        return self.prompt_manager.get_market_sentiment_prompt()
    
    def analyze(self, context: Dict[str, Any]) -> str:
        """
        执行市场分析
        
        Args:
            context: 分析上下文
            
        Returns:
            str: 市场分析结果
        """
        try:
            symbol = context.get('symbol', 'UNKNOWN')
            indicators = context.get('indicators', {})
            market_data = context.get('market_data')
            global_data = context.get('global_data')
            trending_data = context.get('trending_data')
            
            # 构建市场分析上下文
            market_context = self._build_market_context(symbol, indicators, market_data, global_data, trending_data)
            
            # 构建提示 - 使用原始prompt格式
            prompt_template = self.get_prompt_template()
            
            # 格式化市场数据
            formatted_data = {
                'global_market_data': self._format_global_data(global_data),
                'fear_greed_index': "暂无恐贪指数数据",  # 原始系统中可能有这个数据
                'trending_coins': self._format_trending_data(trending_data),
                'major_coins_performance': self._format_major_coins_performance(indicators)
            }
            
            prompt = prompt_template.format(**formatted_data)
            
            # 调用LLM进行分析
            if self.llm_client:
                response = self.llm_client.call(prompt, agent_name='市场分析师')
                return f"🌍 {self.name}分析报告\n\n{response}"
            else:
                return f"❌ {self.name}: LLM客户端未初始化"
                
        except Exception as e:
            return f"❌ {self.name}分析失败: {str(e)}"
    
    def _build_market_context(self, symbol: str, indicators: Dict[str, Any], 
                            market_data: Dict[str, Any], global_data: Dict[str, Any],
                            trending_data: list) -> str:
        """
        构建市场分析上下文
        
        Args:
            symbol: 交易对符号
            indicators: 技术指标
            market_data: 市场数据
            global_data: 全球数据
            trending_data: 热门币种数据
            
        Returns:
            str: 格式化的市场上下文
        """
        context_parts = [
            f"=== {symbol.replace('USDT', '')} 市场环境分析 ===",
            ""
        ]
        
        # 全球市场数据
        if global_data:
            context_parts.extend([
                "🌍 全球加密市场:",
                f"  总市值: ${global_data.get('total_market_cap_usd', 0):,.0f}",
                f"  24H总成交量: ${global_data.get('total_volume_24h_usd', 0):,.0f}",
                f"  24H市值变化: {global_data.get('market_cap_change_percentage_24h_usd', 0):.2f}%",
                f"  活跃加密货币数: {global_data.get('active_cryptocurrencies', 0)}",
                ""
            ])
            
            # 市场主导地位
            market_cap_percentage = global_data.get('market_cap_percentage', {})
            if market_cap_percentage:
                context_parts.append("👑 市场主导地位:")
                for coin, percentage in market_cap_percentage.items():
                    if percentage > 1:  # 只显示占比大于1%的
                        context_parts.append(f"  {coin.upper()}: {percentage:.1f}%")
                context_parts.append("")
        
        # 热门币种
        if trending_data and isinstance(trending_data, list):
            context_parts.extend([
                "🔥 当前热门币种:",
                "  " + ", ".join([coin.get('symbol', 'N/A').upper() for coin in trending_data[:5]]),
                ""
            ])
        
        # 当前币种技术面简要
        if indicators:
            price_data = indicators.get('price', {})
            context_parts.extend([
                f"📊 {symbol.replace('USDT', '')} 当前状态:",
                f"  价格: ${price_data.get('current', 0):.4f}",
                ""
            ])
            
            # RSI情绪指标
            rsi_data = indicators.get('rsi', {})
            rsi_value = rsi_data.get('value')
            if rsi_value is not None:
                if rsi_value > 70:
                    sentiment = "贪婪"
                elif rsi_value < 30:
                    sentiment = "恐慌"
                else:
                    sentiment = "中性"
                context_parts.append(f"  市场情绪(RSI): {sentiment} ({rsi_value:.1f})")
                context_parts.append("")
        
        return '\n'.join(context_parts)
    
    def analyze_market_sentiment(self, global_data: Dict[str, Any], trending_data: list) -> str:
        """
        分析市场情绪 - 使用系统提示词与实时数据分离模式
        
        Args:
            global_data: 全球市场数据
            trending_data: 热门币种数据
            
        Returns:
            str: 市场情绪分析结果
        """
        try:
            # 获取系统提示词
            system_prompt = self.prompt_manager.get_market_sentiment_prompt()
            
            # 构建用户消息
            user_message = self._format_market_sentiment_message(global_data, trending_data)
            
            # 调用LLM（分离模式）
            if self.llm_client:
                if hasattr(self.llm_client, 'call'):
                    return self.llm_client.call(system_prompt, user_message=user_message, agent_name='市场分析师')
                else:
                    # 兼容旧接口
                    full_prompt = f"{system_prompt}\n\n{user_message}"
                    return self.llm_client(full_prompt)
            else:
                return "❌ 市场分析师: LLM客户端未初始化"
                
        except Exception as e:
            return f"❌ 市场情绪分析失败: {str(e)}"
    
    def _format_market_sentiment_message(self, global_data: Dict[str, Any], trending_data: list) -> str:
        """格式化市场情绪分析数据为用户消息"""
        message_parts = ["请基于以下多维度数据分析当前加密货币市场情绪：\n"]
        
        # 全球市场数据
        message_parts.append("=== 全球市场数据 ===")
        message_parts.append(self._format_global_data(global_data))
        message_parts.append("")
        
        # 恐贪指数数据
        message_parts.append("=== 恐贪指数 ===")
        message_parts.append("暂无恐贪指数数据")
        message_parts.append("")
        
        # 热门搜索趋势
        message_parts.append("=== 热门搜索趋势 ===")
        message_parts.append(self._format_trending_data(trending_data))
        message_parts.append("")
        
        # 主流币种表现
        message_parts.append("=== 主流币种表现 ===")
        message_parts.append("需要具体币种数据进行分析")
        message_parts.append("")
        
        message_parts.append("请提供客观专业的市场情绪评估，重点关注多个指标之间的相互验证。")
        
        return "\n".join(message_parts)

    def assess_market_sentiment(self, indicators: Dict[str, Any], global_data: Dict[str, Any]) -> str:
        """
        评估市场情绪
        
        Args:
            indicators: 技术指标
            global_data: 全球数据
            
        Returns:
            str: 市场情绪评估
        """
        sentiments = []
        
        try:
            # 基于RSI的情绪
            rsi_data = indicators.get('rsi', {})
            rsi_value = rsi_data.get('value')
            if rsi_value is not None:
                if rsi_value > 80:
                    sentiments.append("极度贪婪")
                elif rsi_value > 70:
                    sentiments.append("贪婪")
                elif rsi_value < 20:
                    sentiments.append("极度恐慌")
                elif rsi_value < 30:
                    sentiments.append("恐慌")
                else:
                    sentiments.append("中性")
            
            # 基于市值变化的情绪
            if global_data:
                market_change = global_data.get('market_cap_change_percentage_24h_usd', 0)
                if market_change > 5:
                    sentiments.append("市场乐观")
                elif market_change < -5:
                    sentiments.append("市场悲观")
            
            return " & ".join(sentiments) if sentiments else "情绪不明"
            
        except Exception as e:
            return f"情绪评估异常: {e}"
    
    def _format_global_data(self, global_data: Dict[str, Any]) -> str:
        """格式化全球市场数据"""
        if not global_data:
            return "暂无全球市场数据"
        
        lines = [
            f"总市值: ${global_data.get('total_market_cap_usd', 0):,.0f}",
            f"24H成交量: ${global_data.get('total_volume_24h_usd', 0):,.0f}", 
            f"24H市值变化: {global_data.get('market_cap_change_percentage_24h_usd', 0):.2f}%",
            f"活跃加密货币: {global_data.get('active_cryptocurrencies', 0)}"
        ]
        return '\n'.join(lines)
    
    def _format_trending_data(self, trending_data: list) -> str:
        """格式化热门币种数据"""
        if not trending_data:
            return "暂无热门币种数据"
        
        trending_names = []
        for coin in trending_data[:5]:  # 取前5个
            name = coin.get('name', coin.get('symbol', 'Unknown'))
            trending_names.append(name)
        
        return ', '.join(trending_names)
    
    def _format_major_coins_performance(self, indicators: Dict[str, Any]) -> str:
        """格式化主流币种表现"""
        price_data = indicators.get('price', {})
        current_price = price_data.get('current', 0)
        
        return f"当前价格: ${current_price:.4f}"