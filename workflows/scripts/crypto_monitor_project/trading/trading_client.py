# -*- coding: utf-8 -*-
"""
交易客户端
负责与币安期货API交互，执行交易操作
"""

import json
from typing import Dict, List, Any, Optional
from ..config import Settings

try:
    from binance.client import Client
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    Client = None


class TradingClient:
    """币安期货交易客户端"""
    
    def __init__(self, settings: Settings):
        """
        初始化交易客户端
        
        Args:
            settings: 系统配置对象
        """
        self.settings = settings
        self.binance_client = None
        
        if BINANCE_AVAILABLE:
            self._init_binance_client()
        else:
            print("⚠️ 未安装python-binance库，交易功能将不可用")
    
    def _init_binance_client(self):
        """初始化币安客户端"""
        try:
            import os
            api_key = os.getenv('BINANCE_API_KEY')
            api_secret = os.getenv('BINANCE_API_SECRET')
            
            if not api_key or not api_secret:
                print("⚠️ 未配置币安API密钥，交易功能将不可用")
                return
            
            self.binance_client = Client(
                api_key=api_key,
                api_secret=api_secret,
                testnet=self.settings.api.binance_testnet
            )
            
            # 验证API权限
            self._verify_api_permissions()
            
        except Exception as e:
            print(f"❌ 初始化币安客户端失败: {e}")
    
    def _verify_api_permissions(self):
        """验证API权限"""
        try:
            if not self.binance_client:
                return
            
            account_info = self.binance_client.futures_account()
            can_trade = account_info.get('canTrade', False)
            
            if can_trade:
                print("✅ 账户权限验证成功 - 可交易权限: True")
            else:
                print("⚠️ 账户权限验证失败 - 无交易权限")
                
        except Exception as e:
            print(f"❌ API权限验证失败: {e}")
    
    def get_account_balance(self) -> Dict[str, Any]:
        """获取账户余额（期货账户）"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            # 获取期货账户余额
            try:
                account = self.binance_client.futures_account()
                balances = {}
                
                for balance in account.get('assets', []):
                    asset = balance['asset']
                    wallet_balance = float(balance.get('walletBalance', 0))
                    unrealized_profit = float(balance.get('unrealizedProfit', 0))
                    available_balance = float(balance.get('availableBalance', 0))
                    
                    if wallet_balance > 0 or available_balance > 0:
                        balances[asset] = {
                            'free': available_balance,
                            'locked': wallet_balance - available_balance,
                            'total': wallet_balance,
                            'unrealized_profit': unrealized_profit
                        }
                
                return balances
                
            except Exception as futures_error:
                # 备用现货账户
                print(f"⚠️ 期货账户余额获取失败，尝试现货账户: {futures_error}")
                account = self.binance_client.get_account()
                balances = {}
                
                for balance in account['balances']:
                    asset = balance['asset']
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked
                    
                    if total > 0:
                        balances[asset] = {
                            'free': free,
                            'locked': locked,
                            'total': total
                        }
                
                return balances
            
        except Exception as e:
            return {"error": f"获取账户余额失败: {str(e)}"}
    
    def get_current_positions(self) -> List[Dict[str, Any]]:
        """获取当前持仓（永续）"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            positions = self.binance_client.futures_position_information()
            active_positions = []
            
            for pos in positions:
                position_amt = float(pos.get('positionAmt', 0))
                if position_amt != 0:  # 只显示有持仓的
                    entry_price = float(pos.get('entryPrice', 0))
                    mark_price = float(pos.get('markPrice', 0))
                    pnl_value = float(pos.get('unRealizedProfit', 0))
                    
                    # 计算盈亏百分比
                    pnl_pct = 0
                    if entry_price > 0:
                        if position_amt > 0:  # 多头
                            pnl_pct = ((mark_price - entry_price) / entry_price) * 100
                        else:  # 空头
                            pnl_pct = ((entry_price - mark_price) / entry_price) * 100
                    
                    active_positions.append({
                        'symbol': pos.get('symbol', ''),
                        'side': 'LONG' if position_amt > 0 else 'SHORT',
                        'size': abs(position_amt),
                        'entry_price': entry_price,
                        'mark_price': mark_price,
                        'pnl': pnl_value,
                        'pnl_pct': pnl_pct,
                        'margin_type': pos.get('marginType', 'ISOLATED'),
                        'leverage': pos.get('leverage', '1')
                    })
            
            return active_positions
            
        except Exception as e:
            return {"error": f"获取持仓失败: {str(e)}"}
    
    def place_futures_order(self, symbol: str, side: str, quantity: float, 
                           order_type: str = "MARKET", price: Optional[float] = None, 
                           stop_price: Optional[float] = None) -> Dict[str, Any]:
        """下永续订单"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            # 参数验证
            if not symbol or not side or quantity <= 0:
                return {"error": "订单参数无效"}
            
            order_params = {
                'symbol': symbol,
                'side': side.upper(),
                'type': order_type.upper(),
                'quantity': quantity,
            }
            
            if price and order_type.upper() in ['LIMIT', 'STOP']:
                order_params['price'] = price
            
            if stop_price and order_type.upper() in ['STOP_MARKET', 'TAKE_PROFIT_MARKET']:
                order_params['stopPrice'] = stop_price
            
            # 执行订单
            result = self.binance_client.futures_create_order(**order_params)
            
            return {
                'success': True,
                'orderId': result.get('orderId'),
                'symbol': result.get('symbol'),
                'side': result.get('side'),
                'quantity': result.get('origQty'),
                'price': result.get('price'),
                'status': result.get('status')
            }
            
        except Exception as e:
            error_msg = str(e)
            
            # 特殊错误处理
            if "-4061" in error_msg:
                # 订单不存在错误，不算失败
                return {"warning": f"订单操作提示: {error_msg}"}
            
            return {"error": f"下单失败: {error_msg}"}
    
    def get_trading_tools_description(self) -> str:
        """获取可用交易工具描述"""
        return """
可用交易工具:
1. get_account_balance() - 查询账户余额
2. get_current_positions() - 查询当前持仓
3. place_futures_order() - 执行永续合约订单
   - 支持市价单(MARKET)、限价单(LIMIT)
   - 支持止损单(STOP_MARKET)、止盈单(TAKE_PROFIT_MARKET)
4. 风险管理:
   - 最大持仓数: {max_pos}
   - 单笔最大仓位: {max_pos_pct}%
   - 默认杠杆: {default_leverage}倍
""".format(
            max_pos=self.settings.risk.max_positions,
            max_pos_pct=self.settings.risk.max_position_percent,
            default_leverage=self.settings.risk.default_leverage
        )
    
    def is_available(self) -> bool:
        """检查交易客户端是否可用"""
        return self.binance_client is not None