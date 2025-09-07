# -*- coding: utf-8 -*-
"""
投资组合管理器
负责交易决策分析和执行
"""

import json
from typing import Dict, List, Any, Optional

from .trading_client import TradingClient
from ..config import Settings
from ..database import DatabaseManager


class PortfolioManager:
    """投资组合管理器"""
    
    def __init__(self, settings: Settings, db_manager: DatabaseManager, llm_clients: Dict[str, Any]):
        """
        初始化投资组合管理器
        
        Args:
            settings: 系统配置
            db_manager: 数据库管理器
            llm_clients: LLM客户端字典
        """
        self.settings = settings
        self.db_manager = db_manager
        self.llm_clients = llm_clients
        self.trading_client = TradingClient(settings)
    
    def conduct_trading_analysis(self, research_results: Dict[str, Any], question: str) -> str:
        """交易部门：投资组合决策"""
        print("💼 [交易部门] 制定投资组合策略...", flush=True)
        
        # 获取当前账户状态
        print("📊 获取账户信息...", flush=True)
        account_balance = self.trading_client.get_account_balance()
        current_positions = self.trading_client.get_current_positions()
        
        # 打印账户信息
        self._print_account_info(account_balance, current_positions)
        
        # 获取历史交易参考
        recent_research = self._get_recent_chief_analysis(10)
        
        # 交易决策分析
        symbols_analyzed = list(research_results['symbol_analyses'].keys())
        primary_symbol = symbols_analyzed[0] if symbols_analyzed else 'BTCUSDT'
        
        trading_analysis = self._generate_trading_analysis(
            research_results, question, account_balance, current_positions, 
            recent_research, primary_symbol
        )
        
        return trading_analysis
    
    def _print_account_info(self, account_balance: Dict[str, Any], current_positions: List[Dict[str, Any]]):
        """打印账户信息"""
        print("💰 当前账户余额:")
        if 'error' not in account_balance:
            for asset, balance_info in account_balance.items():
                total = balance_info['total']
                if total > 0:
                    if 'unrealized_profit' in balance_info:
                        # 期货账户信息
                        unrealized_pnl = balance_info['unrealized_profit']
                        print(f"  {asset}: 可用={balance_info['free']:.6f}, 冻结={balance_info['locked']:.6f}, 总计={total:.6f}, 未实现盈亏={unrealized_pnl:.6f}")
                    else:
                        # 现货账户信息
                        print(f"  {asset}: 可用={balance_info['free']:.6f}, 冻结={balance_info['locked']:.6f}, 总计={total:.6f}")
        else:
            print(f"  ❌ {account_balance['error']}")
        
        print("📈 当前持仓:")
        if isinstance(current_positions, list) and current_positions:
            for pos in current_positions:
                side = pos['side']
                symbol = pos['symbol']
                size = pos['size']
                pnl = pos['pnl']
                pnl_pct = pos['pnl_pct']
                print(f"  {symbol} {side}: 数量={size}, 盈亏={pnl:.2f}USDT ({pnl_pct:.2f}%)")
        else:
            if isinstance(current_positions, dict) and 'error' in current_positions:
                print(f"  ❌ {current_positions['error']}")
            else:
                print("  ✅ 无持仓")
    
    def _get_recent_chief_analysis(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的首席分析师概要"""
        try:
            records = self.db_manager.get_analysis_records(
                data_type='chief_analysis', 
                agent_name='首席分析师',
                limit=limit
            )
            
            results = []
            for record in records:
                results.append({
                    'timestamp': record.timestamp.isoformat() if record.timestamp else None,
                    'symbol': record.symbol,
                    'summary': record.summary,
                    'content_preview': record.content[:200] if record.content else None
                })
            
            return results
            
        except Exception as e:
            print(f"❌ 获取首席分析历史失败: {e}")
            return []
    
    def _generate_trading_analysis(self, research_results: Dict[str, Any], question: str,
                                 account_balance: Dict[str, Any], current_positions: List[Dict[str, Any]],
                                 recent_research: List[Dict[str, Any]], primary_symbol: str) -> str:
        """生成交易分析"""
        try:
            primary_symbol_name = primary_symbol.replace('USDT', '')
            
            trading_prompt = f"""你是专业的期货交易员，基于研究部门的多币种分析报告，重点针对 {primary_symbol} 制定合约交易策略：

=== 研究部门综合报告 ===
{research_results['research_summary']}

=== 可用交易工具 ===
{self.trading_client.get_trading_tools_description()}

=== 当前账户状态 ===
余额信息: {json.dumps(account_balance, indent=2, ensure_ascii=False)}
当前持仓: {json.dumps(current_positions, indent=2, ensure_ascii=False)}

=== 历史交易参考 ===
{json.dumps(recent_research, indent=2, ensure_ascii=False)}

=== 用户问题 ===
{question}

=== 专业交易原则 ===
1. **严格风险控制**：只在有明确优势的情况下交易
2. **宁缺毋滥**：没有把握不如观望等待更好机会
3. **趋势确认**：技术面、基本面、宏观面至少2个维度一致才考虑交易
4. **合理仓位**：根据置信度和风险调整仓位大小
5. **观望策略**：以下情况应选择HOLD观望：
   - 各维度分析出现明显分歧
   - 市场处于震荡整理阶段，方向不明
   - 技术指标处于中性区间
   - 宏观面存在重大不确定性
   - 当前已有足够仓位，不宜加仓
6. **止盈止损**：每笔交易都要设置明确的止盈止损点位

=== 交易决策要求 ===
请基于以上信息提供具体的交易建议：

1. **交易方向建议**：
   - LONG {primary_symbol_name}：看多，建议开多单
   - SHORT {primary_symbol_name}：看空，建议开空单  
   - HOLD：观望，暂不交易

2. **具体交易参数**（如果建议交易）：
   - 建议仓位大小（占总资金百分比）
   - 建议杠杆倍数
   - 入场点位
   - 止损点位
   - 止盈点位

3. **风险提示**：
   - 主要风险因素
   - 需要关注的市场变化

4. **执行建议**：
   - 是否需要立即执行
   - 还是等待更好的入场时机

请提供专业、具体、可执行的交易建议。"""
            
            # 调用LLM进行交易分析
            llm_client = self._get_trading_llm_client()
            if not llm_client:
                return "❌ LLM客户端未初始化，无法进行交易分析"
            
            response = llm_client.call(trading_prompt, agent_name='交易分析师')
            return f"💼 永续交易员分析报告\n\n{response}"
            
        except Exception as e:
            return f"❌ 交易分析生成失败: {str(e)}"
    
    def _get_trading_llm_client(self):
        """获取交易分析LLM客户端"""
        config = self.settings.api.perpetual_trader
        return self.llm_clients.get(config.provider, self.llm_clients.get('doubao'))
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        return {
            'balance': self.trading_client.get_account_balance(),
            'positions': self.trading_client.get_current_positions(),
            'trading_available': self.trading_client.is_available()
        }
    
    def get_positions(self) -> Dict[str, Any]:
        """获取当前持仓信息"""
        return self.trading_client.get_current_positions()
    
    def execute_trade(self, symbol: str, side: str, quantity: float, 
                     order_type: str = "MARKET", price: Optional[float] = None) -> Dict[str, Any]:
        """执行交易"""
        if not self.trading_client.is_available():
            return {"error": "交易功能不可用"}
        
        return self.trading_client.place_futures_order(symbol, side, quantity, order_type, price)