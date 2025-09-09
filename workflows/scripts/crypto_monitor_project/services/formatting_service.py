# -*- coding: utf-8 -*-
"""
格式化服务 - 处理所有数据展示格式化工作
接管Controller中的所有_format_*方法，实现统一的数据格式化
"""

import pandas as pd
from typing import Dict, List, Any
from ..config import Settings


class FormattingService:
    """格式化服务 - 单一职责：数据展示格式化"""
    
    def __init__(self, settings: Settings):
        """
        初始化格式化服务
        
        Args:
            settings: 系统配置
        """
        self.settings = settings
    
    def format_technical_data_message(self, data_df: pd.DataFrame, symbol: str) -> str:
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
    
    def format_market_sentiment_message(self, global_data: Dict, trending_data: Dict) -> str:
        """格式化市场情绪分析数据为用户消息"""
        message_parts = ["请基于以下多维度数据分析当前加密货币市场情绪：\n"]
        
        # 全球市场数据
        message_parts.append("=== 全球市场数据 ===")
        message_parts.append(self.format_global_data(global_data))
        message_parts.append("")
        
        # 恐贪指数数据
        message_parts.append("=== 恐贪指数 ===")
        message_parts.append("暂无恐贪指数数据")
        message_parts.append("")
        
        # 热门搜索趋势
        message_parts.append("=== 热门搜索趋势 ===")
        message_parts.append(self.format_trending_data(trending_data))
        message_parts.append("")
        
        # 主流币种表现
        message_parts.append("=== 主流币种表现 ===")
        message_parts.append(self.format_major_coins_performance())
        message_parts.append("")
        
        message_parts.append("请提供客观专业的市场情绪评估，重点关注多个指标之间的相互验证。")
        
        return "\n".join(message_parts)
    
    def format_chief_analysis_message(self, symbol: str, technical_analysis: str, 
                                    sentiment_analysis: str, fundamental_analysis: str, 
                                    macro_analysis: str) -> str:
        """格式化首席分析师数据为用户消息"""
        message_parts = [
            f"请整合以下四个专业代理的分析报告，提供针对{symbol}的全面投资建议：\n",
            "=== 技术分析师报告 ===",
            technical_analysis,
            "\n=== 市场分析师报告 ===",
            sentiment_analysis,
            "\n=== 基本面分析师报告 ===", 
            fundamental_analysis,
            "\n=== 宏观分析师报告 ===",
            macro_analysis,
            f"\n请基于技术面、市场情绪、基本面和宏观面的综合分析，提供针对{symbol}的全面投资建议。",
            "注意平衡各方观点，给出客观专业的结论，重点关注各维度分析的一致性和分歧点。",
            f"请提供具体、可操作的{symbol}投资建议，避免空泛的表述。"
        ]
        
        return "\n".join(message_parts)
    
    def format_macro_data_message(self, macro_data: Dict[str, Any]) -> str:
        """格式化宏观数据为用户消息"""
        if 'error' in macro_data:
            return f"⚠️ 宏观数据收集遇到问题: {macro_data['error']}\n\n请基于一般宏观经济环境分析加密货币市场。"
        
        message_parts = ["请基于以下多维度宏观经济数据分析对加密货币市场的影响：\n"]
        
        # 数据完整性报告
        completeness = macro_data.get('data_completeness', {})
        available_sources = [k for k, v in completeness.items() if v]
        message_parts.append(f"=== 数据源状态 ===")
        message_parts.append(f"可用数据源: {len(available_sources)}/{len(completeness)} 个")
        message_parts.append("")
        
        # Bitcoin ETF资金流向数据
        message_parts.append("=== 比特币ETF资金流向 ===")
        etf_data = macro_data.get('bitcoin_etf_flows')
        if etf_data and completeness.get('etf_available'):
            message_parts.append(f"数据源: {etf_data.get('source', 'Unknown')}")
            message_parts.append(f"当日流向估算: ${etf_data.get('net_inflow_today', 0):,.1f}百万")
            message_parts.append(f"总管理规模: ${etf_data.get('total_aum_estimate', 0):,.0f}万")
            message_parts.append(f"注意: {etf_data.get('note', '数据来源说明')}")
            
            # 显示主要ETF表现（实际数据）
            etf_details = etf_data.get('etf_details', [])
            if etf_details:
                message_parts.append("主要ETF当日表现:")
                for etf in etf_details[:5]:  # 显示前5只
                    symbol = etf.get('symbol', 'N/A')
                    price = etf.get('current_price', 0)
                    change_pct = etf.get('price_change_24h', 0)
                    volume = etf.get('volume_24h', 0)
                    message_parts.append(f"  - {symbol}: ${price:.2f} ({change_pct:+.2f}%) 成交量:{volume:,}")
        else:
            message_parts.append("❌ ETF数据暂时不可用")
            message_parts.append("影响: 无法评估机构资金配置态度及规模变化")
        message_parts.append("")
        
        # 美股主要指数表现
        message_parts.append("=== 美股主要指数表现 ===")
        stock_data = macro_data.get('us_stock_indices')
        if stock_data and completeness.get('stocks_available'):
            message_parts.append(f"数据源: {stock_data.get('source', 'Unknown')}")
            indices = stock_data.get('indices', {})
            
            for idx_code, idx_data in indices.items():
                name = idx_data.get('name', idx_code)
                price = idx_data.get('current_price', 0)
                change_pct = idx_data.get('change_percent', 0)
                message_parts.append(f"{name}: {price:,.2f} ({change_pct:+.2f}%)")
            
            # VIX恐慌指数
            vix_data = stock_data.get('vix', {})
            if vix_data:
                vix_current = vix_data.get('current', 0)
                vix_change = vix_data.get('change', 0)
                message_parts.append(f"VIX恐慌指数: {vix_current:.2f} ({vix_change:+.2f})")
            
            market_sentiment = stock_data.get('market_sentiment', 'unknown')
            message_parts.append(f"市场情绪: {market_sentiment}")
        else:
            message_parts.append("❌ 美股数据暂时不可用")
            message_parts.append("影响: 无法判断加密市场与股票市场的相关性程度")
        message_parts.append("")
        
        # 黄金价格数据
        message_parts.append("=== 黄金价格数据 ===")
        gold_data = macro_data.get('gold_price')
        if gold_data and completeness.get('gold_available'):
            message_parts.append(f"数据源: {gold_data.get('source', 'Unknown')}")
            current_price = gold_data.get('current_price', 0)
            change_24h = gold_data.get('change_24h', 0)
            change_pct = gold_data.get('change_percent', 0)
            message_parts.append(f"现货价格: ${current_price:.2f}/盎司")
            message_parts.append(f"24H变化: ${change_24h:+.2f} ({change_pct:+.2f}%)")
            message_parts.append(f"24H区间: ${gold_data.get('low_24h', 0):.2f} - ${gold_data.get('high_24h', 0):.2f}")
            
            # 技术指标
            tech_indicators = gold_data.get('technical_indicators', {})
            if tech_indicators:
                rsi = tech_indicators.get('rsi_14', 0)
                trend = tech_indicators.get('trend', 'unknown')
                message_parts.append(f"RSI(14): {rsi:.1f}")
                message_parts.append(f"技术趋势: {trend}")
        else:
            message_parts.append("❌ 黄金价格数据暂时不可用")
            message_parts.append("影响: 无法分析加密货币作为通胀对冲工具的当前市场定位")
        message_parts.append("")
        
        # 加密货币全球市场数据
        if 'crypto_global' in macro_data:
            message_parts.append("=== 加密货币全球市场数据 ===")
            global_data = macro_data['crypto_global']
            message_parts.append(f"总市值: ${global_data.get('total_market_cap_usd', 0):,.0f}")
            message_parts.append(f"24H成交量: ${global_data.get('total_volume_24h_usd', 0):,.0f}")  
            message_parts.append(f"24H市值变化: {global_data.get('market_cap_change_percentage_24h_usd', 0):.2f}%")
            message_parts.append(f"活跃加密货币: {global_data.get('active_cryptocurrencies', 0)}")
            message_parts.append("")
        
        # 分析指导
        message_parts.append("=== 分析要点 ===")
        message_parts.append("请重点关注：")
        message_parts.append("1. ETF资金流向与比特币价格走势的相关性")
        message_parts.append("2. 美股市场波动对加密市场的传导效应") 
        message_parts.append("3. 黄金与比特币在避险需求中的竞争关系")
        message_parts.append("4. 宏观流动性环境对整体风险资产的影响")
        
        return "\n".join(message_parts)
    
    def format_global_data(self, global_data: Dict) -> str:
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
    
    def format_trending_data(self, trending_data: List) -> str:
        """格式化热门币种"""
        if not trending_data:
            return "暂无热门币种数据"
        
        names = []
        for coin in trending_data[:5]:
            name = coin.get('name', coin.get('symbol', 'Unknown'))
            names.append(name)
        return ', '.join(names)
    
    def format_major_coins_performance(self, coins_data: Dict[str, float] = None) -> str:
        """
        格式化主要币种表现
        
        Args:
            coins_data: 币种价格数据字典，如果为空则返回占位符
        """
        if not coins_data:
            return "暂无主流币种数据"
        
        performances = []
        for symbol, price in coins_data.items():
            coin_name = symbol.replace('USDT', '')
            performances.append(f"{coin_name}: ${price:.4f}")
        
        return '\n'.join(performances) if performances else "获取主流币种数据失败"
    
    def format_fundamental_data_message(self, symbol: str, fundamental_data: Dict[str, Any]) -> str:
        """格式化基本面数据为用户消息"""
        if not fundamental_data:
            return f"获取{symbol}基本面数据失败"
        
        lines = [f"=== {symbol.replace('USDT', '')} 基本面数据 ==="]
        
        current_price = fundamental_data.get('current_price')
        if current_price:
            lines.append(f"当前价格: ${current_price:.4f}")
        
        stats = fundamental_data.get('price_stats')
        if stats:
            lines.extend([
                f"24H变化: {stats.get('price_change_percent', 0):.2f}%",
                f"24H成交量: {stats.get('volume', 0):,.0f}",
                f"24H最高: ${stats.get('high_price', 0):.4f}",
                f"24H最低: ${stats.get('low_price', 0):.4f}"
            ])
        
        return '\n'.join(lines)
    
    def format_symbol_analyses(self, symbol_analyses: Dict[str, Any]) -> str:
        """格式化币种分析报告"""
        lines = []
        for symbol, analysis in symbol_analyses.items():
            lines.extend([
                f"=== {symbol.replace('USDT', '')} 分析报告 ===",
                f"首席分析师: {analysis.get('chief_analysis', '暂无')}",
                ""
            ])
        return '\n'.join(lines)
    
    def format_technical_data(self, data_df: pd.DataFrame) -> str:
        """格式化技术分析数据"""
        lines = []
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
            lines.append(line)
        return '\n'.join(lines)