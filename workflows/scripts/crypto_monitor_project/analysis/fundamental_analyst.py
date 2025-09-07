# -*- coding: utf-8 -*-
"""
基本面分析师
专注于项目基础和长期价值分析
"""

from typing import Dict, Any
from .base_analyst import BaseAnalyst
from .prompt_manager import PromptManager
from ..config import Settings


class FundamentalAnalyst(BaseAnalyst):
    """基本面分析师"""
    
    def __init__(self, settings: Settings, llm_client):
        """
        初始化基本面分析师
        
        Args:
            settings: 系统配置
            llm_client: LLM客户端
        """
        super().__init__(
            name="基本面分析师",
            model_config=settings.api.fundamental_analyst,
            settings=settings
        )
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
    
    def get_prompt_template(self) -> str:
        """
        获取基本面分析师的提示模板
        
        Returns:
            str: 提示模板
        """
        return self.prompt_manager.get_fundamental_analysis_prompt()
    
    def analyze(self, context: Dict[str, Any]) -> str:
        """
        执行基本面分析
        
        Args:
            context: 分析上下文
            
        Returns:
            str: 基本面分析结果
        """
        try:
            symbol = context.get('symbol', 'UNKNOWN')
            indicators = context.get('indicators', {})
            market_data = context.get('market_data')
            
            # 构建基本面分析上下文
            fundamental_context = self._build_fundamental_context(symbol, indicators, market_data)
            
            # 构建提示 - 使用原始prompt格式  
            prompt_template = self.get_prompt_template()
            
            # 构建市场数据字符串
            market_data_str = self._build_fundamental_context(symbol, indicators, market_data)
            
            prompt = prompt_template.format(market_data=market_data_str)
            
            # 调用LLM进行分析
            if self.llm_client:
                response = self.llm_client.call(prompt, agent_name='基本面分析师')
                return f"🏛️ {self.name}分析报告\n\n{response}"
            else:
                return f"❌ {self.name}: LLM客户端未初始化"
                
        except Exception as e:
            return f"❌ {self.name}分析失败: {str(e)}"
    
    def _build_fundamental_context(self, symbol: str, indicators: Dict[str, Any], 
                                 market_data: Dict[str, Any]) -> str:
        """
        构建基本面分析上下文
        
        Args:
            symbol: 交易对符号
            indicators: 技术指标
            market_data: 市场数据
            
        Returns:
            str: 格式化的基本面上下文
        """
        context_parts = [
            f"=== {symbol.replace('USDT', '')} 基本面分析数据 ===",
            ""
        ]
        
        # 根据币种提供基础信息
        coin_name = symbol.replace('USDT', '').upper()
        context_parts.extend([
            f"🪙 分析标的: {coin_name}",
            ""
        ])
        
        # 市场地位信息
        if market_data:
            context_parts.extend([
                "📊 市场地位:",
                f"  市值排名: {market_data.get('market_cap_rank', 'N/A')}",
                f"  当前市值: ${market_data.get('market_cap_usd', 0):,.0f}",
                f"  流通供应: {market_data.get('circulating_supply', 0):,.0f}",
                f"  最大供应: {market_data.get('max_supply', 0):,.0f}",
                ""
            ])
            
            # 价格历史
            ath = market_data.get('ath')
            atl = market_data.get('atl')
            if ath and atl:
                context_parts.extend([
                    "📈 价格历史:",
                    f"  历史最高: ${ath:.4f}",
                    f"  历史最低: ${atl:.4f}",
                    f"  距ATH: {market_data.get('ath_change_percentage', 0):.1f}%",
                    f"  距ATL: {market_data.get('atl_change_percentage', 0):.1f}%",
                    ""
                ])
        
        # 当前价格表现
        if indicators and 'price' in indicators:
            price_data = indicators['price']
            context_parts.extend([
                "💰 当前表现:",
                f"  当前价格: ${price_data.get('current', 0):.4f}",
                ""
            ])
        
        # 根据币种添加特定分析要点
        specific_points = self._get_coin_specific_points(coin_name)
        if specific_points:
            context_parts.extend(["🎯 重点关注:", specific_points, ""])
        
        return '\n'.join(context_parts)
    
    def _get_coin_specific_points(self, coin_name: str) -> str:
        """
        获取币种特定的分析要点
        
        Args:
            coin_name: 币种名称
            
        Returns:
            str: 特定分析要点
        """
        specific_points = {
            'BTC': "  - 数字黄金地位和机构采用\n  - 闪电网络扩容进展\n  - 减半周期影响",
            'ETH': "  - 以太坊2.0升级和POS转换\n  - DeFi生态发展\n  - Layer2解决方案采用",
            'SOL': "  - 高性能区块链竞争力\n  - 生态应用发展\n  - 网络稳定性改善",
            'ADA': "  - 学术研究驱动的开发\n  - 智能合约平台竞争\n  - 治理和去中心化进展",
            'DOT': "  - 跨链互操作性\n  - 平行链拍卖和生态\n  - Web3愿景实现",
        }
        
        return specific_points.get(coin_name, "  - 请关注项目技术创新和应用落地")
    
    def get_long_term_outlook(self, symbol: str, market_data: Dict[str, Any]) -> str:
        """
        获取长期前景评估
        
        Args:
            symbol: 交易对符号
            market_data: 市场数据
            
        Returns:
            str: 长期前景评估
        """
        try:
            coin_name = symbol.replace('USDT', '').upper()
            
            # 基础评估因素
            factors = []
            
            # 市值排名
            rank = market_data.get('market_cap_rank', 999)
            if rank <= 10:
                factors.append("头部币种地位稳固")
            elif rank <= 50:
                factors.append("主流币种认知度高")
            else:
                factors.append("小币种风险较高")
            
            # 供应量模型
            circulating = market_data.get('circulating_supply', 0)
            max_supply = market_data.get('max_supply', 0)
            if max_supply > 0:
                inflation_rate = (max_supply - circulating) / max_supply * 100
                if inflation_rate < 10:
                    factors.append("通胀率较低")
                elif inflation_rate > 50:
                    factors.append("通胀压力较大")
            
            # 距离ATH的位置
            ath_change = market_data.get('ath_change_percentage', 0)
            if ath_change > -50:
                factors.append("仍处高位区间")
            elif ath_change < -80:
                factors.append("已深度回调")
            
            return " | ".join(factors)
            
        except Exception as e:
            return f"长期前景评估异常: {e}"