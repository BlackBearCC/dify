"""
Universal SQLite Database Tool for Dify
通用SQLite数据库工具 - Dify集成版本
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional


class UniversalSQLiteManager:
    """通用SQLite数据库管理器"""
    
    def __init__(self, db_path: str = None):
        # 如果没有指定路径，使用当前工作目录下的数据库文件
        if db_path is None:
            db_path = os.path.join(os.getcwd(), "dify_workflow_data.db")
        
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = self._get_connection()
        try:
            # 话题生成表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    search_keywords TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    metadata TEXT,
                    UNIQUE(topic, type)
                )
            ''')
            
            # 通用工作流数据表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workflow_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_name TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    tags TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # 操作日志表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    table_name TEXT,
                    record_id INTEGER,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    workflow_name TEXT
                )
            ''')
            
            conn.commit()
        finally:
            conn.close()
    
    def insert_record(self, table: str, data: dict) -> dict:
        """插入记录"""
        conn = self._get_connection()
        try:
            # 添加更新时间
            data = dict(data)  # 创建副本避免修改原数据
            if 'updated_at' not in data:
                data['updated_at'] = datetime.now().isoformat()
            
            # 构建SQL
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data])
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            cursor = conn.execute(sql, list(data.values()))
            record_id = cursor.lastrowid
            conn.commit()
            
            # 记录日志
            self._log_operation('INSERT', table, record_id, str(data))
            
            return {
                "success": True,
                "record_id": record_id,
                "message": f"Successfully inserted record into {table}"
            }
            
        except sqlite3.IntegrityError as e:
            return {
                "success": False,
                "error": "Data integrity error",
                "details": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Insert operation failed",
                "details": str(e)
            }
        finally:
            conn.close()
    
    def query_records(self, table: str, conditions: dict = None, limit: int = 10, order_by: str = "created_at DESC") -> dict:
        """查询记录"""
        conn = self._get_connection()
        try:
            sql = f"SELECT * FROM {table}"
            params = []
            
            if conditions:
                where_clauses = []
                for key, value in conditions.items():
                    if isinstance(value, str) and '*' in value:
                        where_clauses.append(f"{key} LIKE ?")
                        params.append(value.replace('*', '%'))
                    else:
                        where_clauses.append(f"{key} = ?")
                        params.append(value)
                
                if where_clauses:
                    sql += f" WHERE {' AND '.join(where_clauses)}"
            
            sql += f" ORDER BY {order_by} LIMIT {limit}"
            
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            
            return {
                "success": True,
                "count": len(results),
                "data": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": "Query operation failed",
                "details": str(e)
            }
        finally:
            conn.close()
    
    def get_table_info(self, table: str) -> dict:
        """获取表信息"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()[0]
            
            return {
                "success": True,
                "table": table,
                "columns": [dict(col) for col in columns],
                "record_count": count
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": "Failed to get table info",
                "details": str(e)
            }
        finally:
            conn.close()
    
    def _log_operation(self, operation_type: str, table_name: str, record_id: int, details: str):
        """记录操作日志"""
        try:
            conn = self._get_connection()
            conn.execute(
                "INSERT INTO operation_logs (operation_type, table_name, record_id, details) VALUES (?, ?, ?, ?)",
                [operation_type, table_name, record_id, details]
            )
            conn.commit()
            conn.close()
        except:
            pass  # 日志失败不影响主要操作


# 全局数据库管理器实例
_db_manager = None

def _get_db_manager():
    """获取数据库管理器实例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = UniversalSQLiteManager()
    return _db_manager


# Dify工具函数接口
def insert_data(table: str, data: str) -> str:
    """
    插入数据到SQLite表
    
    Args:
        table: 表名
        data: JSON格式的数据
    
    Returns:
        操作结果的JSON字符串
    """
    try:
        db_manager = _get_db_manager()
        data_dict = json.loads(data)
        result = db_manager.insert_record(table, data_dict)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False, 
            "error": "Invalid JSON format", 
            "details": str(e)
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False, 
            "error": "Operation failed", 
            "details": str(e)
        }, ensure_ascii=False)


def query_data(table: str, conditions: str = "{}", limit: int = 10, order_by: str = "created_at DESC") -> str:
    """
    查询SQLite表数据
    
    Args:
        table: 表名
        conditions: JSON格式的查询条件
        limit: 限制返回数量
        order_by: 排序方式
    
    Returns:
        查询结果的JSON字符串
    """
    try:
        db_manager = _get_db_manager()
        conditions_dict = json.loads(conditions) if conditions.strip() != "{}" else {}
        result = db_manager.query_records(table, conditions_dict, limit, order_by)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False, 
            "error": "Invalid JSON format in conditions", 
            "details": str(e)
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({
            "success": False, 
            "error": "Query failed", 
            "details": str(e)
        }, ensure_ascii=False)


def get_table_stats(table: str) -> str:
    """
    获取表统计信息
    
    Args:
        table: 表名
    
    Returns:
        表信息的JSON字符串
    """
    try:
        db_manager = _get_db_manager()
        result = db_manager.get_table_info(table)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False, 
            "error": "Failed to get table stats", 
            "details": str(e)
        }, ensure_ascii=False)


# 测试函数
if __name__ == "__main__":
    # 测试基本功能
    print("Testing SQLite Tool...")
    
    # 测试插入
    test_data = {
        "type": "测试类型",
        "topic": "测试话题", 
        "content": "这是一个测试内容",
        "search_keywords": "测试 关键词"
    }
    
    result = insert_data("topics", json.dumps(test_data))
    print("Insert Result:", result)
    
    # 测试查询
    query_result = query_data("topics", "{}", 5)
    print("Query Result:", query_result)
    
    # 测试表信息
    stats_result = get_table_stats("topics")
    print("Table Stats:", stats_result)