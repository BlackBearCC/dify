# -*- coding: utf-8 -*-
"""
配置管理器
负责加载和管理所有系统配置
"""

import yaml
import os
from pathlib import Path
from typing import Optional
from .settings import (
    Settings, SystemConfig, MonitorConfig, KlineConfig, TechnicalIndicatorConfig,
    TriggerConfig, RiskManagementConfig, TraderConfig, DatabaseConfig,
    ModelConfig, APIConfig, NotificationConfig, PerformanceConfig
)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        if config_path is None:
            # 默认配置文件路径
            current_dir = Path(__file__).parent.parent.parent
            config_path = current_dir / "crypto_monitor_config.yaml"
        
        self.config_path = Path(config_path)
        self._settings: Optional[Settings] = None
    
    def load_config(self) -> Settings:
        """
        加载配置文件
        
        Returns:
            Settings: 配置对象
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # 解析配置数据
        settings = self._parse_config(config_data)
        self._settings = settings
        return settings
    
    def get_settings(self) -> Settings:
        """
        获取配置对象，如果未加载则先加载
        
        Returns:
            Settings: 配置对象
        """
        if self._settings is None:
            return self.load_config()
        return self._settings
    
    def _parse_config(self, config_data: dict) -> Settings:
        """
        解析配置数据
        
        Args:
            config_data: 原始配置数据
            
        Returns:
            Settings: 解析后的配置对象
        """
        # 系统配置
        system_data = config_data.get('系统配置', {})
        system_config = SystemConfig(
            name=system_data.get('名称', '加密货币监控系统'),
            version=system_data.get('版本', '2.0'),
            mode=system_data.get('运行模式', '持续监控'),
            log_level=system_data.get('日志级别', 'INFO')
        )
        
        # 监控配置
        monitor_data = config_data.get('监控币种', {})
        monitor_config = MonitorConfig(
            primary_symbols=monitor_data.get('主要币种', []),
            secondary_symbols=monitor_data.get('次要币种', [])
        )
        
        # K线数据配置
        kline_data = config_data.get('K线数据配置', {})
        kline_config = KlineConfig(
            fetch_interval=kline_data.get('获取间隔', 300),
            default_period=kline_data.get('默认时间周期', '15m'),
            history_length=kline_data.get('历史数据长度', 50),
            timeout=kline_data.get('数据源超时', 10)
        )
        
        # 技术指标配置
        indicators_data = config_data.get('技术指标', {})
        rsi_data = indicators_data.get('RSI', {})
        macd_data = indicators_data.get('MACD', {})
        ma_data = indicators_data.get('移动平均线', {})
        
        indicators_config = TechnicalIndicatorConfig(
            rsi_period=rsi_data.get('周期', 14),
            rsi_overbought=rsi_data.get('超买线', 70),
            rsi_oversold=rsi_data.get('超卖线', 30),
            rsi_extreme_overbought=rsi_data.get('极值超买', 80),
            rsi_extreme_oversold=rsi_data.get('极值超卖', 20),
            macd_fast=macd_data.get('快线EMA', 12),
            macd_slow=macd_data.get('慢线EMA', 26),
            macd_signal=macd_data.get('信号线', 9),
            ma_short=ma_data.get('短期', 20),
            ma_medium=ma_data.get('中期', 50),
            ma_long=ma_data.get('长期', 200)
        )
        
        # 触发条件配置
        triggers_data = config_data.get('触发条件', {})
        special_triggers = triggers_data.get('特殊触发', {})
        rsi_extreme = special_triggers.get('RSI极值检测', {})
        price_stop = special_triggers.get('价格止盈止损', {})
        event_cleanup = special_triggers.get('触发事件清理', {})
        
        triggers_config = TriggerConfig(
            normal_interval=triggers_data.get('常规分析间隔', 1800),
            emergency_cooldown=triggers_data.get('紧急分析冷却', 1800),
            trade_confirmation_timeout=triggers_data.get('交易确认超时', 60),
            rsi_extreme_detection=rsi_extreme.get('启用', True),
            rsi_detection_period=rsi_extreme.get('检测周期', 60),
            price_stop_enabled=price_stop.get('启用', True),
            stop_profit_percent=price_stop.get('止盈百分比', 5.0),
            stop_loss_percent=price_stop.get('止损百分比', 3.0),
            cleanup_interval=event_cleanup.get('清理间隔', 300)
        )
        
        # 风险管理配置
        risk_data = config_data.get('风险管理', {})
        symbol_leverage_data = risk_data.get('币种杠杆', {})
        stop_loss_data = risk_data.get('止损设置', {})
        stop_profit_data = risk_data.get('止盈设置', {})
        
        risk_config = RiskManagementConfig(
            max_positions=risk_data.get('最大持仓数', 6),
            max_position_percent=risk_data.get('单笔最大仓位', 20.0),
            default_leverage=risk_data.get('默认杠杆', 5),
            max_leverage=risk_data.get('最大杠杆', 20),
            symbol_leverage=dict(symbol_leverage_data),
            default_stop_loss=stop_loss_data.get('默认止损', 5.0),
            max_stop_loss=stop_loss_data.get('最大止损', 15.0),
            default_stop_profit=stop_profit_data.get('默认止盈', 10.0),
            max_stop_profit=stop_profit_data.get('最大止盈', 50.0)
        )
        
        # 交易员配置
        trader_data = config_data.get('交易员设置', {})
        trader_config = TraderConfig(
            work_status_detection=trader_data.get('工作状态检测', True),
            min_work_interval=trader_data.get('最小工作间隔', 600),
            force_rest_time=trader_data.get('强制休息时间', 3600)
        )
        
        # 数据库配置
        db_data = config_data.get('数据库配置', {})
        db_config = DatabaseConfig(
            filename=db_data.get('文件名', 'crypto_monitor.db'),
            retention_days=db_data.get('数据保留天数', 30),
            auto_cleanup=db_data.get('自动清理', True)
        )
        
        # API配置
        api_data = config_data.get('API配置', {})
        models_data = api_data.get('分析师模型', {})
        general_data = api_data.get('通用设置', {})
        fallback_data = api_data.get('兜底模型', {})
        binance_data = api_data.get('Binance', {})
        coingecko_data = api_data.get('CoinGecko', {})
        
        # 解析各个分析师模型配置
        def parse_model_config(model_data: dict) -> ModelConfig:
            return ModelConfig(
                provider=model_data.get('提供商', 'doubao'),
                model=model_data.get('模型', 'doubao-1.5-lite-32k'),
                max_tokens=model_data.get('最大令牌', 1000),
                temperature=model_data.get('温度', 0.5)
            )
        
        api_config = APIConfig(
            technical_analyst=parse_model_config(models_data.get('技术分析师', {})),
            market_analyst=parse_model_config(models_data.get('市场分析师', {})),
            fundamental_analyst=parse_model_config(models_data.get('基本面分析师', {})),
            macro_analyst=parse_model_config(models_data.get('宏观分析师', {})),
            chief_analyst=parse_model_config(models_data.get('首席分析师', {})),
            research_director=parse_model_config(models_data.get('研究部门总监', {})),
            perpetual_trader=parse_model_config(models_data.get('永续交易员', {})),
            request_timeout=general_data.get('请求超时', 60),
            stream_output=general_data.get('流式输出', True),
            fallback_enabled=fallback_data.get('启用', True),
            fallback_model=parse_model_config(fallback_data),
            binance_testnet=binance_data.get('测试网', False),
            binance_timeout=binance_data.get('请求超时', 15),
            binance_retry=binance_data.get('重试次数', 3),
            coingecko_interval=coingecko_data.get('请求间隔', 10)
        )
        
        # 通知配置
        notification_data = config_data.get('通知配置', {})
        notification_config = NotificationConfig(
            console_output=notification_data.get('控制台输出', True),
            log_file=notification_data.get('日志文件', True),
            important_events=notification_data.get('重要事件通知', [])
        )
        
        # 性能配置
        performance_data = config_data.get('性能设置', {})
        performance_config = PerformanceConfig(
            data_cache=performance_data.get('数据缓存', True),
            analysis_mode=performance_data.get('分析模式', '队列'),
            queue_interval=performance_data.get('队列间隔', 5),
            memory_limit=performance_data.get('内存限制', 512)
        )
        
        return Settings(
            system=system_config,
            monitor=monitor_config,
            kline=kline_config,
            indicators=indicators_config,
            triggers=triggers_config,
            risk=risk_config,
            trader=trader_config,
            database=db_config,
            api=api_config,
            notification=notification_config,
            performance=performance_config
        )
    
    def reload_config(self) -> Settings:
        """
        重新加载配置文件
        
        Returns:
            Settings: 新的配置对象
        """
        return self.load_config()
    
    def save_dynamic_config(self, dynamic_updates: dict):
        """
        保存动态配置更改
        
        Args:
            dynamic_updates: 动态更新的配置项
        """
        try:
            # 为了简单起见，我们将动态配置保存到一个单独的文件
            dynamic_config_path = self.config_path.parent / "dynamic_config.yaml"
            
            # 加载现有的动态配置（如果存在）
            existing_config = {}
            if dynamic_config_path.exists():
                with open(dynamic_config_path, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f) or {}
            
            # 更新配置
            for section, values in dynamic_updates.items():
                if section not in existing_config:
                    existing_config[section] = {}
                existing_config[section].update(values)
            
            # 保存到文件
            with open(dynamic_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(existing_config, f, default_flow_style=False, allow_unicode=True)
            
            print(f"✅ 动态配置已保存到: {dynamic_config_path}")
            
        except Exception as e:
            print(f"⚠️ 保存动态配置失败: {e}")