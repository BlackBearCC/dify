# -*- coding: utf-8 -*-
"""
Telegram机器人集成 - 加密货币监控系统远程控制
"""

import asyncio
import json
import re
import threading
import time
from datetime import datetime
from typing import Optional

try:
    from telegram import Bot, Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("❌ 未安装python-telegram-bot库，请运行: pip install python-telegram-bot")

from crypto_bot import Crypto24hMonitor

class CryptoTelegramBot:
    def __init__(self, token: str, chat_id: str, crypto_monitor: Crypto24hMonitor):
        if not TELEGRAM_AVAILABLE:
            raise ImportError("需要安装python-telegram-bot库")
            
        self.token = token
        self.chat_id = chat_id
        self.crypto_monitor = crypto_monitor
        self.application = None
        self.running = False
        
        # 支持的角色列表
        self.supported_roles = {
            '技术分析师': 'technical_analysis',
            '市场分析师': 'market_sentiment', 
            '基本面分析师': 'fundamental_analysis',
            '宏观分析师': 'macro_analysis',
            '首席分析师': 'coin_chief_analysis',
            '研究部门总监': 'research_summary',
            '永续交易员': 'trader_decision'
        }
        
        # 支持的币种（从配置中获取）
        self.supported_symbols = crypto_monitor.all_symbols
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """启动命令处理"""
        welcome_msg = f"""
🤖 **加密货币监控系统 Telegram Bot**

📊 **可用命令：**

🔍 **获取报告：**
`/report 角色 币种` - 获取指定角色对指定币种的最近报告
例：`/report 技术分析师 BTC`

📈 **完整分析：**
`/analyze 币种` - 执行完整分析流程（包括交易员下单）
例：`/analyze BTC`

📋 **支持的角色：**
{chr(10).join([f"• {role}" for role in self.supported_roles.keys()])}

💰 **支持的币种：**
{', '.join([symbol.replace('USDT', '') for symbol in self.supported_symbols[:10]])}...

ℹ️ **其他命令：**
`/status` - 查看系统状态
`/help` - 显示帮助信息
"""
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """帮助命令"""
        help_msg = """
📖 **命令详细说明：**

**1. 获取报告 `/report`**
格式：`/report [角色] [币种]`
- 角色：技术分析师、市场分析师、基本面分析师、宏观分析师、首席分析师、研究部门总监
- 币种：BTC、ETH、SOL等（不需要USDT后缀）
- 如果今天有缓存报告则直接返回，否则生成新报告

**2. 完整分析 `/analyze`**
格式：`/analyze [币种]`
- 执行完整的华尔街式分析流程
- 包括：技术面→基本面→市场情绪→宏观面→首席分析→交易决策→执行下单
- 会自动执行交易员的建议（如果配置了Binance API）

**3. 系统状态 `/status`**
- 查看监控系统运行状态
- 显示当前持仓和账户余额
- 显示最近交易统计

**示例：**
- `/report 技术分析师 BTC`
- `/analyze ETH`
- `/status`
"""
        await update.message.reply_text(help_msg, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """系统状态命令"""
        try:
            # 获取账户余额
            balance = self.crypto_monitor.get_account_balance()
            positions = self.crypto_monitor.get_current_positions()
            stats = self.crypto_monitor.get_trading_stats()
            
            status_msg = f"""
📊 **系统状态报告**
⏰ 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💰 **账户余额：**
"""
            if 'error' not in balance:
                for asset, info in balance.items():
                    if info['total'] > 0:
                        status_msg += f"• {asset}: {info['total']:.6f} (可用: {info['free']:.6f})\n"
            else:
                status_msg += f"❌ {balance['error']}\n"

            status_msg += f"""
📈 **当前持仓：**
"""
            if isinstance(positions, list) and positions:
                for pos in positions:
                    pnl_emoji = "🟢" if pos['pnl'] > 0 else "🔴" if pos['pnl'] < 0 else "⚪"
                    status_msg += f"{pnl_emoji} {pos['symbol']} {pos['side']}: {pos['size']} ({pos['pnl']:.2f} USDT, {pos['pnl_pct']:.2f}%)\n"
            else:
                status_msg += "无持仓\n"

            status_msg += f"""
📊 **交易统计：**
• 总交易数: {stats['total_trades']}
• 胜率: {stats['win_rate']:.1f}%
• 总盈亏: {stats['total_pnl']:.2f} USDT
• 最佳交易: {stats['best_trade']:.2f} USDT
• 最差交易: {stats['worst_trade']:.2f} USDT
"""
            
            await update.message.reply_text(status_msg, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ 获取系统状态失败: {e}")

    async def report_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """报告命令处理"""
        try:
            if len(context.args) < 2:
                await update.message.reply_text(
                    "❌ 格式错误！\n正确格式：`/report 角色 币种`\n例：`/report 技术分析师 BTC`", 
                    parse_mode='Markdown'
                )
                return
            
            role = context.args[0]
            symbol_input = context.args[1].upper()
            
            # 验证角色
            if role not in self.supported_roles:
                roles_list = '\n'.join([f"• {r}" for r in self.supported_roles.keys()])
                await update.message.reply_text(
                    f"❌ 不支持的角色：{role}\n\n支持的角色：\n{roles_list}"
                )
                return
            
            # 处理币种格式
            symbol = f"{symbol_input}USDT" if not symbol_input.endswith('USDT') else symbol_input
            if symbol not in self.supported_symbols:
                await update.message.reply_text(
                    f"❌ 不支持的币种：{symbol_input}\n支持的币种：{', '.join([s.replace('USDT', '') for s in self.supported_symbols])}"
                )
                return
            
            await update.message.reply_text(f"🔍 正在获取 {role} 对 {symbol_input} 的报告...")
            
            # 获取或生成报告
            report = await self._get_or_generate_report(role, symbol)
            
            if report:
                # 分段发送长消息
                await self._send_long_message(update, f"📊 **{role} - {symbol_input} 报告**\n\n{report}")
            else:
                await update.message.reply_text(f"❌ 无法获取 {role} 的 {symbol_input} 报告")
                
        except Exception as e:
            await update.message.reply_text(f"❌ 处理报告请求失败: {e}")

    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """完整分析命令处理"""
        try:
            if len(context.args) < 1:
                await update.message.reply_text(
                    "❌ 格式错误！\n正确格式：`/analyze 币种`\n例：`/analyze BTC`", 
                    parse_mode='Markdown'
                )
                return
            
            symbol_input = context.args[0].upper()
            symbol = f"{symbol_input}USDT" if not symbol_input.endswith('USDT') else symbol_input
            
            if symbol not in self.supported_symbols:
                await update.message.reply_text(
                    f"❌ 不支持的币种：{symbol_input}\n支持的币种：{', '.join([s.replace('USDT', '') for s in self.supported_symbols])}"
                )
                return
            
            await update.message.reply_text(f"🚀 开始执行 {symbol_input} 完整分析流程...")
            
            # 在后台线程执行完整分析
            def run_analysis():
                try:
                    # 执行华尔街式分析（包括交易员决策）
                    result = self.crypto_monitor.ask_claude_with_data(
                        f"Telegram用户请求完整分析 {symbol}", 
                        [symbol]
                    )
                    
                    # 发送分析结果
                    asyncio.run(self._send_long_message(
                        update, 
                        f"📈 **{symbol_input} 完整分析报告**\n\n{result}"
                    ))
                    
                except Exception as e:
                    asyncio.run(update.message.reply_text(f"❌ 分析执行失败: {e}"))
            
            # 在新线程中运行分析，避免阻塞
            analysis_thread = threading.Thread(target=run_analysis, daemon=True)
            analysis_thread.start()
            
        except Exception as e:
            await update.message.reply_text(f"❌ 处理分析请求失败: {e}")

    async def _get_or_generate_report(self, role: str, symbol: str) -> Optional[str]:
        """获取或生成指定角色的报告"""
        try:
            data_type = self.supported_roles[role]
            agent_name = role
            
            # 特殊处理不同类型的报告
            if role in ['技术分析师']:
                # 技术分析每次都重新生成（实时性要求高）
                return self.crypto_monitor.analyze_kline_data(symbol)
                
            elif role == '市场分析师':
                # 市场情绪分析（全市场，不针对特定币种）
                cached = self.crypto_monitor.get_today_analysis('market_sentiment', '市场分析师')
                if cached:
                    return cached
                return self.crypto_monitor.analyze_market_sentiment()
                
            elif role == '基本面分析师':
                # 基本面分析
                data_type_with_symbol = f'fundamental_analysis_{symbol}'
                cached = self.crypto_monitor.get_today_analysis(data_type_with_symbol, '基本面分析师')
                if cached:
                    return cached
                return self.crypto_monitor.analyze_fundamental_data(symbol)
                
            elif role == '宏观分析师':
                # 宏观分析（全市场）
                cached = self.crypto_monitor.get_today_analysis('macro_analysis', '宏观分析师')
                if cached:
                    return cached
                return self.crypto_monitor.analyze_macro_data()
                
            elif role == '首席分析师':
                # 币种首席分析师
                data_type_with_symbol = f'coin_chief_analysis_{symbol}'
                cached = self.crypto_monitor.get_today_analysis(data_type_with_symbol, f'{symbol}首席分析师')
                if cached:
                    return cached
                    
                # 如果没有缓存，需要先生成四维度分析
                technical = self.crypto_monitor.analyze_kline_data(symbol)
                sentiment = self.crypto_monitor.analyze_market_sentiment()
                fundamental = self.crypto_monitor.analyze_fundamental_data(symbol)
                macro = self.crypto_monitor.analyze_macro_data()
                
                return self.crypto_monitor.generate_coin_chief_analysis(
                    symbol, technical, sentiment, fundamental, macro
                )
                
            elif role == '研究部门总监':
                # 研究部门综合报告
                cached = self.crypto_monitor.get_today_analysis('research_summary', '研究部门总监')
                if cached:
                    return cached
                    
                # 需要执行完整的研究分析
                research_results = self.crypto_monitor.conduct_research_analysis([symbol])
                return research_results['research_summary']
                
            return None
            
        except Exception as e:
            print(f"❌ 获取报告失败: {e}")
            return None

    async def _send_long_message(self, update: Update, message: str):
        """分段发送长消息"""
        max_length = 4000  # Telegram消息长度限制
        
        if len(message) <= max_length:
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            # 分段发送
            parts = []
            current_part = ""
            
            for line in message.split('\n'):
                if len(current_part + line + '\n') > max_length:
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = line + '\n'
                else:
                    current_part += line + '\n'
            
            if current_part:
                parts.append(current_part.strip())
            
            for i, part in enumerate(parts):
                if i == 0:
                    await update.message.reply_text(part, parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"📄 **续：** {part}", parse_mode='Markdown')
                await asyncio.sleep(1)  # 避免发送过快

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理普通消息"""
        text = update.message.text.strip()
        
        # 简单的自然语言处理
        if any(word in text.lower() for word in ['分析', 'analyze', '报告', 'report']):
            await update.message.reply_text(
                "💡 提示：\n"
                "• 获取报告：`/report 角色 币种`\n"
                "• 完整分析：`/analyze 币种`\n"
                "• 查看帮助：`/help`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "🤖 我是加密货币监控助手！\n"
                "发送 `/help` 查看可用命令。"
            )

    def setup_handlers(self):
        """设置命令处理器"""
        if not self.application:
            return
            
        # 添加命令处理器
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("report", self.report_command))
        self.application.add_handler(CommandHandler("analyze", self.analyze_command))
        
        # 添加消息处理器
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))

    async def start_bot(self):
        """启动Telegram机器人"""
        try:
            if not TELEGRAM_AVAILABLE:
                print("❌ Telegram功能不可用：请安装python-telegram-bot库")
                return
                
            print("🤖 启动Telegram机器人...")
            
            # 创建应用
            self.application = Application.builder().token(self.token).build()
            
            # 设置处理器
            self.setup_handlers()
            
            # 启动机器人
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.running = True
            print(f"✅ Telegram机器人已启动，Chat ID: {self.chat_id}")
            
            # 发送启动通知
            try:
                await self.application.bot.send_message(
                    chat_id=self.chat_id,
                    text="🚀 **加密货币监控系统已启动**\n\n发送 `/help` 查看可用命令。",
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"⚠️ 发送启动通知失败: {e}")
            
            # 保持运行
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"❌ Telegram机器人启动失败: {e}")
        finally:
            if self.application:
                await self.application.stop()
                await self.application.shutdown()

    def stop_bot(self):
        """停止Telegram机器人"""
        self.running = False
        print("⏹️ Telegram机器人已停止")

# 在crypto_bot.py中集成的函数
def start_telegram_bot_thread(crypto_monitor: Crypto24hMonitor, token: str, chat_id: str):
    """在独立线程中启动Telegram机器人"""
    if not TELEGRAM_AVAILABLE:
        print("❌ 无法启动Telegram机器人：缺少python-telegram-bot库")
        return None
    
    def run_bot():
        try:
            bot = CryptoTelegramBot(token, chat_id, crypto_monitor)
            asyncio.run(bot.start_bot())
        except Exception as e:
            print(f"❌ Telegram机器人线程异常: {e}")
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    return bot_thread
