# -*- coding: utf-8 -*-
"""
交易客户端 - 基于crypto_bot.py的实现
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
    """币安期货交易客户端 - 采用crypto_bot.py的成功实现"""
    
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
        """初始化币安客户端 - 参考crypto_bot.py实现"""
        try:
            import os
            api_key = os.getenv('BINANCE_API_KEY')
            api_secret = os.getenv('BINANCE_API_SECRET')
            testnet = os.getenv('BINANCE_TESTNET', 'false').lower() == 'true'
            
            if not api_key or not api_secret:
                print("⚠️ 未配置币安API密钥，交易功能将不可用")
                return
            
            self.binance_client = Client(
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet
            )
            
            # 测试连接
            self.binance_client.ping()
            print("✅ 交易管理器初始化完成")
            
        except Exception as e:
            print(f"❌ 初始化币安客户端失败: {e}")
            self.binance_client = None
    
    def get_account_balance(self):
        """获取账户余额（期货账户余额）- 来自crypto_bot.py"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            # 期货账户余额
            try:
                account = self.binance_client.futures_account()
                balances = {}
                
                for balance in account.get('assets', []):
                    asset = balance['asset']
                    wallet_balance = float(balance.get('walletBalance', 0))
                    unrealized_profit = float(balance.get('unrealizedProfit', 0))
                    available_balance = float(balance.get('availableBalance', 0))
                    
                    if wallet_balance > 0 or available_balance > 0:  # 显示有余额的币种
                        balances[asset] = {
                            'free': available_balance,
                            'locked': wallet_balance - available_balance,
                            'total': wallet_balance,
                            'unrealized_profit': unrealized_profit
                        }
                
                return {
                    "success": True,
                    "balances": balances,
                    "account_type": "期货账户"
                }
                
            except Exception as futures_error:
                # 如果期货API失败，尝试现货API作为备用
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
                            'total': total,
                            'unrealized_profit': 0
                        }
                
                return {
                    "success": True,
                    "balances": balances,
                    "account_type": "现货账户（备用）"
                }
            
        except Exception as e:
            return {"error": f"获取余额失败: {str(e)}"}
    
    def get_current_positions(self):
        """获取当前持仓（永续）- 来自crypto_bot.py"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            # 获取永续持仓
            positions = self.binance_client.futures_position_information()
            active_positions = []
            
            for pos in positions:
                position_amt = float(pos.get('positionAmt', 0))
                if position_amt != 0:  # 只显示有持仓的
                    # 获取基本信息
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
                        'pnl_value': pnl_value,
                        'pnl_pct': pnl_pct,
                        'notional': abs(position_amt) * mark_price
                    })
            
            return {
                "success": True,
                "positions": active_positions,
                "count": len(active_positions)
            }
            
        except Exception as e:
            return {"error": f"获取持仓失败: {str(e)}"}
    
    def place_futures_order(self, symbol: str, side: str, quantity: float, order_type: str = "MARKET", price: float = None, stop_price: float = None):
        """下永续订单 - 单向持仓模式 - 来自crypto_bot.py"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            # 安全检查
            if quantity <= 0:
                return {"error": "订单数量必须大于0"}
            
            # 构建订单参数（单向持仓模式）
            order_params = {
                'symbol': symbol,
                'side': side.upper(),
                'type': order_type.upper(),
                'quantity': quantity
            }
            
            # 根据订单类型添加价格参数
            if order_type.upper() in ['LIMIT', 'STOP', 'TAKE_PROFIT']:
                if price is None:
                    return {"error": f"{order_type}订单需要指定价格"}
                order_params['price'] = price
                order_params['timeInForce'] = 'GTC'  # Good Till Cancel
            
            if order_type.upper() in ['STOP_MARKET', 'TAKE_PROFIT_MARKET']:
                if stop_price is None:
                    return {"error": f"{order_type}订单需要指定触发价格"}
                order_params['stopPrice'] = stop_price
            
            # 下单
            result = self.binance_client.futures_create_order(**order_params)
            
            return {
                "success": True,
                "order_id": result['orderId'],
                "symbol": result['symbol'],
                "side": result['side'],
                "type": result['type'],
                "status": result['status'],
                "quantity": result['origQty']
            }
            
        except Exception as e:
            error_str = str(e)
            if "-4061" in error_str:
                # -4061: 订单会立即触发，跳过不报错
                return {"info": "订单会立即触发，已跳过"}
            else:
                return {"error": f"下单失败: {error_str}"}
    
    def set_leverage(self, symbol: str, leverage: int):
        """设置杠杆倍数 - 来自crypto_bot.py"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            result = self.binance_client.futures_change_leverage(
                symbol=symbol,
                leverage=leverage
            )
            
            return {
                "success": True,
                "symbol": result['symbol'],
                "leverage": result['leverage']
            }
            
        except Exception as e:
            return {"error": f"设置杠杆失败: {str(e)}"}
    
    def cancel_all_orders(self, symbol: str):
        """取消所有订单 - 来自crypto_bot.py"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            result = self.binance_client.futures_cancel_all_open_orders(symbol=symbol)
            return {"success": True, "cancelled_orders": len(result)}
            
        except Exception as e:
            return {"error": f"取消订单失败: {str(e)}"}
    
    def close_position(self, symbol: str):
        """平仓 - 来自crypto_bot.py"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            # 获取当前持仓
            positions = self.binance_client.futures_position_information(symbol=symbol)
            position = positions[0] if positions else None
            
            if not position:
                return {"error": "未找到持仓信息"}
            
            position_amt = float(position['positionAmt'])
            if position_amt == 0:
                return {"error": "当前无持仓"}
            
            # 平仓：持多仓则卖出，持空仓则买入
            side = 'SELL' if position_amt > 0 else 'BUY'
            quantity = abs(position_amt)
            
            result = self.place_futures_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type='MARKET'
            )
            
            if result.get('success'):
                return {
                    "success": True,
                    "message": f"已平仓 {symbol} {abs(position_amt)} 张",
                    "order_result": result
                }
            else:
                return result
                
        except Exception as e:
            return {"error": f"平仓失败: {str(e)}"}
    
    def test_connectivity(self) -> bool:
        """测试连接"""
        try:
            if not self.binance_client:
                return False
            
            self.binance_client.ping()
            return True
            
        except Exception:
            return False
    
    def is_available(self) -> bool:
        """检查交易客户端是否可用"""
        return self.binance_client is not None and self.test_connectivity()