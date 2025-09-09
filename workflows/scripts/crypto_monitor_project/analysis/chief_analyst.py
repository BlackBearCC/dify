# -*- coding: utf-8 -*-
"""
首席分析师
整合所有分析师观点，提供综合建议
"""

from typing import Dict, Any, List
from .base_analyst import BaseAnalyst
from .prompt_manager import PromptManager
from ..config import Settings


class ChiefAnalyst(BaseAnalyst):
    """首席分析师"""
    
    def __init__(self, settings: Settings, llm_client):
        """
        初始化首席分析师
        
        Args:
            settings: 系统配置
            llm_client: LLM客户端
        """
        super().__init__(
            name="首席分析师",
            model_config=settings.api.chief_analyst,
            settings=settings
        )
        self.llm_client = llm_client
        self.prompt_manager = PromptManager()
    
    def get_prompt_template(self) -> str:
        """
        获取首席分析师的提示模板
        
        Returns:
            str: 提示模板
        """
        return self.prompt_manager.get_chief_analysis_prompt()
    
    def generate_comprehensive_analysis(self, symbol: str, technical_analysis: str, 
                                      sentiment_analysis: str, fundamental_analysis: str, 
                                      macro_analysis: str) -> str:
        """
        首席分析师综合分析 - 分离系统提示词与实时数据
        
        Args:
            symbol: 币种符号
            technical_analysis: 技术分析结果
            sentiment_analysis: 市场情绪分析结果
            fundamental_analysis: 基本面分析结果
            macro_analysis: 宏观分析结果
            
        Returns:
            str: 综合分析结果
        """
        try:
            # 1. 获取系统提示词
            system_prompt = self.get_prompt_template()
            
            # 2. 构建用户消息
            user_message = self._format_chief_analysis_message(
                symbol, technical_analysis, sentiment_analysis, fundamental_analysis, macro_analysis
            )
            
            # 3. 调用LLM（分离模式）
            if self.llm_client:
                if hasattr(self.llm_client, 'call'):
                    return self.llm_client.call(system_prompt, user_message=user_message, agent_name='首席分析师')
                else:
                    # 兼容旧接口
                    full_prompt = f"{system_prompt}\n\n{user_message}"
                    return self.llm_client(full_prompt)
            else:
                return "❌ 首席分析师: LLM客户端未初始化"
                
        except Exception as e:
            return f"❌ 首席分析师综合分析失败: {str(e)}"
    
    def _format_chief_analysis_message(self, symbol: str, technical_analysis: str, 
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

    def analyze(self, context: Dict[str, Any]) -> str:
        """
        执行综合分析
        
        Args:
            context: 分析上下文
            
        Returns:
            str: 综合分析结果
        """
        try:
            symbol = context.get('symbol', 'UNKNOWN')
            indicators = context.get('indicators', {})
            market_data = context.get('market_data')
            analyst_reports = context.get('analyst_reports', [])
            
            # 格式化基础上下文
            formatted_context = self.format_analysis_context(symbol, indicators, market_data)
            
            # 格式化分析师报告
            formatted_reports = self._format_analyst_reports(analyst_reports)
            
            # 构建提示 - 使用原始prompt格式
            prompt_template = self.get_prompt_template()
            
            prompt = prompt_template.format(
                symbol=symbol,
                technical_analysis=self._extract_report_content(analyst_reports, '技术分析师'),
                sentiment_analysis=self._extract_report_content(analyst_reports, '市场分析师'),
                fundamental_analysis=self._extract_report_content(analyst_reports, '基本面分析师'),
                macro_analysis=self._extract_report_content(analyst_reports, '宏观分析师')
            )
            
            # 调用LLM进行综合分析
            if self.llm_client:
                response = self.llm_client.call(prompt, agent_name='首席分析师')
                return f"👨‍💼 {self.name}综合报告\n\n{response}"
            else:
                return f"❌ {self.name}: LLM客户端未初始化"
                
        except Exception as e:
            return f"❌ {self.name}分析失败: {str(e)}"
    
    def _format_analyst_reports(self, reports: List[Dict[str, Any]]) -> str:
        """
        格式化分析师报告
        
        Args:
            reports: 分析师报告列表
            
        Returns:
            str: 格式化的报告文本
        """
        if not reports:
            return "暂无其他分析师报告"
        
        formatted_reports = []
        
        for report in reports:
            analyst_name = report.get('analyst', '未知分析师')
            content = report.get('content', '无内容')
            
            formatted_reports.append(f"### {analyst_name}\n{content}\n")
        
        return '\n'.join(formatted_reports)
    
    def synthesize_recommendations(self, analyst_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        综合各分析师建议
        
        Args:
            analyst_reports: 分析师报告列表
            
        Returns:
            Dict[str, Any]: 综合建议结果
        """
        synthesis = {
            'consensus_strength': 'neutral',
            'agreement_level': 0.5,
            'key_points': [],
            'risks': [],
            'final_recommendation': 'observe'
        }
        
        try:
            if not analyst_reports:
                return synthesis
            
            # 提取关键观点
            bullish_signals = 0
            bearish_signals = 0
            total_signals = 0
            
            for report in analyst_reports:
                content = report.get('content', '').lower()
                
                # 简单的关键词分析
                bullish_keywords = ['买入', 'buy', '看涨', '上涨', '突破', '金叉']
                bearish_keywords = ['卖出', 'sell', '看跌', '下跌', '跌破', '死叉']
                
                for keyword in bullish_keywords:
                    if keyword in content:
                        bullish_signals += 1
                        total_signals += 1
                        break
                
                for keyword in bearish_keywords:
                    if keyword in content:
                        bearish_signals += 1
                        total_signals += 1
                        break
            
            # 计算一致性
            if total_signals > 0:
                if bullish_signals > bearish_signals:
                    synthesis['consensus_strength'] = 'bullish'
                    synthesis['agreement_level'] = bullish_signals / len(analyst_reports)
                    if synthesis['agreement_level'] > 0.7:
                        synthesis['final_recommendation'] = 'buy'
                    else:
                        synthesis['final_recommendation'] = 'observe'
                elif bearish_signals > bullish_signals:
                    synthesis['consensus_strength'] = 'bearish'
                    synthesis['agreement_level'] = bearish_signals / len(analyst_reports)
                    if synthesis['agreement_level'] > 0.7:
                        synthesis['final_recommendation'] = 'sell'
                    else:
                        synthesis['final_recommendation'] = 'observe'
                else:
                    synthesis['consensus_strength'] = 'neutral'
                    synthesis['final_recommendation'] = 'observe'
            
            # 提取关键点和风险
            synthesis['key_points'] = [
                f"技术面信号: {bullish_signals}个看涨，{bearish_signals}个看跌",
                f"分析师一致性: {synthesis['agreement_level']:.1%}"
            ]
            
            synthesis['risks'] = [
                "市场波动风险",
                "分析师观点分歧" if synthesis['agreement_level'] < 0.6 else "观点相对一致"
            ]
            
        except Exception as e:
            synthesis['key_points'].append(f"综合分析异常: {e}")
        
        return synthesis
    
    def _extract_report_content(self, reports: List[Dict[str, Any]], analyst_name: str) -> str:
        """
        从报告列表中提取指定分析师的报告内容
        
        Args:
            reports: 报告列表
            analyst_name: 分析师名称
            
        Returns:
            str: 报告内容
        """
        for report in reports:
            if report.get('analyst') == analyst_name:
                return report.get('content', '暂无报告')
        return f'暂无{analyst_name}报告'