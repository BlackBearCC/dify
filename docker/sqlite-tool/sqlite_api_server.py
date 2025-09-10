"""
SQLite Tool Flask API Server for Dify
提供HTTP API接口供Dify调用SQLite操作
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import sys
import os

# 导入我们的SQLite工具
sys.path.append(os.path.dirname(__file__))
from sqlite_tool import insert_data, query_data, get_table_stats

app = Flask(__name__)
CORS(app)  # 允许跨域请求

@app.route('/insert_data', methods=['POST'])
def api_insert_data():
    """插入数据API端点"""
    try:
        # 获取JSON数据
        if not request.is_json:
            return jsonify({
                "success": False,
                "error": "Content-Type must be application/json"
            }), 400
            
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body must contain valid JSON"
            }), 400
            
        table = data.get('table')
        insert_data_json = data.get('data')
        
        if not table or not insert_data_json:
            return jsonify({
                "success": False,
                "error": "Missing required parameters: table and data"
            }), 400
        
        # 调用SQLite工具函数
        result_json = insert_data(table, insert_data_json)
        result = json.loads(result_json)
        
        return jsonify(result), 200 if result.get('success') else 400
        
    except json.JSONDecodeError as e:
        return jsonify({
            "success": False,
            "error": "Invalid JSON in request",
            "details": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "details": str(e)
        }), 500

@app.route('/query_data', methods=['POST'])
def api_query_data():
    """查询数据API端点"""
    try:
        if not request.is_json:
            return jsonify({
                "success": False,
                "error": "Content-Type must be application/json"
            }), 400
            
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body must contain valid JSON"
            }), 400
            
        table = data.get('table')
        conditions = data.get('conditions', '{}')
        limit = data.get('limit', 10)
        order_by = data.get('order_by', 'created_at DESC')
        
        if not table:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: table"
            }), 400
        
        # 调用SQLite工具函数
        result_json = query_data(table, conditions, limit, order_by)
        result = json.loads(result_json)
        
        return jsonify(result), 200 if result.get('success') else 400
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "details": str(e)
        }), 500

@app.route('/get_table_stats', methods=['POST'])
def api_get_table_stats():
    """获取表统计信息API端点"""
    try:
        if not request.is_json:
            return jsonify({
                "success": False,
                "error": "Content-Type must be application/json"
            }), 400
            
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body must contain valid JSON"
            }), 400
            
        table = data.get('table')
        
        if not table:
            return jsonify({
                "success": False,
                "error": "Missing required parameter: table"
            }), 400
        
        # 调用SQLite工具函数
        result_json = get_table_stats(table)
        result = json.loads(result_json)
        
        return jsonify(result), 200 if result.get('success') else 400
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "details": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "healthy",
        "service": "SQLite Tool API",
        "version": "1.0.0"
    })

@app.route('/', methods=['GET'])
def root():
    """根路径信息"""
    return jsonify({
        "service": "SQLite Tool API for Dify",
        "version": "1.0.0",
        "endpoints": [
            "POST /insert_data",
            "POST /query_data", 
            "POST /get_table_stats",
            "GET /health"
        ],
        "documentation": "See sqlite_tool_openapi.yaml for API specification"
    })

if __name__ == '__main__':
    print("Starting SQLite Tool API Server...")
    print("Database will be created at: dify_workflow_data.db")
    print("API will be available at: http://localhost:5555")
    print("OpenAPI spec: sqlite_tool_openapi.yaml")
    print("Test with: curl -X GET http://localhost:5555/health")
    
    # 启动Flask应用
    app.run(
        host='0.0.0.0',
        port=5555,
        debug=True
    )