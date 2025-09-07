# -*- coding: utf-8 -*-
"""
数据库管理器
负责所有数据库操作，包括数据存储、查询和维护
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Any, Dict
from pathlib import Path

from .models import MarketData, AnalysisRecord, TriggerEvent
from ..config import Settings


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, settings: Settings):
        """
        初始化数据库管理器
        
        Args:
            settings: 系统配置对象
        """
        self.settings = settings
        self.db_path = self._get_db_path()
        self._init_database()
    
    def _get_db_path(self) -> Path:
        """获取数据库文件路径"""
        # 数据库文件与脚本在同一目录
        current_dir = Path(__file__).parent.parent.parent
        return current_dir / self.settings.database.filename
    
    def _init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建市场数据表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    price REAL NOT NULL,
                    rsi REAL,
                    macd REAL,
                    volume REAL DEFAULT 0,
                    ma_20 REAL,
                    ma_50 REAL,
                    ma_200 REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp)
                )
            ''')
            
            # 创建分析记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data_type TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    symbol TEXT,
                    content TEXT NOT NULL,
                    summary TEXT,
                    status TEXT DEFAULT 'pending',
                    metadata TEXT
                )
            ''')
            
            # 创建触发事件表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trigger_events (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    data TEXT,
                    status TEXT DEFAULT 'pending'
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time ON market_data(symbol, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analysis_records_type_time ON analysis_records(data_type, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trigger_events_symbol_type ON trigger_events(symbol, event_type)')
            
            conn.commit()
    
    def save_market_data(self, data: MarketData) -> bool:
        """
        保存市场数据
        
        Args:
            data: 市场数据对象
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO market_data 
                    (symbol, timestamp, price, rsi, macd, volume, ma_20, ma_50, ma_200)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data.symbol, data.timestamp, data.price, data.rsi, data.macd,
                    data.volume, data.ma_20, data.ma_50, data.ma_200
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ 保存市场数据失败: {e}")
            return False
    
    def save_analysis_record(self, record: AnalysisRecord) -> bool:
        """
        保存分析记录
        
        Args:
            record: 分析记录对象
            
        Returns:
            bool: 保存是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO analysis_records 
                    (data_type, agent_name, symbol, content, summary, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record.data_type, record.agent_name, record.symbol,
                    record.content, record.summary, record.status, record.metadata
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ 保存分析记录失败: {e}")
            return False
    
    def save_trigger_event(self, event: TriggerEvent) -> bool:
        """
        保存触发事件
        
        Args:
            event: 触发事件对象
            
        Returns:
            bool: 保存是否成功
        """
        try:
            if not event.id:
                event.id = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO trigger_events 
                    (id, symbol, event_type, data, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    event.id, event.symbol, event.event_type, event.data, event.status
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ 保存触发事件失败: {e}")
            return False
    
    def get_latest_market_data(self, symbol: str, limit: int = 100) -> List[MarketData]:
        """
        获取最新的市场数据
        
        Args:
            symbol: 交易对符号
            limit: 返回条数限制
            
        Returns:
            List[MarketData]: 市场数据列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT symbol, timestamp, price, rsi, macd, volume, ma_20, ma_50, ma_200
                    FROM market_data 
                    WHERE symbol = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (symbol, limit))
                
                rows = cursor.fetchall()
                return [MarketData(*row) for row in rows]
        except Exception as e:
            print(f"❌ 获取市场数据失败: {e}")
            return []
    
    def get_analysis_records(self, data_type: Optional[str] = None, 
                           agent_name: Optional[str] = None,
                           limit: int = 50) -> List[AnalysisRecord]:
        """
        获取分析记录
        
        Args:
            data_type: 数据类型过滤
            agent_name: 分析师名称过滤
            limit: 返回条数限制
            
        Returns:
            List[AnalysisRecord]: 分析记录列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT id, timestamp, data_type, agent_name, symbol, content, summary, status, metadata
                    FROM analysis_records 
                '''
                params = []
                
                conditions = []
                if data_type:
                    conditions.append('data_type = ?')
                    params.append(data_type)
                if agent_name:
                    conditions.append('agent_name = ?')
                    params.append(agent_name)
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
                
                query += ' ORDER BY timestamp DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                records = []
                for row in rows:
                    record = AnalysisRecord(
                        id=row[0], timestamp=row[1], data_type=row[2], agent_name=row[3],
                        symbol=row[4], content=row[5], summary=row[6], status=row[7], metadata=row[8]
                    )
                    records.append(record)
                
                return records
        except Exception as e:
            print(f"❌ 获取分析记录失败: {e}")
            return []
    
    def get_trigger_events(self, symbol: Optional[str] = None,
                          event_type: Optional[str] = None,
                          status: Optional[str] = None) -> List[TriggerEvent]:
        """
        获取触发事件
        
        Args:
            symbol: 交易对符号过滤
            event_type: 事件类型过滤
            status: 状态过滤
            
        Returns:
            List[TriggerEvent]: 触发事件列表
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT id, symbol, event_type, timestamp, data, status
                    FROM trigger_events 
                '''
                params = []
                
                conditions = []
                if symbol:
                    conditions.append('symbol = ?')
                    params.append(symbol)
                if event_type:
                    conditions.append('event_type = ?')
                    params.append(event_type)
                if status:
                    conditions.append('status = ?')
                    params.append(status)
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
                
                query += ' ORDER BY timestamp DESC'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                events = []
                for row in rows:
                    event = TriggerEvent(
                        id=row[0], symbol=row[1], event_type=row[2],
                        timestamp=row[3], data=row[4], status=row[5]
                    )
                    events.append(event)
                
                return events
        except Exception as e:
            print(f"❌ 获取触发事件失败: {e}")
            return []
    
    def update_trigger_event_status(self, event_id: str, status: str) -> bool:
        """
        更新触发事件状态
        
        Args:
            event_id: 事件ID
            status: 新状态
            
        Returns:
            bool: 更新是否成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE trigger_events SET status = ? WHERE id = ?
                ''', (status, event_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ 更新触发事件状态失败: {e}")
            return False
    
    def cleanup_old_data(self) -> bool:
        """
        清理过期数据
        
        Returns:
            bool: 清理是否成功
        """
        try:
            retention_days = self.settings.database.retention_days
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 清理旧的市场数据
                cursor.execute('''
                    DELETE FROM market_data 
                    WHERE created_at < ?
                ''', (cutoff_date,))
                market_deleted = cursor.rowcount
                
                # 清理旧的分析记录
                cursor.execute('''
                    DELETE FROM analysis_records 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                analysis_deleted = cursor.rowcount
                
                # 清理旧的触发事件
                cursor.execute('''
                    DELETE FROM trigger_events 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                trigger_deleted = cursor.rowcount
                
                conn.commit()
                
                if market_deleted > 0 or analysis_deleted > 0 or trigger_deleted > 0:
                    print(f"🧹 数据清理完成: 市场数据({market_deleted}), 分析记录({analysis_deleted}), 触发事件({trigger_deleted})")
                
                return True
        except Exception as e:
            print(f"❌ 数据清理失败: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, int]:
        """
        获取数据库统计信息
        
        Returns:
            Dict[str, int]: 统计信息
        """
        stats = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 市场数据统计
                cursor.execute('SELECT COUNT(*) FROM market_data')
                stats['market_data_count'] = cursor.fetchone()[0]
                
                # 分析记录统计
                cursor.execute('SELECT COUNT(*) FROM analysis_records')
                stats['analysis_records_count'] = cursor.fetchone()[0]
                
                # 触发事件统计
                cursor.execute('SELECT COUNT(*) FROM trigger_events')
                stats['trigger_events_count'] = cursor.fetchone()[0]
                
                # 数据库文件大小
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                stats['database_size_mb'] = round(db_size / (1024 * 1024), 2)
                
        except Exception as e:
            print(f"❌ 获取数据库统计信息失败: {e}")
        
        return stats