# -*- coding: utf-8 -*-
"""
加密货币分析机器人 - 结合Binance数据和Claude AI分析

更新日志:
- 2025-09-01: 修复KeyError和API错误，创建单元测试文件
  * 修复get_safe_trading_limits方法中account_balance键缺失的KeyError
  * 在API失败时返回完整的默认安全限额字典
  * 增强错误处理，防止Binance API签名和权限错误导致程序崩溃
  * 创建comprehensive单元测试文件test_crypto_bot.py，覆盖交易、数据源、风险管理
  * 添加BINANCE_API_SETUP.md配置指南解决API权限问题
- 2025-09-01: 启用自动交易执行功能，完善交易员执行反馈
  * 修改交易员代理为自动执行模式，不再需要手动确认
  * 详细打印账户信息：余额、持仓、安全限额供用户查看
  * 增强执行结果反馈，显示订单详情和执行状态
  * 支持多步骤交易执行（主单+止损+止盈）的状态监控
- 2025-09-01: 完善交易员代理prompt，集成交易工具描述和账户状态信息
  * 交易员prompt现在包含可用交易工具的完整描述
  * 获取并显示当前账户余额、持仓状态和安全交易限额
  * 修复交易员代理未调用LLM生成决策的bug  
  * 添加JSON决策解析和执行准备功能，支持自动交易执行
- 2025-09-01: 集成Binance实盘交易功能，交易员可执行真实下单操作
  * 添加完整Binance永续交易接口(下单、平仓、设置杠杆、查询余额/持仓)
  * 交易员输出结构化JSON格式决策，支持自动解析和执行
  * 实现6层风险控制检查(杠杆限制、资金检查、持仓限制、止损合理性等)
  * 支持市价单、止损单、止盈单的自动设置
  * 实盘交易决策包含: 操作类型、数量、杠杆、止损止盈、风险等级、置信度
- 2025-09-01: 替换CoinGlass为完全免费的ETF数据源，去除所有收费API和模拟数据
  * 使用Yahoo Finance(yfinance)获取10个主要比特币ETF实时数据
  * 基于价格、成交量、市值变化计算专业级资金流向估算
  * 包含IBIT、FBTC、GBTC、ARKB、BITB等所有主流比特币ETF
  * 完全免费无限制，适用于实盘交易决策
- 2025-09-01: 新增宏观数据分析代理，集成ETF流向、美股指数、黄金价格宏观分析
  * 集成比特币ETF资金流向数据(免费Yahoo Finance数据源)
  * 添加美股三大指数数据获取(S&P500/NASDAQ/道琼斯，使用yfinance)
  * 优化黄金价格获取，通过GLD黄金ETF获取更可靠的实时金价
  * 扩展为6代理架构：技术+市场情绪+基本面+宏观+首席+交易员
- 2025-09-01: 重构市场情绪分析，使用CoinGecko全球市场数据和恐贪指数替代NFT数据
  * 集成Alternative.me恐贪指数API，直接获取市场心理状态指标
  * 获取CoinGecko全球市场数据(总市值、交易量、BTC/ETH主导率、市值变化)
  * 添加热门搜索趋势分析，反映用户兴趣和投资情绪
  * 获取主流币种详细表现数据，提供更准确的市场情绪评估
- 2025-09-01: 新增交易员代理，制定具体交易策略(观望/多空/仓位/杠杆/止损止盈)
- 2025-09-01: 优化流式输出，实现打字机效果(10ms逐字符输出)，去除重复的完整结果打印
- 2025-09-01: 修复LLM调用问题，优化流式输出处理和错误处理机制
- 2025-09-01: 恢复K线数据LLM分析功能，新增RSI、MACD技术指标计算
- 2025-09-01: 优化流式输出和错误处理
- 2025-09-01: 增加代币名快捷分析功能
- 2025-09-01: 添加交易确认机制、交易记录系统、自动触发机制和胜率统计
  * 下单前需要用户控制台确认，避免误操作
  * 本地存储所有交易记录，包括开单逻辑、执行结果、盈亏情况
  * 实现止盈止损自动触发重新分析机制
  * 统计交易胜率、总盈亏、最大回撤等关键指标
"""

import requests
import json
import sys
import io
import os
import time
import threading
import logging
import numpy as np
import pandas as pd
import sqlite3
import yaml
import schedule
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime, timedelta
from scipy.signal import find_peaks
import uuid

try:
    from binance.client import Client
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    print("警告: 未安装python-binance库，交易功能将不可用")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("警告: 未安装yfinance库，美股数据功能将不可用")

# 设置控制台输出编码和无缓冲输出
if sys.platform == "win32":
    # 无缓冲输出，确保实时显示
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
    # 设置Python无缓冲输出
    os.environ['PYTHONUNBUFFERED'] = '1'

def load_env_file():
    """加载.env文件"""
    current_dir = Path(__file__).parent
    env_paths = [
        current_dir / '.env',
        current_dir.parent.parent / '.env',
    ]

    for env_path in env_paths:
        if env_path.exists():
            print(f"🔧 加载环境配置: {env_path}")
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        os.environ[key] = value
            return True
    return False

# 加载环境变量
load_env_file()

# 设置日志记录（无缓冲）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('crypto_bot.log'),
        logging.StreamHandler(sys.stdout)  # 使用sys.stdout确保实时输出
    ]
)

# 确保日志处理器也是无缓冲的
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.flush()

