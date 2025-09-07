# -*- coding: utf-8 -*-
"""
配置数据类定义
定义系统所有配置项的数据结构
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional


@dataclass
class SystemConfig:
    """系统基础配置"""
    name: str
    version: str
    mode: str
    log_level: str


@dataclass
class MonitorConfig:
    """监控配置"""
    primary_symbols: List[str]
    secondary_symbols: List[str]


@dataclass
class KlineConfig:
    """K线数据配置"""
    fetch_interval: int
    default_period: str
    history_length: int
    timeout: int


@dataclass
class TechnicalIndicatorConfig:
    """技术指标配置"""
    rsi_period: int
    rsi_overbought: float
    rsi_oversold: float
    rsi_extreme_overbought: float
    rsi_extreme_oversold: float
    macd_fast: int
    macd_slow: int
    macd_signal: int
    ma_short: int
    ma_medium: int
    ma_long: int


@dataclass
class TriggerConfig:
    """触发条件配置"""
    normal_interval: int
    emergency_cooldown: int
    trade_confirmation_timeout: int
    rsi_extreme_detection: bool
    rsi_detection_period: int
    price_stop_enabled: bool
    stop_profit_percent: float
    stop_loss_percent: float
    cleanup_interval: int


@dataclass
class RiskManagementConfig:
    """风险管理配置"""
    max_positions: int
    max_position_percent: float
    default_leverage: int
    max_leverage: int
    symbol_leverage: Dict[str, int]
    default_stop_loss: float
    max_stop_loss: float
    default_stop_profit: float
    max_stop_profit: float


@dataclass
class TraderConfig:
    """交易员配置"""
    work_status_detection: bool
    min_work_interval: int
    force_rest_time: int


@dataclass
class DatabaseConfig:
    """数据库配置"""
    filename: str
    retention_days: int
    auto_cleanup: bool


@dataclass
class ModelConfig:
    """LLM模型配置"""
    provider: str
    model: str
    max_tokens: int
    temperature: float


@dataclass
class APIConfig:
    """API配置"""
    technical_analyst: ModelConfig
    market_analyst: ModelConfig
    fundamental_analyst: ModelConfig
    macro_analyst: ModelConfig
    chief_analyst: ModelConfig
    research_director: ModelConfig
    perpetual_trader: ModelConfig
    request_timeout: int
    stream_output: bool
    fallback_enabled: bool
    fallback_model: ModelConfig
    binance_testnet: bool
    binance_timeout: int
    binance_retry: int
    coingecko_interval: int


@dataclass
class NotificationConfig:
    """通知配置"""
    console_output: bool
    log_file: bool
    important_events: List[str]


@dataclass
class PerformanceConfig:
    """性能配置"""
    data_cache: bool
    analysis_mode: str
    queue_interval: int
    memory_limit: int


@dataclass
class Settings:
    """全局配置设置"""
    system: SystemConfig
    monitor: MonitorConfig
    kline: KlineConfig
    indicators: TechnicalIndicatorConfig
    triggers: TriggerConfig
    risk: RiskManagementConfig
    trader: TraderConfig
    database: DatabaseConfig
    api: APIConfig
    notification: NotificationConfig
    performance: PerformanceConfig
    
    def get_symbol_leverage(self, symbol: str) -> int:
        """获取指定币种的杠杆倍数"""
        return self.risk.symbol_leverage.get(symbol, self.risk.default_leverage)