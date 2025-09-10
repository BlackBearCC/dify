# SQLite工具使用说明

## ✅ 您说得对！SQLite不需要启动服务

SQLite是**嵌入式数据库**，直接以文件形式存储，不需要启动任何服务。

## 📁 为您准备的文件

### 1. 工具文件（已就绪）
- **`tools/sqlite_tool.py`** - SQLite工具主文件
- **`tools/sqlite_tool_config.json`** - 工具配置文件（您直接导入这个）

### 2. 数据库文件（自动创建）
- **`dify_workflow_data.db`** - 数据库文件将自动创建在项目根目录

## 🚀 使用步骤

### 第1步：导入工具到Dify
1. 打开Dify管理后台
2. 进入"工具"页面
3. 点击"导入工具"或"添加工具"
4. **上传文件**：`tools/sqlite_tool_config.json`
5. 确认导入成功

### 第2步：使用工具
导入成功后，您的工作流中就可以使用以下工具：

- **`insert_data`** - 插入数据
- **`query_data`** - 查询数据  
- **`get_table_stats`** - 获取表信息

## 📊 预设数据表

工具会**自动创建**以下数据表：

### topics表（话题专用）
```sql
id, type, topic, content, search_keywords, created_at, updated_at, status, metadata
```

### workflow_data表（通用数据）
```sql
id, workflow_name, data_type, title, content, tags, metadata, created_at, updated_at, status
```

### operation_logs表（操作日志）
```sql
id, operation_type, table_name, record_id, details, created_at, workflow_name
```

## 🎯 在DSL中使用示例

```yaml
- data:
    desc: 保存话题到数据库
    provider_id: sqlite_database_tool
    provider_type: builtin
    title: SQLite存储
    tool_configurations:
      insert_data:
        table: topics
        data: "{{#previous_node.json_data#}}"
    tool_name: insert_data
    type: tool
```

## ✅ 测试结果

工具已通过测试：
- ✅ 数据库自动创建
- ✅ 表结构正确
- ✅ 插入数据成功
- ✅ 查询数据正常
- ✅ 统计信息准确

## 💡 重要提醒

1. **数据库位置**：`dify_workflow_data.db` 将在项目根目录自动创建
2. **无需服务**：SQLite是文件数据库，不需要启动任何服务
3. **自动初始化**：首次使用时自动创建所有表结构
4. **线程安全**：支持多个工作流同时使用
5. **错误处理**：完善的错误处理和日志记录

现在您只需要：
1. 将 `tools/sqlite_tool_config.json` 导入到Dify
2. 在工作流中使用SQLite工具
3. 数据会自动保存到SQLite数据库文件中！