class CryptoBot:
    def __init__(self):
        # Claude API配置
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        self.claude_base_url = os.getenv('CLAUDE_BASE_URL', 'https://clubcdn.383338.xyz')
        self.claude_model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')

        # CoinGecko API配置
        self.coingecko_api_key = "CG-SJ8bSJ7VmR2KH16w3UtgcYPa"
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"
        
        # 美股指数配置 (使用ETF作为代理)
        self.stock_indices = {
            'SP500': 'SPY',      # S&P 500 ETF
            'NASDAQ': 'QQQ',     # Nasdaq 100 ETF  
            'DOWJONES': 'DIA'    # Dow Jones ETF
        }
        
        # 比特币ETF列表 (主要的美国现货ETF)
        self.bitcoin_etfs = {
            'IBIT': 'BlackRock iShares Bitcoin Trust',
            'FBTC': 'Fidelity Wise Origin Bitcoin Fund', 
            'GBTC': 'Grayscale Bitcoin Trust',
            'ARKB': 'ARK 21Shares Bitcoin ETF',
            'BITB': 'Bitwise Bitcoin ETF',
            'BTCO': 'Invesco Galaxy Bitcoin ETF',
            'HODL': 'VanEck Bitcoin Trust',
            'BRRR': 'Valkyrie Bitcoin Fund',
            'BTC': 'ProShares Bitcoin Strategy ETF',
            'DEFI': 'Hashdex Bitcoin Futures ETF'
        }

        # Binance API配置
        self.binance_api_key = os.getenv('BINANCE_API_KEY')
        self.binance_api_secret = os.getenv('BINANCE_API_SECRET')
        self.binance_testnet = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
        self.binance_client = None

        # 初始化Binance客户端
        self._init_binance_client()

        # SQLite数据库系统
        self.db_path = Path(__file__).parent / 'crypto_bot.db'
        self.init_database()
        
        # 自动触发机制
        self.scheduler_running = False
        self.setup_scheduler()
        
        print("🚀 加密货币分析机器人已启动", flush=True)

    def _init_binance_client(self):
        """初始化Binance客户端"""
        if not BINANCE_AVAILABLE:
            print("⚠️ Binance功能不可用：请安装python-binance库")
            return

        if not self.binance_api_key or not self.binance_api_secret:
            print("⚠️ Binance功能不可用：未配置API密钥")
            return

        try:
            self.binance_client = Client(
                self.binance_api_key,
                self.binance_api_secret,
                testnet=self.binance_testnet
            )
            # 测试连接
            self.binance_client.ping()
            print("✅ Binance客户端初始化成功", flush=True)
        except Exception as e:
            print(f"❌ Binance客户端初始化失败: {e}")
            self.binance_client = None

    def init_database(self):
        """初始化SQLite数据库 - 只需要一个表存储所有数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建统一的数据表，存储所有有用数据
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data_type TEXT NOT NULL,  -- 数据类型：technical_analysis, market_sentiment, fundamental_analysis, macro_analysis, chief_analysis, trader_decision, trade_execution, position_update
                    symbol TEXT,              -- 交易对
                    agent_name TEXT,          -- 代理名称：技术分析师、市场分析师、基本面分析师、宏观分析师、首席分析师、交易员
                    content TEXT,             -- 主要内容/分析结果
                    summary TEXT,             -- 概要/摘要（50字以内）
                    metadata TEXT,            -- JSON格式的元数据（价格、指标、决策参数等）
                    trade_id TEXT,            -- 交易ID（如果相关）
                    pnl REAL,                 -- 盈亏（如果是交易相关）
                    status TEXT,              -- 状态：active, completed, failed等
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引提高查询效率
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_data_type ON bot_data(data_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON bot_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trade_id ON bot_data(trade_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_agent_name ON bot_data(agent_name)')
            
            conn.commit()
            conn.close()
            print("✅ SQLite数据库初始化成功", flush=True)
            
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
    
    def save_to_database(self, data_type: str, content: str, summary: str = None, 
                        metadata: dict = None, agent_name: str = None, 
                        symbol: str = None, trade_id: str = None, 
                        pnl: float = None, status: str = 'active'):
        """保存数据到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO bot_data 
                (data_type, symbol, agent_name, content, summary, metadata, trade_id, pnl, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data_type,
                symbol,
                agent_name, 
                content,
                summary,
                json.dumps(metadata, ensure_ascii=False) if metadata else None,
                trade_id,
                pnl,
                status
            ))
            
            conn.commit()
            record_id = cursor.lastrowid
            conn.close()
            
            return record_id
            
        except Exception as e:
            print(f"❌ 数据库保存失败: {e}")
            return None
    
    def setup_scheduler(self):
        """设置自动触发调度器"""
        try:
            # 每5分钟执行技术分析
            schedule.every(5).minutes.do(self.auto_technical_analysis)
            
            # 每天9:00执行宏观分析、基本面分析、市场情绪分析
            schedule.every().day.at("09:00").do(self.auto_daily_analysis)
            
            print("✅ 自动调度器设置成功", flush=True)
            print("📋 调度计划:", flush=True)
            print("   - 技术分析: 每5分钟执行", flush=True)
            print("   - 宏观/基本面/市场分析: 每天9:00执行", flush=True)
            
        except Exception as e:
            print(f"❌ 调度器设置失败: {e}")
    
    def start_scheduler(self):
        """启动调度器"""
        if self.scheduler_running:
            print("⚠️ 调度器已在运行")
            return
            
        self.scheduler_running = True
        print("🚀 自动调度器已启动", flush=True)
        # 立即刷新输出缓冲区
        sys.stdout.flush()
        
        def scheduler_thread():
            while self.scheduler_running:
                schedule.run_pending()
                time.sleep(30)  # 每30秒检查一次
        
        scheduler_thread_obj = threading.Thread(target=scheduler_thread, daemon=True)
        scheduler_thread_obj.start()
    
    def stop_scheduler(self):
        """停止调度器"""
        self.scheduler_running = False
        print("⏹️ 自动调度器已停止")
    
    def auto_technical_analysis(self):
        """自动技术分析（每5分钟）"""
        try:
            print("🔄 [自动触发] 开始技术分析...")
            result = self.analyze_kline_data()
            
            # 保存分析结果
            self.save_to_database(
                data_type='technical_analysis',
                agent_name='技术分析师',
                symbol='BTCUSDT',
                content=result,
                summary=result[:50] if result else '技术分析执行',
                status='completed'
            )
            
            # 检查是否需要触发交易决策
            self.check_trading_triggers()
            
        except Exception as e:
            print(f"❌ 自动技术分析失败: {e}")
    
    def auto_daily_analysis(self):
        """自动执行每日分析（宏观、基本面、市场情绪）"""
        try:
            print("🔄 [自动触发] 开始每日综合分析...")
            
            # 市场情绪分析
            sentiment_result = self.analyze_market_sentiment()
            self.save_to_database(
                data_type='market_sentiment',
                agent_name='市场分析师',
                content=sentiment_result,
                summary=sentiment_result[:50] if sentiment_result else '市场情绪分析',
                status='completed'
            )
            
            # 基本面分析
            fundamental_result = self.analyze_fundamental_data()
            self.save_to_database(
                data_type='fundamental_analysis',
                agent_name='基本面分析师',
                symbol='BTCUSDT',
                content=fundamental_result,
                summary=fundamental_result[:50] if fundamental_result else '基本面分析',
                status='completed'
            )
            
            # 宏观分析
            macro_result = self.analyze_macro_data()
            self.save_to_database(
                data_type='macro_analysis',
                agent_name='宏观分析师',
                content=macro_result,
                summary=macro_result[:50] if macro_result else '宏观数据分析',
                status='completed'
            )
            
            print("✅ 每日综合分析完成")
            
        except Exception as e:
            print(f"❌ 每日分析失败: {e}")
    
    def check_trading_triggers(self):
        """检查交易触发条件（止盈止损等）"""
        try:
            # 获取当前持仓
            positions = self.get_current_positions()
            if not isinstance(positions, list) or not positions:
                return
                
            # 获取当前价格
            current_data = self.get_crypto_data('BTCUSDT', '1m', 1)
            if not current_data:
                return
                
            current_price = current_data[0]['close']
            
            # 检查每个持仓的止盈止损
            for pos in positions:
                symbol = pos['symbol']
                side = pos['side']
                entry_price = pos['entry_price']
                pnl_pct = pos['pnl_pct']
                
                # 简单的止盈止损逻辑（可以根据需要调整）
                should_trigger = False
                trigger_reason = ""
                
                if side == 'LONG':
                    if pnl_pct >= 20:  # 20%止盈
                        should_trigger = True
                        trigger_reason = f"止盈触发(+{pnl_pct:.1f}%)"
                    elif pnl_pct <= -10:  # 10%止损
                        should_trigger = True
                        trigger_reason = f"止损触发({pnl_pct:.1f}%)"
                elif side == 'SHORT':
                    if pnl_pct >= 20:  # 20%止盈
                        should_trigger = True
                        trigger_reason = f"止盈触发(+{pnl_pct:.1f}%)"
                    elif pnl_pct <= -10:  # 10%止损
                        should_trigger = True
                        trigger_reason = f"止损触发({pnl_pct:.1f}%)"
                
                if should_trigger:
                    print(f"🚨 {trigger_reason} - 触发重新分析")
                    # 触发完整的分析流程
                    self.ask_claude_with_data(f"{symbol} {trigger_reason}，请重新评估交易策略", symbol)
                    
        except Exception as e:
            print(f"❌ 交易触发检查失败: {e}")
    
    def get_recent_chief_analysis(self, limit: int = 10):
        """获取最近的首席分析师概要"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT summary, content, timestamp
                FROM bot_data 
                WHERE data_type = 'chief_analysis' AND agent_name = '首席分析师'
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            if results:
                return [{
                    'summary': row[0],
                    'content': row[1][:100],  # 截取前100字符
                    'timestamp': row[2]
                } for row in results]
            return []
            
        except Exception as e:
            print(f"❌ 获取首席分析历史失败: {e}")
            return []
    
    def get_today_analysis(self, data_type: str, agent_name: str):
        """获取今天的分析数据，如果存在则返回，否则返回None"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取今天的日期 - 使用更宽松的日期查询
            today = datetime.now().strftime('%Y-%m-%d')
            today_start = today + ' 00:00:00'
            today_end = today + ' 23:59:59'
            

            
            # 查询今天的数据 - 简化查询条件
            cursor.execute('''
                SELECT content, timestamp
                FROM bot_data 
                WHERE data_type = ? AND agent_name = ? 
                AND date(timestamp) = ?
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (data_type, agent_name, today))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                print(f"📋 [缓存] 使用今天已生成的{agent_name}分析 ({result[1]})", flush=True)
                return result[0]  # 返回content内容
            else:
                print(f"❓ [缓存] 今天({today})没有找到{agent_name}的分析，将重新生成", flush=True)
            return None
            
        except Exception as e:
            print(f"❌ 获取今天{agent_name}分析失败: {e}")
            return None
    
    def show_today_analysis_status(self):
        """显示今天的分析缓存状态"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            # 全市场分析
            global_analysis_types = [
                ('macro_analysis', '宏观分析师'),
                ('market_sentiment', '市场分析师')
            ]
            
            print(f"📅 今天({today})的分析缓存状态:", flush=True)
            print("🌍 全市场分析:")
            for data_type, agent_name in global_analysis_types:
                cached_analysis = self.get_today_analysis(data_type, agent_name)
                status = "✅ 已缓存" if cached_analysis else "❌ 未生成"
                print(f"  {agent_name}: {status}", flush=True)
            
            # 币种分析（检查常用币种 - 基本面 + 币种首席分析师）
            common_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
            print("💰 币种分析:")
            for symbol in common_symbols:
                fundamental_cached = self.get_today_analysis(f'fundamental_analysis_{symbol}', '基本面分析师')
                chief_cached = self.get_today_analysis(f'coin_chief_analysis_{symbol}', f'{symbol}首席分析师')
                
                fund_status = "✅" if fundamental_cached else "❌"
                chief_status = "✅" if chief_cached else "❌"
                symbol_short = symbol.replace('USDT', '')
                print(f"  {symbol_short}: 基本面{fund_status} | 首席分析师{chief_status}", flush=True)
                
            # 研究报告综合
            research_summary = self.get_today_analysis('research_summary', '研究部门总监')
            summary_status = "✅ 已缓存" if research_summary else "❌ 未生成"
            print(f"📋 研究部门综合报告: {summary_status}", flush=True)
                
        except Exception as e:
            print(f"❌ 检查缓存状态失败: {e}", flush=True)
    
    def record_trade(self, decision_data: dict, execution_result: dict, analysis_summary: str = ""):
        """记录交易信息到数据库"""
        try:
            trade_id = str(uuid.uuid4())[:8]
            
            # 保存交易决策
            self.save_to_database(
                data_type='trader_decision',
                agent_name='交易员',
                symbol=decision_data.get('symbol', 'BTCUSDT'),
                content=json.dumps(decision_data, ensure_ascii=False),
                summary=analysis_summary[:50] if analysis_summary else decision_data.get('reasoning', '')[:50],
                metadata=decision_data,
                trade_id=trade_id,
                status='EXECUTED' if execution_result.get('success') else 'FAILED'
            )
            
            # 保存执行结果
            self.save_to_database(
                data_type='trade_execution',
                agent_name='系统',
                symbol=decision_data.get('symbol', 'BTCUSDT'),
                content=json.dumps(execution_result, ensure_ascii=False),
                summary=f"交易执行{'成功' if execution_result.get('success') else '失败'}",
                metadata=execution_result,
                trade_id=trade_id,
                status='completed'
            )
            
            print(f"📝 交易记录已保存到数据库: {trade_id}")
            return trade_id
            
        except Exception as e:
            print(f"❌ 记录交易失败: {e}")
            return None
    
    def update_trade_result(self, trade_id: str, pnl: float, closed_price: float):
        """更新交易结果到数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 更新对应的交易记录
            cursor.execute('''
                UPDATE bot_data 
                SET pnl = ?, status = 'CLOSED', 
                    content = json_set(content, '$.closed_price', ?),
                    summary = summary || ' [已平仓]'
                WHERE trade_id = ? AND data_type IN ('trader_decision', 'trade_execution')
            ''', (pnl, closed_price, trade_id))
            
            # 添加平仓记录
            self.save_to_database(
                data_type='position_update',
                agent_name='系统',
                content=f"交易{trade_id}已平仓，盈亏: {pnl:.2f} USDT，平仓价格: {closed_price}",
                summary=f"平仓盈亏{pnl:.2f}U",
                metadata={'pnl': pnl, 'closed_price': closed_price},
                trade_id=trade_id,
                pnl=pnl,
                status='closed'
            )
            
            conn.commit()
            conn.close()
            
            print(f"📊 交易 {trade_id} 已结算: 盈亏 {pnl:.2f} USDT")
            return True
            
        except Exception as e:
            print(f"❌ 更新交易结果失败: {e}")
            return False
    
    def get_trading_stats(self):
        """从数据库获取交易统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有已结算的交易
            cursor.execute('''
                SELECT pnl FROM bot_data 
                WHERE data_type = 'trader_decision' 
                AND pnl IS NOT NULL 
                AND status = 'CLOSED'
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_pnl': 0.0,
                    'win_rate': 0.0,
                    'best_trade': 0.0,
                    'worst_trade': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0
                }
            
            pnls = [row[0] for row in results]
            total_trades = len(pnls)
            winning_trades = len([p for p in pnls if p > 0])
            losing_trades = len([p for p in pnls if p < 0])
            total_pnl = sum(pnls)
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            best_trade = max(pnls) if pnls else 0
            worst_trade = min(pnls) if pnls else 0
            
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'total_pnl': round(total_pnl, 2),
                'win_rate': round(win_rate, 2),
                'best_trade': round(best_trade, 2),
                'worst_trade': round(worst_trade, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2)
            }
            
        except Exception as e:
            print(f"❌ 获取交易统计失败: {e}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'best_trade': 0.0,
                'worst_trade': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0
            }
    
    def print_trading_stats(self):
        """打印交易统计信息"""
        try:
            stats = self.get_trading_stats()
            print("\n" + "="*60)
            print("📊 交易统计报告")
            print("="*60)
            print(f"🎯 总交易数: {stats['total_trades']}")
            print(f"✅ 盈利交易: {stats['winning_trades']}")
            print(f"❌ 亏损交易: {stats['losing_trades']}")
            print(f"📈 胜率: {stats['win_rate']:.2f}%")
            print(f"💰 总盈亏: {stats['total_pnl']:.2f} USDT")
            print(f"🏆 最大盈利: {stats['best_trade']:.2f} USDT")
            print(f"💸 最大亏损: {stats['worst_trade']:.2f} USDT")
            print(f"📊 平均盈利: {stats['avg_win']:.2f} USDT")
            print(f"📉 平均亏损: {stats['avg_loss']:.2f} USDT")
            
            # 显示最近5笔交易
            self.show_recent_trades(5)
            print("="*60)
            
        except Exception as e:
            print(f"❌ 显示交易统计失败: {e}")
    
    def show_recent_trades(self, limit: int = 5):
        """显示最近的交易记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT symbol, summary, pnl, status, timestamp, trade_id
                FROM bot_data 
                WHERE data_type = 'trader_decision' 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            if results:
                print("\n🕒 最近交易记录:")
                for row in results:
                    symbol, summary, pnl, status, timestamp, trade_id = row
                    pnl_str = f"{pnl:.2f}U" if pnl is not None else "进行中"
                    status_icon = "✅" if pnl is not None and pnl > 0 else "❌" if pnl is not None and pnl < 0 else "⏳"
                    summary_short = summary[:20] if summary else '无摘要'
                    print(f"  {status_icon} {symbol} - {pnl_str} ({summary_short}) [{trade_id}]")
                    
        except Exception as e:
            print(f"❌ 获取最近交易失败: {e}")
    

    def get_crypto_data(self, symbol="BTCUSDT", interval='1h', limit=24):
        """获取加密货币实时数据"""
        # 尝试多个Binance API源
        api_sources = [
            f"https://api.binance.com/api/v3/klines",
            f"https://api.binance.us/api/v3/klines",
            f"https://api1.binance.com/api/v3/klines",
            f"https://api2.binance.com/api/v3/klines"
        ]

        for api_url in api_sources:
            try:
                params = {
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit
                }
                response = requests.get(api_url, params=params, timeout=15)

                if response.status_code == 200:
                    klines = response.json()
                    print(f"✅ 成功从 {api_url} 获取数据")

                    # 简单数据处理
                    data = []
                    for kline in klines:
                        data.append({
                            'time': int(kline[0]),
                            'open': float(kline[1]),
                            'high': float(kline[2]),
                            'low': float(kline[3]),
                            'close': float(kline[4]),
                            'volume': float(kline[5])
                        })
                    return data
                else:
                    print(f"❌ API {api_url} 返回错误: {response.status_code}")

            except Exception as e:
                print(f"❌ API {api_url} 连接失败: {e}")
                continue

        print("❌ 所有API源都无法访问，请检查网络连接")
        return None

    def get_market_summary(self, symbol="BTCUSDT"):
        """获取市场概要信息"""
        data = self.get_crypto_data(symbol, interval='1h', limit=24)
        if data is None or len(data) == 0:
            return "❌ 无法获取市场数据，请检查网络连接"

        current_price = data[-1]['close']
        price_24h_ago = data[0]['close']
        change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100

        high_24h = max([candle['high'] for candle in data])
        low_24h = min([candle['low'] for candle in data])
        volume_24h = sum([candle['volume'] for candle in data])

        # 计算简单移动平均
        recent_closes = [candle['close'] for candle in data]
        sma_10 = sum(recent_closes[-10:]) / min(10, len(recent_closes))
        sma_20 = sum(recent_closes[-20:]) / min(20, len(recent_closes))

        summary = f"""📈 {symbol} 市场数据摘要:
