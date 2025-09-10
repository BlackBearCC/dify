# SQLite工具 - Docker集成完成

## 🎉 集成完成

SQLite工具已成功集成到Docker容器中，现在可以与Dify项目一起启动。

## 📋 集成详情

### ✅ 已完成的配置

1. **Docker服务定义**
   - 服务名称: `sqlite-tool`
   - 端口: 5555 (可通过环境变量配置)
   - 健康检查: 自动监控API可用性
   - 数据持久化: `./docker/volumes/sqlite-tool/data`

2. **环境变量配置**
   - `SQLITE_TOOL_PORT`: 服务端口 (默认: 5555)
   - `SQLITE_TOOL_FLASK_ENV`: Flask环境 (默认: production)
   - `SQLITE_TOOL_PYTHONUNBUFFERED`: Python输出缓冲 (默认: 1)

3. **Docker构建文件**
   - 位置: `docker/sqlite-tool/Dockerfile`
   - 基于: Python 3.11-slim
   - 包含: Flask, Flask-CORS, curl

## 🚀 启动方式

### 方式一：与Dify一起启动（推荐）
```bash
cd docker
docker-compose up -d
```

### 方式二：仅启动SQLite工具
```bash
cd docker
docker-compose up -d sqlite-tool
```

### 方式三：重新构建并启动
```bash
cd docker
docker-compose build sqlite-tool
docker-compose up -d sqlite-tool
```

## 🔍 验证启动

### 检查服务状态
```bash
# 查看所有服务状态
docker-compose ps

# 查看SQLite工具日志
docker-compose logs sqlite-tool

# 实时查看日志
docker-compose logs -f sqlite-tool
```

### 测试API接口
```bash
# 健康检查
curl http://localhost:5555/health

# 测试插入数据
curl -X POST http://localhost:5555/insert_data \
  -H "Content-Type: application/json" \
  -d '{"table": "topics", "data": "{\"type\": \"测试\", \"topic\": \"标题\", \"content\": \"内容\"}"}'
```

## 📁 数据持久化

- **数据库文件位置**: `docker/volumes/sqlite-tool/data/dify_workflow_data.db`
- **自动创建**: 首次启动时会自动创建必要的表结构
- **数据保持**: 容器重启后数据会保持

## 🔧 配置自定义

### 修改端口
```bash
# 在 .env 文件中添加或修改
echo "SQLITE_TOOL_PORT=8888" >> .env

# 重新启动服务
docker-compose up -d sqlite-tool
```

### 修改环境
```bash
# 开发模式
echo "SQLITE_TOOL_FLASK_ENV=development" >> .env
```

## 🛠 在Dify工作流中使用

1. **工具已导入**: SQLite数据库工具已在Dify中可用
2. **API端点**: 容器内部可通过 `http://sqlite-tool:5555` 访问
3. **外部访问**: 主机可通过 `http://localhost:5555` 访问

### DSL配置示例
```yaml
- data:
    desc: 插入数据到SQLite数据库
    provider_id: sqlite_database_tool
    provider_type: api
    title: SQLite存储
    tool_configurations:
      insert_data:
        table: topics
        data: "{{#previous_node.db_data#}}"
    tool_name: insert_data
    type: tool
```

## 📊 监控和维护

### 查看资源使用
```bash
docker stats sqlite-tool
```

### 备份数据库
```bash
# 复制数据库文件
cp docker/volumes/sqlite-tool/data/dify_workflow_data.db backup_$(date +%Y%m%d_%H%M%S).db
```

### 清理和重置
```bash
# 停止并删除容器
docker-compose down sqlite-tool

# 清理数据（慎重！会删除所有数据）
rm -rf docker/volumes/sqlite-tool/data/*

# 重新启动
docker-compose up -d sqlite-tool
```

## ✅ 优势特点

- **🔄 自动重启**: 容器异常退出时自动重启
- **💾 数据持久**: 数据存储在宿主机，容器重建不影响数据
- **🏥 健康检查**: 自动监控服务健康状态
- **🌐 网络隔离**: 在Docker网络中安全运行
- **⚙️ 环境配置**: 支持灵活的环境变量配置
- **📈 可扩展**: 可轻松添加更多SQLite操作功能

现在SQLite工具已完全集成到Docker环境中，可以与Dify无缝协作！