# darwin-framework API文档

## 概述

本文档描述了darwin-framework项目的API接口规范和使用方法。

## 快速开始

### 基础URL

```
http://localhost:8000/api/v1
```

### 认证方式

所有API请求需要在请求头中包含JWT令牌：

```
Authorization: Bearer <your-jwt-token>
```

### 获取令牌

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your-username", "password": "your-password"}'
```

## API接口

### 基础接口

#### 健康检查
```http
GET /health
```

**响应示例：**
```json
{
  "status": "healthy",
  "service": "darwin-framework",
  "version": "1.0.0"
}
```

#### 系统状态
```http
GET /api/v1/status
```

**响应示例：**
```json
{
  "status": "operational",
  "uptime": "99.9%",
  "response_time": "45ms"
}
```

### 数据接口

#### 获取数据列表
```http
GET /api/v1/data
```

**查询参数：**
- `page`: 页码（默认1）
- `limit`: 每页数量（默认20）
- `sort`: 排序字段
- `order`: 排序方向（asc/desc）

**响应示例：**
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

#### 上传数据
```http
POST /api/v1/data
Content-Type: multipart/form-data
```

**请求体：**
- `file`: 数据文件
- `metadata`: 元数据（JSON格式）

#### 获取特定数据
```http
GET /api/v1/data/{id}
```

### 分析接口

#### 数据分析
```http
POST /api/v1/analyze
Content-Type: application/json
```

**请求体：**
```json
{
  "dataset": "dataset_name",
  "variables": ["var1", "var2"],
  "analysis_type": "statistical",
  "parameters": {
    "method": "regression",
    "confidence_level": 0.95
  }
}
```

**响应示例：**
```json
{
  "analysis_id": "analysis_001",
  "summary": {
    "dataset": "dataset_name",
    "variables": ["var1", "var2"]
  },
  "statistics": {
    "mean": 0.5,
    "std": 0.1,
    "p_value": 0.05
  },
  "visualizations": ["histogram.png", "scatter_plot.png"],
  "conclusions": ["数据呈正态分布", "变量间存在显著相关性"]
}
```

### 用户接口

#### 用户登录
```http
POST /api/v1/auth/login
Content-Type: application/json
```

**请求体：**
```json
{
  "username": "your-username",
  "password": "your-password"
}
```

**响应示例：**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### 用户注册
```http
POST /api/v1/auth/register
Content-Type: application/json
```

**请求体：**
```json
{
  "username": "new-username",
  "email": "user@example.com",
  "password": "secure-password",
  "full_name": "用户姓名"
}
```

## 错误处理

### 错误响应格式

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "请求参数无效",
    "details": {
      "field": "email",
      "reason": "邮箱格式不正确"
    }
  }
}
```

### 常见错误码

- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证
- `403 Forbidden`: 无权限
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

## SDK和工具

### Python SDK

```python
import requests

class DarwinframeworkClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def get_data(self, page=1, limit=20):
        response = requests.get(
            f"{self.base_url}/api/v1/data",
            params={"page": page, "limit": limit},
            headers=self.headers
        )
        return response.json()
    
    def analyze(self, dataset, variables, analysis_type):
        response = requests.post(
            f"{self.base_url}/api/v1/analyze",
            json={
                "dataset": dataset,
                "variables": variables,
                "analysis_type": analysis_type
            },
            headers=self.headers
        )
        return response.json()
```

### 使用示例

```python
# 初始化客户端
client = DarwinframeworkClient(
    base_url="http://localhost:8000",
    token="your-jwt-token"
)

# 获取数据
data = client.get_data(page=1, limit=10)
print(data)

# 分析数据
analysis = client.analyze(
    dataset="my_dataset",
    variables=["var1", "var2"],
    analysis_type="statistical"
)
print(analysis)
```

## 部署说明

### 开发环境

```bash
# 克隆仓库
git clone https://github.com/MoKangMedical/darwin-framework.git
cd darwin-framework

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑.env文件

# 启动服务
python -m uvicorn src.main:app --reload
```

### 生产环境

```bash
# 使用Docker Compose
docker-compose up -d

# 或手动部署
# 参考部署文档
```

## 监控和日志

### 监控端点

- `/metrics`: Prometheus指标
- `/health`: 健康检查
- `/status`: 系统状态

### 日志配置

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/darwin-framework/app.log'),
        logging.StreamHandler()
    ]
)
```

## 常见问题

### Q: 如何重置密码？

A: 访问 `/api/v1/auth/reset-password` 接口，提供邮箱地址。

### Q: 如何申请API密钥？

A: 登录后访问 `/api/v1/settings/api-keys` 生成新的API密钥。

### Q: 请求频率限制是多少？

A: 默认限制为每分钟100次请求，可通过配置文件调整。

## 联系方式

- 项目维护者: MoKangMedical
- 邮箱: contact@mokangmedical.com
- 项目主页: https://github.com/MoKangMedical/darwin-framework

## 更新日志

请查看 [CHANGELOG.md](../CHANGELOG.md) 获取最新更新信息。