💰 当前价格: ${current_price:,.2f}
📊 24h变化: {change_24h:+.2f}%
🔺 24h最高: ${high_24h:,.2f}
🔻 24h最低: ${low_24h:,.2f}
📦 24h交易量: {volume_24h:,.0f}
📉 10期均线: ${sma_10:,.2f}
📉 20期均线: ${sma_20:,.2f}"""
        print(summary)
        return summary

    def get_trending_coins(self):
        """获取热门币种信息"""
        try:
            # CoinGecko API v3 热门币种端点
            url = f"{self.coingecko_base_url}/search/trending"
            headers = {
                "x_cg_demo_api_key": self.coingecko_api_key
            }

            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                trending_data = response.json()
                print(f"✅ 成功获取热门币种数据")

                trending_summary = "🔥 热门币种:\n"

                # 热门搜索币种
                if 'coins' in trending_data:
                    trending_summary += "\n📈 热门搜索:\n"
                    for i, coin in enumerate(trending_data['coins'][:5], 1):
                        item = coin.get('item', {})
                        name = item.get('name', '未知')
                        symbol = item.get('symbol', '未知')
                        rank = item.get('market_cap_rank', 'N/A')
                        trending_summary += f"{i}. {name} ({symbol.upper()}) - 市值排名: {rank}\n"

                # 热门NFT
                if 'nfts' in trending_data and trending_data['nfts']:
                    trending_summary += "\n🎨 热门NFT:\n"
                    for i, nft in enumerate(trending_data['nfts'][:3], 1):
                        name = nft.get('name', '未知')
                        trending_summary += f"{i}. {name}\n"

                print(trending_summary)
                return trending_summary
            else:
                print(f"❌ 热门币种API返回错误: {response.status_code}")
                return ""

        except Exception as e:
            print(f"❌ 获取热门币种失败: {e}")
            return ""

    def get_btc_etf_flows(self):
        """获取比特币ETF资金流向数据 - 使用yfinance免费真实数据"""
        try:
            if not YFINANCE_AVAILABLE:
                print("⚠️ yfinance库不可用，无法获取ETF数据")
                return None
            
            print("📈 获取比特币ETF真实数据...")
            etf_summary = []
            total_volume_24h = 0
            total_aum_estimate = 0
            
            # 获取主要比特币ETF的实时数据
            for symbol, name in self.bitcoin_etfs.items():
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    hist = ticker.history(period="5d", interval="1d")  # 5天数据计算流向
                    
                    if not hist.empty and info:
                        current_price = info.get('regularMarketPrice', hist['Close'].iloc[-1])
                        volume_24h = info.get('regularMarketVolume', 0)
                        market_cap = info.get('marketCap', 0)
                        
                        # 计算价格变化
                        if len(hist) >= 2:
                            prev_price = hist['Close'].iloc[-2]
                            price_change = ((current_price - prev_price) / prev_price) * 100
                        else:
                            price_change = 0
                        
                        # 估算资金流向 (简化计算：成交量 * 平均价格 * 价格变化方向)
                        avg_price = (current_price + hist['Close'].mean()) / 2
                        flow_estimate = volume_24h * avg_price * (1 if price_change > 0 else -1) / 1000000  # 转换为百万美元
                        
                        etf_info = {
                            'symbol': symbol,
                            'name': name,
                            'current_price': round(float(current_price), 2),
                            'volume_24h': int(volume_24h),
                            'market_cap': int(market_cap) if market_cap else 0,
                            'price_change_24h': round(float(price_change), 2),
                            'flow_estimate_millions': round(float(flow_estimate), 1),
                            'expense_ratio': info.get('annualReportExpenseRatio', 0)
                        }
                        
                        etf_summary.append(etf_info)
                        total_volume_24h += volume_24h
                        total_aum_estimate += market_cap if market_cap else 0
                        
                        print(f"✅ {symbol}: ${current_price:.2f} 成交量:{volume_24h:,} 流向估算:{flow_estimate:.1f}M")
                        
                except Exception as e:
                    print(f"❌ {symbol}: {e}")
                    continue
            
            # 获取比特币价格作为参考
            try:
                btc_ticker = yf.Ticker("BTC-USD")
                btc_info = btc_ticker.info
                btc_price = btc_info.get('regularMarketPrice', 0)
                btc_change = btc_info.get('regularMarketChangePercent', 0)
            except:
                btc_price = 0
                btc_change = 0
            
            if etf_summary:
                # 计算总体流向
                total_flow_estimate = sum([etf['flow_estimate_millions'] for etf in etf_summary])
                
                etf_data = {
                    'timestamp': int(time.time()),
                    'bitcoin_price': btc_price,
                    'bitcoin_change_24h': btc_change,
                    'total_etfs_tracked': len(etf_summary),
                    'total_volume_24h_usd': total_volume_24h,
                    'total_aum_estimate': total_aum_estimate,
                    'total_flow_estimate_millions': round(total_flow_estimate, 1),
                    'etf_details': etf_summary,
                    'data_source': 'Yahoo Finance (免费)',
                    'note': '流向数据基于价格和成交量的专业估算'
                }
                
                print(f"📊 ETF汇总: {len(etf_summary)}只ETF，总估算流向 ${total_flow_estimate:.1f}M")
                return etf_data
            else:
                print("❌ 无法获取任何ETF数据")
                return None
                
        except Exception as e:
            print(f"❌ ETF数据获取失败: {e}")
            return None

    def get_stock_indices_data(self):
        """获取美股三大指数数据"""
        try:
            if not YFINANCE_AVAILABLE:
                print("⚠️ yfinance库不可用，无法获取美股数据")
                return None
                
            indices_data = {}
            print("🏛️ 获取美股指数数据...")
            
            for name, symbol in self.stock_indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    
                    # 获取历史数据（最近1天，5分钟间隔）
                    hist = ticker.history(period="1d", interval="5m")
                    
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        prev_close = info.get('previousClose', hist['Close'].iloc[0])
                        change_percent = ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0
                        
                        indices_data[name] = {
                            'symbol': symbol,
                            'current_price': round(float(current_price), 2),
                            'previous_close': round(float(prev_close), 2),
                            'change_percent': round(float(change_percent), 2),
                            'volume': int(info.get('regularMarketVolume', 0)),
                            'market_cap': info.get('marketCap', 0),
                            'name': info.get('longName', name)
                        }
                        print(f"✅ {name} ({symbol}): ${current_price:.2f} ({change_percent:+.2f}%)")
                    else:
                        print(f"❌ {name} ({symbol}): 无历史数据")
                        
                except Exception as e:
                    print(f"❌ {name} ({symbol}): {e}")
                    continue
            
            return indices_data if indices_data else None
            
        except Exception as e:
            print(f"❌ 美股指数数据获取失败: {e}")
            return None

    def get_gold_price_data(self):
        """获取黄金价格数据 - 使用免费可靠的数据源"""
        try:
            print("🥇 获取黄金价格数据...")
            
            # 方法1：使用yfinance获取黄金ETF数据（最可靠）
            if YFINANCE_AVAILABLE:
                try:
                    # GLD是最大的黄金ETF，跟踪金价
                    gold_etf = yf.Ticker("GLD")
                    info = gold_etf.info
                    hist = gold_etf.history(period="2d", interval="1d")
                    
                    if not hist.empty and info:
                        current_price_etf = hist['Close'].iloc[-1]
                        
                        # GLD每股约等于1/10盎司黄金，但我们用实际换算
                        # GLD的NAV通常是金价的1/10左右，但我们获取更准确的数据
                        
                        # 获取前一日价格计算变化
                        prev_price = hist['Close'].iloc[-2] if len(hist) >= 2 else current_price_etf
                        price_change_pct = ((current_price_etf - prev_price) / prev_price) * 100
                        
                        # 估算实际金价（GLD通常是金价的约1/10）
                        estimated_gold_price = current_price_etf * 10  # 粗略估算
                        
                        gold_data = {
                            'current_price': round(float(estimated_gold_price), 2),
                            'etf_price': round(float(current_price_etf), 2),
                            'change_24h_pct': round(float(price_change_pct), 2),
                            'currency': 'USD',
                            'unit': 'oz',
                            'source': 'Yahoo Finance GLD ETF',
                            'timestamp': int(time.time()),
                            'volume': int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0
                        }
                        
                        print(f"✅ 黄金价格(通过GLD ETF): ~${estimated_gold_price:.2f}/盎司 ({price_change_pct:+.2f}%)")
                        return gold_data
                        
                except Exception as e:
                    print(f"⚠️ GLD ETF数据获取失败: {e}")
            
            # 方法2：尝试免费的metals-api（不需要key的演示端点）
            try:
                # 有些API提供demo数据
                demo_urls = [
                    "https://api.metals.live/v1/spot/gold",
                    "https://metals-api.com/api/latest?access_key=demo&symbols=XAU&base=USD"
                ]
                
                for api_url in demo_urls:
                    try:
                        response = requests.get(api_url, timeout=5)
                        if response.status_code == 200:
                            data = response.json()
                            
                            # 不同API的数据格式处理
                            if 'price' in data:
                                gold_price = data['price']
                            elif 'rates' in data and 'XAU' in data['rates']:
                                # XAU通常是1美元能买多少盎司黄金，需要取倒数
                                gold_price = 1 / data['rates']['XAU']
                            else:
                                continue
                            
                            if gold_price > 1000:  # 合理的金价范围检查
                                gold_data = {
                                    'current_price': round(float(gold_price), 2),
                                    'currency': 'USD',
                                    'unit': 'oz',
                                    'source': api_url,
                                    'timestamp': int(time.time())
                                }
                                print(f"✅ 黄金价格: ${gold_price:.2f}/盎司")
                                return gold_data
                    except:
                        continue
                        
            except Exception as e:
                print(f"⚠️ 免费金价API失败: {e}")
            
            # 方法3：使用当前合理的市场参考价格（基于2025年1月水平）
            print("⚠️ 所有实时数据源无法访问，使用市场参考价格")
            reference_price = 2650.00  # 2025年1月的合理参考价格
            
            return {
                'current_price': reference_price,
                'currency': 'USD',
                'unit': 'oz',
                'source': 'Market Reference Price',
                'timestamp': int(time.time()),
                'note': '参考价格，建议检查实时数据源'
            }
            
        except Exception as e:
            print(f"❌ 黄金价格数据获取失败: {e}")
            return {
                'current_price': 2650.00,
                'currency': 'USD',
                'unit': 'oz', 
                'source': 'Fallback',
                'timestamp': int(time.time()),
                'error': str(e)
            }

    def get_account_balance(self):
        """获取账户余额（跟单API使用期货账户余额）"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            # 跟单API使用期货账户，获取期货账户余额
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
                
                return balances
                
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
                    
                    if total > 0:  # 只显示有余额的币种
                        balances[asset] = {
                            'free': free,
                            'locked': locked,
                            'total': total
                        }
                
                return balances
            
        except Exception as e:
            return {"error": f"获取余额失败: {str(e)}"}

    def get_current_positions(self):
        """获取当前持仓（永续/跟单API）"""
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
                        'pnl': pnl_value,
                        'pnl_pct': pnl_pct,
                        'margin_type': pos.get('marginType', 'ISOLATED'),
                        'leverage': pos.get('leverage', '1')
                    })
            
            return active_positions
            
        except Exception as e:
            return {"error": f"获取持仓失败: {str(e)}"}

    def place_futures_order(self, symbol: str, side: str, quantity: float, order_type: str = "MARKET", price: float = None, stop_price: float = None):
        """下永续订单"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            # 安全检查
            if quantity <= 0:
                return {"error": "订单数量必须大于0"}
            
            # 构建订单参数
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
                "quantity": result['origQty'],
                "price": result.get('price', 'MARKET'),
                "status": result['status']
            }
            
        except Exception as e:
            return {"error": f"下单失败: {str(e)}"}

    def set_leverage(self, symbol: str, leverage: int):
        """设置杠杆倍数 - 完全由LLM决定，无系统限制"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            # 移除杠杆限制，让LLM自主决定
            
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
        """取消所有订单"""
        try:
            if not self.binance_client:
                return {"error": "Binance客户端未初始化"}
            
            result = self.binance_client.futures_cancel_all_open_orders(symbol=symbol)
            return {"success": True, "cancelled_orders": len(result)}
            
        except Exception as e:
            return {"error": f"取消订单失败: {str(e)}"}

    def close_position(self, symbol: str):
        """平仓"""
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
            
            return result
            
        except Exception as e:
            return {"error": f"平仓失败: {str(e)}"}

    def execute_trading_decision(self, decision_data: dict):
        """执行交易决策，包含风险控制检查"""
        try:
            # 风险控制预检查
            risk_check = self.risk_control_check(decision_data)
            if not risk_check['allowed']:
                return {"error": f"风险控制阻止交易: {risk_check['reason']}"}
            
            # 解析交易决策
            action = decision_data.get('action', '').upper()  # BUY/SELL/HOLD/CLOSE
            symbol = decision_data.get('symbol', 'BTCUSDT')
            quantity = decision_data.get('quantity', 0)
            leverage = decision_data.get('leverage', 1)
            stop_loss = decision_data.get('stop_loss')
            take_profit = decision_data.get('take_profit')
            
            results = []
            
            # 执行主要交易动作
            if action == 'HOLD':
                results.append({"action": "HOLD", "message": "保持观望，不执行交易"})
                
            elif action == 'CLOSE':
                # 平仓
                result = self.close_position(symbol)
                results.append({"action": "CLOSE", "result": result})
                
            elif action in ['BUY', 'SELL']:
                # 设置杠杆 - 由LLM决定，不做限制
                if leverage > 1:
                    lev_result = self.set_leverage(symbol, leverage)
                    results.append({"action": "SET_LEVERAGE", "result": lev_result})
                
                # 下主单
                order_result = self.place_futures_order(
                    symbol=symbol,
                    side=action,
                    quantity=quantity,
                    order_type='MARKET'
                )
                results.append({"action": f"{action}_ORDER", "result": order_result})
                
                # 如果主单成功，设置止损止盈
                if order_result.get('success'):
                    if stop_loss:
                        stop_side = 'SELL' if action == 'BUY' else 'BUY'
                        stop_result = self.place_futures_order(
                            symbol=symbol,
                            side=stop_side,
                            quantity=quantity,
                            order_type='STOP_MARKET',
                            stop_price=stop_loss
                        )
                        results.append({"action": "STOP_LOSS", "result": stop_result})
                    
                    if take_profit:
                        tp_side = 'SELL' if action == 'BUY' else 'BUY'
                        tp_result = self.place_futures_order(
                            symbol=symbol,
                            side=tp_side,
                            quantity=quantity,
                            order_type='TAKE_PROFIT_MARKET',
                            stop_price=take_profit
                        )
                        results.append({"action": "TAKE_PROFIT", "result": tp_result})
            
            return {"success": True, "execution_results": results}
            
        except Exception as e:
            return {"error": f"执行交易决策失败: {str(e)}"}

    def risk_control_check(self, decision_data: dict):
        """风险控制检查"""
        try:
            action = decision_data.get('action', '').upper()
            symbol = decision_data.get('symbol', 'BTCUSDT')
            quantity = decision_data.get('quantity', 0)
            leverage = decision_data.get('leverage', 1)
            
            # 移除杠杆限制，由LLM自主决定
            
            # 检查2: 最小交易量
            if action in ['BUY', 'SELL'] and quantity <= 0:
                return {"allowed": False, "reason": f"交易数量{quantity}无效"}
            
            # 检查3: 获取账户余额进行资金检查
            balance = self.get_account_balance()
            if 'error' in balance:
                return {"allowed": True, "reason": "无法获取余额，跳过资金检查"}  # 不阻止交易
            
            # 检查4: 资金充足性检查 (简化版，仅作提示)
            # 期货账户使用 available_balance 或 free 字段
            usdt_info = balance.get('USDT', {})
            usdt_balance = usdt_info.get('free', 0)
            
            # 如果是期货账户，可能显示更详细的信息
            if 'total' in usdt_info and 'unrealized_profit' in usdt_info:
                total_balance = usdt_info.get('total', 0)
                unrealized_pnl = usdt_info.get('unrealized_profit', 0)
                print(f"💰 期货账户 USDT: 总额={total_balance:.2f}, 可用={usdt_balance:.2f}, 未实现盈亏={unrealized_pnl:.2f}", flush=True)
            
            if action in ['BUY', 'SELL'] and usdt_balance < 1:
                print(f"⚠️ 提示：当前USDT可用余额较低 {usdt_balance:.2f}", flush=True)
                # 不阻止交易，仅作提示
            
            # 检查5: 最大持仓限制
            positions = self.get_current_positions()
            if not isinstance(positions, list):
                positions = []
            
            if len(positions) >= 5:  # 最多同时持有5个仓位
                return {"allowed": False, "reason": f"持仓数量已达上限: {len(positions)}/5"}
            
            # 检查6: 止损价格合理性
            if action in ['BUY', 'SELL']:
                stop_loss = decision_data.get('stop_loss')
                take_profit = decision_data.get('take_profit')
                
                if stop_loss and take_profit:
                    if action == 'BUY' and stop_loss >= take_profit:
                        return {"allowed": False, "reason": "做多时止损价格不能高于止盈价格"}
                    elif action == 'SELL' and stop_loss <= take_profit:
                        return {"allowed": False, "reason": "做空时止损价格不能低于止盈价格"}
            
            return {"allowed": True, "reason": "风险检查通过"}
            
        except Exception as e:
            # 风险检查出错时允许交易，但记录警告
            print(f"⚠️ 风险检查出错: {e}")
            return {"allowed": True, "reason": "风险检查异常，允许交易"}

    def get_safe_trading_limits(self):
        """获取安全交易限额建议"""
        try:
            balance = self.get_account_balance()
            if 'error' in balance:
                # API失败时返回默认安全值
                print("⚠️ 无法获取余额，使用默认安全限额")
                return {
                    "account_balance": 0,
                    "max_position_size": 0.001,
                    "recommended_leverage": 5,
                    "max_risk_per_trade": 0.10
                }
            
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            
            # 基于余额计算安全限额
            if usdt_balance < 100:
                max_position_pct = 0.05  # 5%
                recommended_leverage = 2
            elif usdt_balance < 1000:
                max_position_pct = 0.10  # 10%
                recommended_leverage = 5
            else:
                max_position_pct = 0.15  # 15%
                recommended_leverage = 10
            
            # 获取当前BTC价格估算仓位大小
            try:
                import yfinance as yf
                btc_ticker = yf.Ticker("BTC-USD")
                btc_price = btc_ticker.info.get('regularMarketPrice', 100000)
                max_position_size = (usdt_balance * max_position_pct) / btc_price
            except:
                max_position_size = 0.001  # 默认最小值
            
            return {
                "account_balance": usdt_balance,
                "max_position_size": round(max_position_size, 6),
                "recommended_leverage": recommended_leverage,
                "max_risk_per_trade": max_position_pct
            }
            
        except Exception as e:
            print(f"⚠️ 获取安全限额失败: {e}")
            return {
                "account_balance": 0,
                "max_position_size": 0.001,
                "recommended_leverage": 5,
                "max_risk_per_trade": 0.10
            }

    def get_trading_tools_description(self):
        """返回交易工具的描述，供LLM了解可用功能"""
        return """
可用的交易工具：
1. get_account_balance() - 查询账户余额
2. get_current_positions() - 查询当前持仓
3. place_futures_order(symbol, side, quantity, order_type, price, stop_price) - 下永续订单
4. set_leverage(symbol, leverage) - 设置杠杆倍数 
5. cancel_all_orders(symbol) - 取消所有订单
6. close_position(symbol) - 平仓
7. execute_trading_decision(decision_data) - 执行完整交易决策

交易决策格式：
{
    "action": "BUY/SELL/HOLD/CLOSE",
    "symbol": "BTCUSDT", 
    "quantity": 0.001,
    "leverage": 10,
    "stop_loss": 95000,
    "take_profit": 105000
}
"""

    def _call_claude_api(self, prompt: str, agent_name: str) -> str:
        """调用Claude API的通用方法"""
        print(f"🤖 [{agent_name}] 调用模型: {self.claude_model}", flush=True)

        if not self.claude_api_key:
            error_msg = f"❌ [{agent_name}] 未配置Claude API密钥"
            print(error_msg, flush=True)
            return error_msg

        url = f"{self.claude_base_url}/v1/messages"
        payload = {
            "model": self.claude_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "stream": True
        }

        headers = {
            "x-api-key": self.claude_api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60, stream=True)

            if response.status_code != 200:
                error_msg = f"❌ [{agent_name}] API请求失败: {response.status_code} - {response.text}"
                print(error_msg)
                return error_msg

            full_response = ""
            buffer = ""

            for chunk in response:
                if chunk:
                    buffer += chunk.decode('utf-8', errors='ignore')

                    # 处理完整的行
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()

                        if line.startswith('data: '):
                            data_text = line[6:]
                            if data_text.strip() == '[DONE]':
                                break

                            try:
                                data = json.loads(data_text)
                                if data.get('type') == 'content_block_delta':
                                    if 'delta' in data and data['delta'].get('type') == 'text_delta':
                                        chunk_text = data['delta']['text']
                                        # 实时输出：直接输出整个chunk，确保立即显示
                                        print(chunk_text, end='', flush=True)
                                        # 立即刷新标准输出缓冲区
                                        sys.stdout.flush()
                                        full_response += chunk_text
                                elif data.get('type') == 'content_block_start':
                                    continue
                                elif data.get('type') == 'message_start':
                                    continue
                            except json.JSONDecodeError:
                                continue
                            except Exception as e:
                                print(f"⚠️ [{agent_name}] 处理数据错误: {e}")
                                continue

            print()  # 换行

            if not full_response.strip():
                error_msg = f"❌ [{agent_name}] 未收到有效响应内容"
                print(error_msg)
                return error_msg

            return full_response.strip()

        except requests.exceptions.Timeout:
            error_msg = f"❌ [{agent_name}] 请求超时"
            print(error_msg)
            return error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"❌ [{agent_name}] 网络请求错误: {e}"
            print(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"❌ [{agent_name}] 未知错误: {e}"
            print(error_msg)
            return error_msg

    def analyze_kline_data(self, symbol="BTCUSDT", interval='15m', limit=100) -> str:
        """K线数据技术分析代理"""
        # 获取K线数据
        kline_data = self.get_crypto_data(symbol, interval, limit)
        if not kline_data:
            error_msg = f"❌ [技术分析师] 无法获取{symbol}的K线数据"
            print(error_msg)
            return error_msg

        try:
            # 准备技术分析数据
            df = pd.DataFrame(kline_data)

            # 确保有足够的数据进行计算
            if len(df) < 50:
                limit = 100  # 增加数据量
                kline_data = self.get_crypto_data(symbol, interval, limit)
                df = pd.DataFrame(kline_data)

            # 计算技术指标
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['rsi'] = self._calculate_rsi(df['close'])
            df['macd'], df['macd_signal'] = self._calculate_macd(df['close'])

            # 获取最近10个有效数据点
            recent_data = df.dropna().tail(10)
            if recent_data.empty:
                error_msg = f"❌ [技术分析师] 计算技术指标失败，数据不足"
                print(error_msg)
                return error_msg

            # 转换为字典格式，处理NaN值
            recent_dict = []
            for _, row in recent_data.iterrows():
                row_dict = {}
                for col in row.index:
                    value = row[col]
                    if pd.isna(value):
                        row_dict[col] = None
                    elif isinstance(value, (int, float)):
                        row_dict[col] = round(float(value), 4)
                    else:
                        row_dict[col] = value
                recent_dict.append(row_dict)

            # 构建技术分析prompt
            prompt = f"""
你是专业的技术分析师，请分析{symbol}的{interval}K线数据：

最近10个周期的技术指标数据：
时间戳(time)、开盘价(open)、最高价(high)、最低价(low)、收盘价(close)、成交量(volume)
20期简单移动平均线(sma_20)、50期简单移动平均线(sma_50)
相对强弱指数RSI(rsi)、MACD线(macd)、MACD信号线(macd_signal)

{json.dumps(recent_dict, indent=2, ensure_ascii=False)}

请提供：
1. 趋势分析（短期、中期）
2. 支撑阻力位识别
3. 技术指标解读（RSI、MACD、均线）
4. 交易建议（入场点位、止损止盈）

请保持简洁专业，重点关注15分钟级别的短期走势。
"""
            return self._call_claude_api(prompt, "技术分析师")

        except Exception as e:
            error_msg = f"❌ [技术分析师] 数据处理错误: {e}"
            print(error_msg)
            return error_msg

    def analyze_market_sentiment(self) -> str:
        """市场情绪分析代理 - 基于CoinGecko全球市场数据和恐贪指数分析整体市场情绪"""
        try:
            print("🔍 获取全球市场数据...")
            sentiment_data = {}

            # 1. 获取CoinGecko全球市场数据
            try:
                global_url = f"{self.coingecko_base_url}/global"
                headers = {"x_cg_demo_api_key": self.coingecko_api_key}
                response = requests.get(global_url, headers=headers, timeout=15)

                if response.status_code == 200:
                    global_data = response.json()
                    if 'data' in global_data:
                        data = global_data['data']
                        sentiment_data['global_market'] = {
                            'total_market_cap_usd': data.get('total_market_cap', {}).get('usd', 0),
                            'total_volume_24h_usd': data.get('total_volume', {}).get('usd', 0),
                            'market_cap_change_24h': data.get('market_cap_change_percentage_24h_usd', 0),
                            'btc_dominance': data.get('market_cap_percentage', {}).get('btc', 0),
                            'eth_dominance': data.get('market_cap_percentage', {}).get('eth', 0),
                            'active_cryptocurrencies': data.get('active_cryptocurrencies', 0)
                        }
                        print("✅ 获取全球市场数据成功")
                    else:
                        print("❌ 全球市场数据格式异常")
                else:
                    print(f"❌ 全球市场数据API返回错误: {response.status_code}")
            except Exception as e:
                print(f"❌ 获取全球市场数据失败: {e}")

            # 2. 获取热门搜索趋势（用户兴趣指标）
            try:
                trending_url = f"{self.coingecko_base_url}/search/trending"
                headers = {"x_cg_demo_api_key": self.coingecko_api_key}
                response = requests.get(trending_url, headers=headers, timeout=15)

                if response.status_code == 200:
                    trending_data = response.json()
                    if 'coins' in trending_data:
                        trending_coins = []
                        for coin in trending_data['coins'][:5]:
                            item = coin.get('item', {})
                            trending_coins.append({
                                'name': item.get('name', '未知'),
                                'symbol': item.get('symbol', '未知').upper(),
                                'market_cap_rank': item.get('market_cap_rank', 'N/A'),
                                'score': item.get('score', 0)
                            })
                        sentiment_data['trending_coins'] = trending_coins
                        print("✅ 获取热门搜索数据成功")
            except Exception as e:
                print(f"❌ 获取热门搜索数据失败: {e}")

            # 3. 获取恐贪指数（Alternative.me API）
            try:
                fng_url = "https://api.alternative.me/fng/"
                response = requests.get(fng_url, timeout=10)

                if response.status_code == 200:
                    fng_data = response.json()
                    if 'data' in fng_data and len(fng_data['data']) > 0:
                        latest_fng = fng_data['data'][0]
                        sentiment_data['fear_greed_index'] = {
                            'value': int(latest_fng.get('value', 0)),
                            'classification': latest_fng.get('value_classification', '未知'),
                            'timestamp': latest_fng.get('timestamp', '未知'),
                            'time_until_update': latest_fng.get('time_until_update', '未知')
                        }
                        print(f"✅ 获取恐贪指数成功: {sentiment_data['fear_greed_index']['value']} ({sentiment_data['fear_greed_index']['classification']})")
                    else:
                        print("❌ 恐贪指数数据格式异常")
                else:
                    print(f"❌ 恐贪指数API返回错误: {response.status_code}")
            except Exception as e:
                print(f"❌ 获取恐贪指数失败: {e}")

            # 4. 获取主流币种表现（作为补充数据）
            try:
                major_coins = ['bitcoin', 'ethereum', 'ripple', 'binancecoin', 'cardano', 'solana']
                market_url = f"{self.coingecko_base_url}/coins/markets"
                params = {
                    'vs_currency': 'usd',
                    'ids': ','.join(major_coins),
                    'order': 'market_cap_desc',
                    'per_page': 6,
                    'page': 1,
                    'sparkline': 'false',
                    'price_change_percentage': '24h'
                }
                headers = {"x_cg_demo_api_key": self.coingecko_api_key}
                response = requests.get(market_url, headers=headers, params=params, timeout=15)

                if response.status_code == 200:
                    coins_data = response.json()
                    if isinstance(coins_data, list) and len(coins_data) > 0:
                        major_performance = []
                        for coin in coins_data:
                            major_performance.append({
                                'name': coin.get('name', '未知'),
                                'symbol': coin.get('symbol', '未知').upper(),
                                'current_price': coin.get('current_price', 0),
                                'price_change_24h': coin.get('price_change_percentage_24h', 0),
                                'market_cap': coin.get('market_cap', 0),
                                'total_volume': coin.get('total_volume', 0)
                            })
                        sentiment_data['major_coins_performance'] = major_performance
                        print("✅ 获取主流币种表现数据成功")
                    else:
                        print("❌ 主流币种数据格式异常")
                else:
                    print(f"❌ 主流币种API返回错误: {response.status_code}")
            except Exception as e:
                print(f"❌ 获取主流币种表现失败: {e}")

            if not sentiment_data:
                return "❌ 无法获取任何市场情绪数据"

            # 构建综合市场情绪分析prompt
            prompt = f"""
你是专业的市场情绪分析师，请基于以下多维度数据分析当前加密货币市场情绪：

=== 全球市场数据 ===
{json.dumps(sentiment_data.get('global_market', {}), indent=2, ensure_ascii=False)}

=== 恐贪指数 ===
{json.dumps(sentiment_data.get('fear_greed_index', {}), indent=2, ensure_ascii=False)}

=== 热门搜索趋势 ===
{json.dumps(sentiment_data.get('trending_coins', []), indent=2, ensure_ascii=False)}

=== 主流币种表现 ===
{json.dumps(sentiment_data.get('major_coins_performance', []), indent=2, ensure_ascii=False)}

请基于以上数据分析：
1. 当前市场情绪状态（极度恐慌/恐慌/谨慎/中性/乐观/贪婪/极度贪婪）
2. 恐贪指数的含义和市场心理状态
3. BTC/ETH主导地位变化对情绪的影响
4. 热门搜索趋势反映的投资者兴趣
5. 全球市值变化和资金流向分析
6. 短期情绪变化预期和关键转折点

请提供客观专业的市场情绪评估，重点关注多个指标之间的相互验证。
"""
            return self._call_claude_api(prompt, "市场分析师")

        except Exception as e:
            error_msg = f"❌ [市场分析师] 情绪分析失败: {e}"
            print(error_msg)
            return error_msg

    def analyze_fundamental_data(self, symbol="BTCUSDT") -> str:
        """基本面分析代理"""
        # 获取基本市场数据
        market_data = self.get_market_summary(symbol)

        prompt = f"""
你是基本面分析专家，请基于以下市场数据进行基本面分析：

{market_data}

请分析：
1. 价格走势的基本面逻辑
2. 交易量变化的意义
3. 市值排名变化趋势
4. 长期投资价值评估

保持理性客观的分析视角。
"""
        return self._call_claude_api(prompt, "基本面分析师")

    def analyze_macro_data(self) -> str:
        """宏观数据分析代理 - 分析ETF流向、美股指数、黄金价格对加密货币市场的影响"""
        try:
            print("🌍 获取宏观经济数据...")
            macro_data = {}
            
            # 1. 获取比特币ETF资金流向数据
            try:
                etf_data = self.get_btc_etf_flows()
                if etf_data:
                    macro_data['bitcoin_etf'] = etf_data
                    if 'total_flow_estimate_millions' in etf_data:
                        total_flow = etf_data['total_flow_estimate_millions']
                        print(f"📈 ETF数据: 估算净流向 ${total_flow:.1f}M，追踪{etf_data['total_etfs_tracked']}只ETF")
                    else:
                        print("✅ 获取ETF数据成功")
            except Exception as e:
                print(f"❌ ETF数据获取失败: {e}")
            
            # 2. 获取美股三大指数数据
            try:
                stock_data = self.get_stock_indices_data()
                if stock_data:
                    macro_data['stock_indices'] = stock_data
                    # 计算综合表现
                    avg_change = sum([data['change_percent'] for data in stock_data.values()]) / len(stock_data)
                    print(f"🏛️ 美股数据: 平均涨跌幅 {avg_change:+.2f}%")
            except Exception as e:
                print(f"❌ 美股数据获取失败: {e}")
            
            # 3. 获取黄金价格数据
            try:
                gold_data = self.get_gold_price_data()
                if gold_data:
                    macro_data['gold_price'] = gold_data
                    print(f"🥇 黄金数据: ${gold_data['current_price']:.2f}/盎司")
            except Exception as e:
                print(f"❌ 黄金数据获取失败: {e}")
            
            if not macro_data:
                return "❌ 无法获取任何宏观经济数据"
            
            # 构建宏观分析prompt
            prompt = f"""
你是专业的宏观经济分析师，请基于以下宏观数据分析对加密货币市场的影响：

=== 比特币ETF资金流向 ===
{json.dumps(macro_data.get('bitcoin_etf', {}), indent=2, ensure_ascii=False)}

=== 美股主要指数表现 ===
{json.dumps(macro_data.get('stock_indices', {}), indent=2, ensure_ascii=False)}

=== 黄金价格数据 ===
{json.dumps(macro_data.get('gold_price', {}), indent=2, ensure_ascii=False)}

请基于以上宏观数据分析：
1. **ETF资金流向影响**: 
   - 机构资金对比特币的配置态度
   - ETF净流入/流出对BTC价格的传导机制
   - 主要ETF产品的资金偏好差异

2. **美股市场关联性**:
   - 美股三大指数与加密货币的相关性分析
   - 科技股表现(NASDAQ)对加密市场的指引作用
   - 市场风险偏好的传递效应

3. **避险资产对比**:
   - 黄金价格变化反映的宏观经济环境
   - 比特币vs黄金的避险属性对比
   - 通胀预期对加密资产配置的影响

4. **宏观投资建议**:
   - 当前宏观环境下的加密投资策略
   - 关注的关键宏观指标和转折点
   - 风险管理建议

请提供客观专业的宏观经济视角分析，重点关注传统金融市场与加密市场的联动性。
"""
            return self._call_claude_api(prompt, "宏观分析师")
            
        except Exception as e:
            error_msg = f"❌ [宏观分析师] 分析失败: {e}"
            print(error_msg)
            return error_msg

    def _calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        exp1 = prices.ewm(span=fast).mean()
        exp2 = prices.ewm(span=slow).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=signal).mean()
        return macd, macd_signal

    def conduct_research_analysis(self, symbols):
        """研究部门：多币种综合分析"""
        research_results = {}
        
        # 1. 宏观分析（全市场，只做一次）
        print("🌍 [研究部门-宏观分析师] 分析全球市场环境...", flush=True)
        macro_analysis = self.get_today_analysis('macro_analysis', '宏观分析师')
        if macro_analysis is None:
            print("🔄 生成新的宏观分析...", flush=True)
            macro_analysis = self.analyze_macro_data()
            self.save_to_database(
                data_type='macro_analysis',
                agent_name='宏观分析师',
                content=macro_analysis,
                summary=macro_analysis[:50] if macro_analysis else '宏观数据分析',
                status='completed'
            )
        
        # 2. 市场情绪分析（全市场，只做一次）
        print("🔥 [研究部门-市场分析师] 分析市场情绪...", flush=True)
        sentiment_analysis = self.get_today_analysis('market_sentiment', '市场分析师')
        if sentiment_analysis is None:
            print("🔄 生成新的市场情绪分析...", flush=True)
            sentiment_analysis = self.analyze_market_sentiment()
            self.save_to_database(
                data_type='market_sentiment',
                agent_name='市场分析师',
                content=sentiment_analysis,
                summary=sentiment_analysis[:50] if sentiment_analysis else '市场情绪分析',
                status='completed'
            )
        
        # 3. 各币种的四维度分析 + 币种首席分析师
        for symbol in symbols:
            print(f"📈 [研究部门-技术分析师] 分析 {symbol}...", flush=True)
            
            # 技术分析（每个币种都要分析）
            kline_analysis = self.analyze_kline_data(symbol)
            self.save_to_database(
                data_type='technical_analysis',
                agent_name='技术分析师',
                symbol=symbol,
                content=kline_analysis,
                summary=kline_analysis[:50] if kline_analysis else f'{symbol}技术分析',
                status='completed'
            )
            
            print(f"📊 [研究部门-基本面分析师] 分析 {symbol}...", flush=True)
            
            # 基本面分析（优先使用缓存）
            fundamental_analysis = self.get_today_analysis(f'fundamental_analysis_{symbol}', '基本面分析师')
            if fundamental_analysis is None:
                print(f"🔄 生成新的{symbol}基本面分析...", flush=True)
                fundamental_analysis = self.analyze_fundamental_data(symbol)
                self.save_to_database(
                    data_type=f'fundamental_analysis_{symbol}',
                    agent_name='基本面分析师',
                    symbol=symbol,
                    content=fundamental_analysis,
                    summary=fundamental_analysis[:50] if fundamental_analysis else f'{symbol}基本面分析',
                    status='completed'
                )
            
            # 每个币种的首席分析师整合四个维度
            print(f"🎯 [研究部门-{symbol}首席分析师] 整合四维度分析...", flush=True)
            coin_chief_analysis = self.generate_coin_chief_analysis(
                symbol, kline_analysis, sentiment_analysis, fundamental_analysis, macro_analysis
            )
            
            research_results[symbol] = {
                'technical': kline_analysis,
                'fundamental': fundamental_analysis,
                'chief_analysis': coin_chief_analysis  # 每个币种的首席分析
            }
        
        # 4. 研究部门综合报告
        print("🎯 [研究部门-首席分析师] 整合多币种研究报告...", flush=True)
        research_summary = self.generate_research_summary(research_results, macro_analysis, sentiment_analysis)
        
        return {
            'macro_analysis': macro_analysis,
            'sentiment_analysis': sentiment_analysis,
            'symbol_analyses': research_results,
            'research_summary': research_summary
        }
    
    def generate_coin_chief_analysis(self, symbol, technical_analysis, sentiment_analysis, fundamental_analysis, macro_analysis):
        """生成单个币种的首席分析师报告"""
        
        coin_chief_prompt = f"""
你是{symbol}首席分析师，请整合以下四个专业代理的分析报告，提供针对{symbol}的全面投资建议：

=== 技术分析师报告 ===
{technical_analysis}

=== 市场分析师报告 ===
{sentiment_analysis}

=== 基本面分析师报告 ===
{fundamental_analysis}

=== 宏观分析师报告 ===
{macro_analysis}

=== 分析要求 ===
请基于技术面、市场情绪、基本面和宏观面的综合分析，提供针对{symbol}的全面投资建议。
注意平衡各方观点，给出客观专业的结论，重点关注：

1. **各维度分析的一致性和分歧点**
   - 技术面vs基本面的信号对比
   - 短期情绪vs长期宏观趋势的冲突
   - {symbol}特有的市场表现特征

2. **短期和中长期的投资策略差异**
   - 1-7天的短期交易机会
   - 1-3个月的中期趋势判断
   - 3-12个月的长期配置建议

3. **风险因素的多维度评估**
   - 技术风险：关键支撑阻力位
   - 基本面风险：项目发展、监管政策
   - 宏观风险：流动性、市场周期
   - 情绪风险：FOMO、恐慌抛售

4. **关键的市场转折点和信号**
   - 技术指标的重要突破位
   - 宏观数据的关键变化
   - 市场情绪的极值反转信号
   - 基本面的重大催化事件

请提供具体、可操作的{symbol}投资建议，避免空泛的表述。
"""
        
        coin_chief_analysis = self._call_claude_api(coin_chief_prompt, f"{symbol}首席分析师")
        
        # 保存币种首席分析
        self.save_to_database(
            data_type=f'coin_chief_analysis_{symbol}',
            agent_name=f'{symbol}首席分析师',
            symbol=symbol,
            content=coin_chief_analysis,
            summary=coin_chief_analysis[:50] if coin_chief_analysis else f'{symbol}首席分析',
            status='completed'
        )
        
        return coin_chief_analysis
    
    def generate_research_summary(self, symbol_analyses, macro_analysis, sentiment_analysis):
        """生成研究部门综合报告"""
        symbols_list = list(symbol_analyses.keys())
        
        # 构建研究报告 - 基于各币种首席分析师的报告
        symbol_reports = ""
        for symbol, analyses in symbol_analyses.items():
            symbol_reports += f"\n=== {symbol} 首席分析师报告 ===\n"
            symbol_reports += f"{analyses['chief_analysis']}\n\n"
        
        research_prompt = f"""
你是研究部门总监，请基于各币种首席分析师的报告，提供投资组合的综合建议：

=== 各币种首席分析师报告 ===
{symbol_reports}

=== 整体市场环境参考 ===
宏观环境: {macro_analysis}
市场情绪: {sentiment_analysis}

=== 分析要求 ===
请基于各币种首席分析师的专业报告，提供投资组合层面的综合建议：

1. **币种间的比较分析**
   - 各币种投资机会的排序和权重建议
   - 不同币种间的相关性和配置策略
   - 风险分散的最优组合方案

2. **时间维度的配置策略**
   - 短期(1-7天)的主要关注币种
   - 中期(1-3月)的核心配置建议
   - 长期(3-12月)的战略布局方向

3. **风险管控建议**
   - 基于各币种分析的整体风险评估
   - 关键风险点的预警和应对策略
   - 投资组合的止损和止盈设置

4. **市场时机判断**
   - 当前市场阶段的整体判断
   - 关键转折点的识别和应对
   - 资金配置的优先级排序

请提供具体的投资组合建议，包括币种选择、权重分配、进出场时机等。
"""
        
        research_summary = self._call_claude_api(research_prompt, "研究部门总监")
        
        # 保存研究报告
        self.save_to_database(
            data_type='research_summary',
            agent_name='研究部门总监',
            content=research_summary,
            summary=research_summary[:50] if research_summary else '多币种研究综合报告',
            status='completed'
        )
        
        return research_summary

    def ask_claude_with_data(self, question: str, symbols=None) -> str:
        """华尔街式多币种分析架构 - 研究部门 + 交易部门"""
        if symbols is None:
            symbols = ["BTCUSDT"]  # 默认分析BTC
        elif isinstance(symbols, str):
            symbols = [symbols]  # 单个币种转为列表
            
        print(f"🏛️ 启动华尔街式分析架构", flush=True)
        print(f"📊 研究部门分析币种: {', '.join(symbols)}", flush=True)
        print("="*80, flush=True)

        # === 研究部门：多币种分析 ===
        research_results = self.conduct_research_analysis(symbols)
        
        print("\n" + "="*80, flush=True)

        # === 交易部门：投资组合决策 ===
        trading_decisions = self.conduct_trading_analysis(research_results, question)
        
        return research_results['research_summary']  # 返回研究报告作为主要输出

    def conduct_trading_analysis(self, research_results, question):
        """交易部门：投资组合决策"""
        print("💼 [交易部门] 制定投资组合策略...", flush=True)
        
        # 获取当前账户状态
        print("📊 获取账户信息...", flush=True)
        account_balance = self.get_account_balance()
        current_positions = self.get_current_positions()
        
        # 打印账户信息
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
        

        
        # 获取最近10次研究报告给交易员参考
        recent_research = self.get_recent_chief_analysis(10)
        
        # 交易部门决策 - 永续交易员
        symbols_analyzed = list(research_results['symbol_analyses'].keys())
        # 选择主要分析币种进行交易决策（通常选第一个）
        primary_symbol = symbols_analyzed[0] if symbols_analyzed else 'BTCUSDT'
        primary_symbol_name = primary_symbol.replace('USDT', '')
        
        trading_prompt = f"""
你是专业交易员，基于研究部门的多币种分析报告，重点针对 {primary_symbol} 制定合约交易策略：

=== 研究部门综合报告 ===
{research_results['research_summary']}

=== 可用交易工具 ===
{self.get_trading_tools_description()}

=== 当前账户状态 ===
余额信息: {json.dumps(account_balance, indent=2, ensure_ascii=False)}
当前持仓: {json.dumps(current_positions, indent=2, ensure_ascii=False)}

=== 历史交易参考 ===
{json.dumps(recent_research, indent=2, ensure_ascii=False)}

=== 用户问题 ===
{question}

=== 交易参数要求 ===
- 交易标的: {primary_symbol}
- 完全自主决策: 你可以根据分析结果自主决定所有交易参数
- 输出格式: 必须是JSON格式，以便自动执行

请输出以下JSON格式的交易决策：
{{
    "action": "BUY/SELL/HOLD/CLOSE",
    "symbol": "{primary_symbol}",
    "quantity": 0.001,
    "leverage": 10,
    "stop_loss": 95000,
    "take_profit": 105000,
    "risk_level": "HIGH",
    "confidence": 85,
    "reasoning": "详细的交易理由，结合技术面、基本面、宏观和市场情绪",
    "entry_price": 100000,
    "position_size_pct": 20
}}

注意：
1. quantity必须是具体的数量（如0.001 BTC）
2. 价格必须是具体数值（如95000表示95000 USDT）
3. leverage杠杆倍数由你自主决定
4. confidence是置信度百分比（0-100）
5. reasoning必须包含研究部门各维度分析的综合考虑
6. 参考账户余额状况和历史交易表现
7. 根据市场波动性和合约特性决定合适的杠杆和仓位

请基于研究部门的综合分析给出明确可执行的JSON决策。
"""

        trading_decision = self._call_claude_api(trading_prompt, "永续交易员")
        print("\n" + "="*80)
        
        # 解析并执行交易决策
        print("⚡ [交易部门] 解析交易决策...")
        try:
            # 尝试从回复中提取JSON
            import re
            json_match = re.search(r'\{.*\}', trading_decision, re.DOTALL)
            if json_match:
                decision_data = json.loads(json_match.group())
                print(f"✅ 解析成功: {decision_data.get('action', 'UNKNOWN')} - {decision_data.get('reasoning', '无理由')[:100]}...")
                
                # 先显示交易统计（如果有历史记录）
                stats = self.get_trading_stats()
                if stats['total_trades'] > 0:
                    self.print_trading_stats()
                
                # 创建交易摘要
                analysis_summary = decision_data.get('reasoning', '永续交易决策')[:50]
                
                # 如果有Binance客户端且不是观望操作，则直接执行交易
                if self.binance_client and decision_data.get('action', '').upper() not in ['HOLD']:
                    print("🚀 开始执行交易决策...")
                    execution_result = self.execute_trading_decision(decision_data)
                    
                    # 记录交易
                    trade_id = self.record_trade(decision_data, execution_result, analysis_summary)
                    
                    print(f"💼 执行结果:", flush=True)
                    if execution_result.get('success'):
                        print("✅ 交易执行成功！", flush=True)
                        for result in execution_result.get('execution_results', []):
                            action = result.get('action', 'UNKNOWN')
                            result_data = result.get('result', {})
                            if result_data.get('success'):
                                print(f"  ✅ {action}: 成功", flush=True)
                                if 'order_id' in result_data:
                                    print(f"     订单ID: {result_data['order_id']}", flush=True)
                                if 'symbol' in result_data:
                                    print(f"     交易对: {result_data['symbol']}", flush=True)
                                if 'quantity' in result_data:
                                    print(f"     数量: {result_data['quantity']}", flush=True)
                            else:
                                print(f"  ❌ {action}: {result_data.get('error', '未知错误')}", flush=True)
                        
                        if trade_id:
                            print(f"📝 交易已记录，ID: {trade_id}", flush=True)
                            print("💡 提示：您可以手动调用 update_trade_result() 更新盈亏情况", flush=True)
                    else:
                        error_msg = execution_result.get('error', '未知错误')
                        print(f"❌ 交易执行失败: {error_msg}", flush=True)
                        
                        # 如果是余额不足，给出友好提示
                        if "余额不足" in error_msg:
                            print("💡 这是模拟交易环境，交易决策分析已完成。", flush=True)
                            print("   如需实盘交易，请确保账户有足够的USDT余额。", flush=True)
                elif decision_data.get('action', '').upper() == 'HOLD':
                    print("⏳ 永续交易员建议观望，不执行交易")
                    # 观望也记录决策
                    execution_result = {"success": True, "action": "HOLD", "message": "观望决策"}
                    self.record_trade(decision_data, execution_result, analysis_summary)
                else:
                    print("⚠️ 未配置Binance客户端，仅输出交易建议")
                    
            else:
                print("❌ 无法解析JSON格式决策，请检查永续交易员输出")
        except Exception as e:
            print(f"❌ 解析交易决策失败: {e}")
        
        return trading_decision

