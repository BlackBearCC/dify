# -*- coding: utf-8 -*-
"""
分析服务 - 协调所有分析师模块的分析工作
使用现有的TechnicalAnalyst, MarketAnalyst等模块
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from ..config import Settings
from ..analysis import TechnicalAnalyst, MarketAnalyst, FundamentalAnalyst, ChiefAnalyst, PromptManager
from ..database import DatabaseManager, AnalysisRecord
from ..data import DataCollector


class AnalysisService:
    """分析协调服务 - 单一职责：协调各种分析师进行分析"""
    
    def __init__(self, settings: Settings, db_manager: DatabaseManager, 
                 data_collector: DataCollector, llm_clients: Dict[str, Any]):
        """
        初始化分析服务
        
        Args:
            settings: 系统配置
            db_manager: 数据库管理器
            data_collector: 数据收集器
            llm_clients: LLM客户端字典
        """
        self.settings = settings
        self.db_manager = db_manager
        self.data_collector = data_collector
        self.llm_clients = llm_clients
        
        # 初始化分析师
        self._initialize_analysts()
        
        # Prompt管理器
        self.prompt_manager = PromptManager()
    
    def _initialize_analysts(self):
        """初始化所有分析师"""
        # 技术分析师
        self.technical_analyst = TechnicalAnalyst(
            self.settings, 
            self._get_llm_client_for_analyst('技术分析师')
        )
        
        # 市场分析师
        self.market_analyst = MarketAnalyst(
            self.settings,
            self._get_llm_client_for_analyst('市场分析师')
        )
        
        # 基本面分析师
        self.fundamental_analyst = FundamentalAnalyst(
            self.settings,
            self._get_llm_client_for_analyst('基本面分析师')
        )
        
        # 首席分析师
        self.chief_analyst = ChiefAnalyst(
            self.settings,
            self._get_llm_client_for_analyst('首席分析师')
        )
    
    def _get_llm_client_for_analyst(self, analyst_name: str):
        """为分析师获取对应的LLM客户端"""
        config_map = {
            '技术分析师': self.settings.api.technical_analyst,
            '市场分析师': self.settings.api.market_analyst,
            '基本面分析师': self.settings.api.fundamental_analyst,
            '宏观分析师': self.settings.api.macro_analyst,
            '首席分析师': self.settings.api.chief_analyst,
            '研究部门总监': self.settings.api.research_director
        }
        
        config = config_map.get(analyst_name)
        if not config:
            return self.llm_clients.get('doubao')
        
        return self.llm_clients.get(config.provider, self.llm_clients.get('doubao'))
    
    def conduct_comprehensive_analysis(self, symbols: List[str]) -> Dict[str, Any]:
        """
        进行全面的多币种分析
        
        Args:
            symbols: 要分析的币种列表
            
        Returns:
            Dict: 完整的分析结果
        """
        print(f"🏛️ 启动多分析师协作分析")
        print(f"📊 分析币种: {', '.join([s.replace('USDT', '') for s in symbols])}")
        print("="*80)
        
        symbol_analyses = {}
        macro_analysis = None
        sentiment_analysis = None
        
        for symbol in symbols:
            analysis_result = self.conduct_independent_coin_analysis(symbol)
            symbol_analyses[symbol] = analysis_result
            
            # 共享的宏观和情绪分析
            if macro_analysis is None:
                macro_analysis = analysis_result['macro_analysis']
            if sentiment_analysis is None:
                sentiment_analysis = analysis_result['sentiment_analysis']
        
        return {
            'symbol_analyses': symbol_analyses,
            'macro_analysis': macro_analysis,
            'sentiment_analysis': sentiment_analysis
        }
    
    def conduct_independent_coin_analysis(self, symbol: str) -> Dict[str, Any]:
        """
        独立币种分析 - 协调所有分析师对单个币种进行分析
        
        Args:
            symbol: 币种符号
            
        Returns:
            Dict: 币种分析结果
        """
        newly_generated = set()
        
        print(f"🏛️ 启动币种分析: {symbol}")
        print("="*80)
        
        # 1. 宏观分析
        print("🌍 [宏观分析师] 分析全球市场环境...")
        macro_analysis = self.get_today_analysis('macro_analysis', '宏观分析师')
        if macro_analysis is None:
            print("🔄 生成新的宏观分析...")
            macro_analysis = self.analyze_macro_data()
            newly_generated.add('macro_analysis')
            self._save_analysis_record('宏观分析师', None, macro_analysis, '宏观数据分析')
        
        # 2. 市场情绪分析
        print("🔥 [市场分析师] 分析市场情绪...")
        sentiment_analysis = self.get_today_analysis('market_sentiment', '市场分析师')
        if sentiment_analysis is None:
            print("🔄 生成新的市场情绪分析...")
            sentiment_analysis = self.market_analyst.analyze_market_sentiment(
                self.data_collector.collect_global_market_data(),
                self.data_collector.collect_trending_data()
            )
            newly_generated.add('market_sentiment')
            self._save_analysis_record('市场分析师', None, sentiment_analysis, '市场情绪分析')
        
        # 3. 技术分析
        print(f"📈 [技术分析师] 分析 {symbol}...")
        kline_data = self.data_collector.collect_kline_data([symbol]).get(symbol, [])
        if not kline_data:
            raise Exception(f"无法获取{symbol}的K线数据")
        
        technical_analysis = self.technical_analyst.analyze_kline_data(symbol, kline_data)
        self._save_analysis_record('技术分析师', symbol, technical_analysis, f'{symbol}技术分析')
        newly_generated.add(f'technical_analysis_{symbol}')
        
        # 4. 基本面分析
        print(f"📊 [基本面分析师] 分析 {symbol}...")
        fundamental_analysis = self.get_today_analysis(f'fundamental_analysis_{symbol}', '基本面分析师')
        if fundamental_analysis is None:
            print(f"🔄 生成新的{symbol}基本面分析...")
            fundamental_analysis = self.fundamental_analyst.analyze_fundamental_data(symbol, self.data_collector)
            newly_generated.add(f'fundamental_analysis_{symbol}')
            self._save_analysis_record('基本面分析师', symbol, fundamental_analysis, f'{symbol}基本面分析')
        
        # 5. 首席分析师整合
        print(f"🎯 [{symbol}首席分析师] 整合分析...")
        dependencies_updated = any(dep in newly_generated for dep in [
            'macro_analysis', 'market_sentiment', 
            f'technical_analysis_{symbol}', f'fundamental_analysis_{symbol}'
        ])
        
        coin_chief_analysis = self.get_today_analysis(f'coin_chief_analysis_{symbol}', f'{symbol}首席分析师')
        if coin_chief_analysis is None or dependencies_updated:
            coin_chief_analysis = self.chief_analyst.generate_comprehensive_analysis(
                symbol, technical_analysis, sentiment_analysis, fundamental_analysis, macro_analysis
            )
            self._save_analysis_record(f'{symbol}首席分析师', symbol, coin_chief_analysis, f'{symbol}首席分析')
        
        return {
            'symbol': symbol,
            'macro_analysis': macro_analysis,
            'sentiment_analysis': sentiment_analysis,
            'technical_analysis': technical_analysis,
            'fundamental_analysis': fundamental_analysis,
            'chief_analysis': coin_chief_analysis,
        }
    
    def analyze_macro_data(self) -> str:
        """宏观分析 - 分离系统提示词与实时数据"""
        # 获取系统提示词
        system_prompt = self.prompt_manager.get_macro_analysis_prompt()
        
        # 收集宏观数据
        macro_data = self._collect_macro_data()
        
        # 构建用户消息
        user_message = self._format_macro_data_message(macro_data)
        
        # 调用LLM（分离模式）
        llm_client = self._get_llm_client_for_analyst('宏观分析师')
        return llm_client.call(system_prompt, user_message=user_message, agent_name='宏观分析师')
    
    def _collect_macro_data(self) -> Dict[str, Any]:
        """收集宏观经济数据"""
        try:
            comprehensive_macro = self.data_collector.collect_comprehensive_macro_data()
            
            if comprehensive_macro:
                # 添加加密货币全局数据
                global_data = self.data_collector.collect_global_market_data()
                if global_data:
                    comprehensive_macro['crypto_global'] = global_data
                
                return comprehensive_macro
            else:
                print("⚠️ 宏观数据收集失败，使用备用数据结构")
                return self._get_fallback_macro_data()
            
        except Exception as e:
            print(f"❌ 收集宏观数据失败: {e}")
            return self._get_fallback_macro_data(error=str(e))
    
    def _get_fallback_macro_data(self, error: str = None) -> Dict[str, Any]:
        """宏观数据收集失败时的备用数据结构"""
        fallback_data = {
            'timestamp': datetime.now().isoformat(),
            'data_completeness': {
                'etf_available': False,
                'stocks_available': False,
                'gold_available': False
            },
            'bitcoin_etf_flows': None,
            'us_stock_indices': None,
            'gold_price': None
        }
        
        if error:
            fallback_data['error'] = error
        
        # 尝试至少获取加密货币全局数据
        try:
            global_data = self.data_collector.collect_global_market_data()
            if global_data:
                fallback_data['crypto_global'] = global_data
                fallback_data['data_completeness']['crypto_global_available'] = True
        except Exception:
            fallback_data['data_completeness']['crypto_global_available'] = False
        
        return fallback_data
    
    def _format_macro_data_message(self, macro_data: Dict[str, Any]) -> str:
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
            
            # 显示主要ETF表现
            etf_details = etf_data.get('etf_details', [])
            if etf_details:
                message_parts.append("主要ETF当日表现:")
                for etf in etf_details[:5]:
                    symbol = etf.get('symbol', 'N/A')
                    price = etf.get('current_price', 0)
                    change_pct = etf.get('price_change_24h', 0)
                    volume = etf.get('volume_24h', 0)
                    message_parts.append(f"  - {symbol}: ${price:.2f} ({change_pct:+.2f}%) 成交量:{volume:,}")
        else:
            message_parts.append("❌ ETF数据暂时不可用")
        message_parts.append("")
        
        return "\n".join(message_parts)
    
    def get_today_analysis(self, data_type: str, agent_name: str) -> Optional[str]:
        """获取今日分析缓存"""
        try:
            records = self.db_manager.get_analysis_records(data_type=data_type, agent_name=agent_name, limit=1)
            if records:
                record = records[0]
                if record.timestamp and record.timestamp.date() == datetime.now().date():
                    return record.content
            return None
        except Exception:
            return None
    
    def _save_analysis_record(self, analyst_name: str, symbol: str, content: str, reason: str):
        """保存分析记录"""
        try:
            record = AnalysisRecord(
                data_type='analysis',
                agent_name=analyst_name,
                symbol=symbol,
                content=content,
                summary=reason,
                status='completed'
            )
            self.db_manager.save_analysis_record(record)
            
        except Exception as e:
            print(f"❌ 保存分析记录失败: {e}")
    
    def generate_research_summary(self, symbol_analyses: Dict[str, Any], 
                                macro_analysis: str, sentiment_analysis: str) -> str:
        """生成研究综合报告"""
        prompt_file = self.prompt_manager.prompts_dir / "research_summary.txt"
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read().strip()
        
        # 格式化币种分析报告
        analysis_reports = self._format_symbol_analyses(symbol_analyses)
        
        prompt = prompt_template.format(
            symbol_reports=analysis_reports, 
            macro_analysis=macro_analysis,
            sentiment_analysis=sentiment_analysis
        )
        
        llm_client = self._get_llm_client_for_analyst('研究部门总监')
        return llm_client.call(prompt, agent_name='研究部门总监')
    
    def _format_symbol_analyses(self, symbol_analyses: Dict[str, Any]) -> str:
        """格式化币种分析报告"""
        lines = []
        for symbol, analysis in symbol_analyses.items():
            lines.extend([
                f"=== {symbol.replace('USDT', '')} 分析报告 ===",
                f"首席分析师: {analysis.get('chief_analysis', '暂无')}",
                ""
            ])
        return '\n'.join(lines)