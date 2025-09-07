# -*- coding: utf-8 -*-
"""
集成示例 - 在主控制器中使用新的日志系统和Telegram推送
"""

# 在 crypto_monitor_controller.py 的开头添加以下导入和初始化代码：

from utils import get_logger, set_telegram_integration, botinfo, info, warning, error

class CryptoMonitorController:
    def __init__(self, config_file: str):
        # ... 其他初始化代码 ...
        
        # 初始化Telegram集成
        self.telegram_integration = TelegramIntegration(self.settings)
        
        # 设置日志系统的Telegram集成
        set_telegram_integration(self.telegram_integration)
        
        # 获取日志实例
        self.logger = get_logger("CryptoMonitor", self.telegram_integration)
        
        # 启动Telegram机器人
        if self.telegram_integration.is_available():
            self.telegram_integration.start_telegram_bot(self)
            botinfo("🤖 系统启动 - 智能交易主脑已就绪")
    
    def _process_symbol(self, symbol: str):
        """处理单个币种的监控逻辑"""
        try:
            info(f"开始处理币种: {symbol}")
            
            # 获取市场数据
            klines = self.data_collector.get_klines(symbol)
            if not klines:
                warning(f"{symbol}: 无法获取K线数据")
                return
            
            # 计算技术指标
            indicators = self.indicator_calculator.calculate_all(klines)
            
            # 检查特殊触发条件
            if self._check_special_triggers(symbol, indicators):
                botinfo(f"🚨 {symbol} 触发特殊条件，启动智能分析")
                self._trigger_intelligent_analysis(symbol)
            
            # 正常心跳检查
            elif self._should_trigger_regular_analysis(symbol):
                info(f"⏰ {symbol} 达到常规分析时间")
                self._trigger_intelligent_analysis(symbol)
                
        except Exception as e:
            error(f"处理币种 {symbol} 时出错: {e}")
            self.logger.exception(f"币种处理异常: {symbol}")
    
    def _trigger_intelligent_analysis(self, symbol: str):
        """触发智能分析"""
        try:
            botinfo(f"🧠 启动智能分析: {symbol}")
            
            # 调用智能主脑进行分析
            analysis_request = f"请分析 {symbol} 的当前市场情况"
            response = self.master_brain.process_request(analysis_request)
            
            # 记录分析结果
            info(f"✅ {symbol} 分析完成")
            
            # 如果是重要分析结果，推送到Telegram
            if "强烈建议" in response or "紧急" in response:
                botinfo(f"📊 重要分析结果:\n{response}")
                
        except Exception as e:
            error(f"智能分析失败 {symbol}: {e}")
    
    def process_user_message(self, message: str) -> str:
        """处理用户消息 - 直接调用智能主脑"""
        try:
            info(f"收到用户消息: {message}")
            
            context = {
                'source': 'direct',
                'message_type': 'user_request'
            }
            
            response = self.master_brain.process_request(message, context)
            
            # 用户交互也通过botinfo推送到Telegram
            if len(message) > 10:  # 避免推送太短的消息
                botinfo(f"💬 用户交互:\nQ: {message}\nA: {response}")
            
            return response
            
        except Exception as e:
            error_msg = f"处理用户消息失败: {e}"
            error(error_msg)
            return error_msg
    
    def start_monitoring(self):
        """启动监控"""
        botinfo("🚀 开始24小时智能监控")
        info("监控系统已启动")
        # ... 其他启动逻辑
    
    def stop_monitoring(self):
        """停止监控"""
        botinfo("⏹️ 停止智能监控系统")
        info("监控系统已停止")
        
        # 关闭日志系统
        if hasattr(self, 'logger'):
            self.logger.close()


# 使用示例：

def example_usage():
    """使用示例"""
    from utils import botinfo, info, warning, error
    
    # 普通日志
    info("这是普通信息日志")
    warning("这是警告日志")
    error("这是错误日志")
    
    # 重要信息 - 会推送到Telegram
    botinfo("🎯 这是重要的机器人信息，会推送到Telegram")
    botinfo("📈 BTC价格突破关键阻力位 $50,000")
    botinfo("⚠️ 检测到异常波动，建议密切关注")


# 日志输出格式示例：
# 控制台: 10:30:45 | INFO | 开始处理币种: BTCUSDT
# 文件: 2024-01-15 10:30:45 | INFO | controller.py:123 | _process_symbol() | 开始处理币种: BTCUSDT  
# Telegram: 🤖 [BOTINFO] 10:30:45\n🚨 BTCUSDT 触发特殊条件，启动智能分析