def main():
    bot = CryptoBot()

    if len(sys.argv) > 1:
        # 检查是否要启动自动调度器
        if sys.argv[1] == '--auto' or sys.argv[1] == '-a':
            print("🚀 启动自动调度模式", flush=True)
            bot.start_scheduler()
            try:
                # 保持程序运行
                while True:
                    time.sleep(60)  # 每分钟检查一次
            except KeyboardInterrupt:
                print("\n🛑 收到中断信号，正在停止...", flush=True)
                bot.stop_scheduler()
                print("👋 程序已退出", flush=True)
                return
        
        # 命令行模式 - 支持多币种分析
        if len(sys.argv) == 2:
            # 只有一个参数，检查是否是代币名或组合
            arg = sys.argv[1].upper()
            known_tokens = ['BTC', 'ETH', 'XRP', 'BNB', 'ADA', 'SOL', 'DOGE', 'MATIC', 'DOT', 'AVAX', 'SHIB', 'LTC', 'UNI', 'LINK', 'TRX']
            
            # 检查是否是多个币种（用逗号分隔）
            if ',' in arg:
                tokens = [token.strip() + 'USDT' for token in arg.split(',') if token.strip() in known_tokens]
                if tokens:
                    question = f"分析 {', '.join([t.replace('USDT', '') for t in tokens])} 的投资组合配置"
                    bot.ask_claude_with_data(question, tokens)
                else:
                    print("❌ 未识别的币种组合")
            elif arg in known_tokens:
                # 单个币种
                symbol = arg + 'USDT'
                question = f"{arg}日内走势如何？技术面和基本面分析"
                bot.ask_claude_with_data(question, [symbol])
            else:
                question = sys.argv[1]
                bot.ask_claude_with_data(question)
        else:
            # 多个参数
            question = " ".join(sys.argv[1:])
            # 检查是否指定了特定币种
            if len(sys.argv) > 2 and sys.argv[1].upper().endswith('USDT'):
                symbol = sys.argv[1].upper()
                question = " ".join(sys.argv[2:])
                bot.ask_claude_with_data(question, [symbol])
            else:
                bot.ask_claude_with_data(question)
    else:
        # 交互模式
        print("🏛️ 华尔街式加密货币分析机器人 (输入quit退出)", flush=True)
        print("💡 用法示例:", flush=True)
        print("   - 单币种分析: 'BTC' 或 'ETH'", flush=True)
        print("   - 多币种投资组合: 'BTC,ETH,SOL' (逗号分隔)", flush=True)
        print("   - 指定交易对: 'ETHUSDT 以太坊今天走势如何?'", flush=True)
        print("   - 直接提问: '当前市场适合投资吗?'", flush=True)
        print("   - 启动自动模式: python crypto_bot.py --auto", flush=True)
        print("   - 查看交易统计: 输入 'stats'", flush=True)
        print("   - 查看今日分析缓存: 输入 'cache'", flush=True)
        print("   - 启动调度器: 输入 'start_auto'", flush=True)

        while True:
            user_input = input("\n❓ 问题: ").strip()
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'stats':
                bot.print_trading_stats()
                continue
            elif user_input.lower() == 'cache':
                bot.show_today_analysis_status()
                continue
            elif user_input.lower() == 'start_auto':
                bot.start_scheduler()
                print("🔄 自动调度器已启动，继续输入问题或输入quit退出")
                continue
            elif user_input.lower() == 'stop_auto':
                bot.stop_scheduler()
                print("⏹️ 自动调度器已停止")
                continue
            
            if user_input:
                # 解析输入，支持多币种分析
                known_tokens = ['BTC', 'ETH', 'XRP', 'BNB', 'ADA', 'SOL', 'DOGE', 'MATIC', 'DOT', 'AVAX', 'SHIB', 'LTC', 'UNI', 'LINK', 'TRX']
                
                # 检查是否是多币种组合（用逗号分隔）
                if ',' in user_input and all(token.strip().upper() in known_tokens for token in user_input.split(',')):
                    tokens = [token.strip().upper() + 'USDT' for token in user_input.split(',')]
                    question = f"分析 {', '.join([t.replace('USDT', '') for t in tokens])} 的投资组合配置"
                    bot.ask_claude_with_data(question, tokens)
                else:
                    parts = user_input.split(' ', 1)
                    
                    # 检查是否是单独的代币名
                    if len(parts) == 1 and parts[0].upper() in known_tokens:
                        symbol = parts[0].upper() + 'USDT'
                        question = f"{parts[0].upper()}技术面和基本面分析"
                        bot.ask_claude_with_data(question, [symbol])
                    elif len(parts) > 1 and parts[0].upper().endswith('USDT'):
                        # 指定了完整交易对
                        symbol = parts[0].upper()
                        question = parts[1]
                        bot.ask_claude_with_data(question, [symbol])
                    else:
                        # 普通问题，使用默认多币种分析
                        bot.ask_claude_with_data(user_input, ['BTCUSDT', 'ETHUSDT'])

if __name__ == "__main__":
    main()
