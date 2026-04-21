import pytest
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_root_endpoint(client: TestClient):
    """测试根路径接口"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

def test_api_status(client: TestClient):
    """测试API状态接口"""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"

def test_get_data_list(client: TestClient):
    """测试获取数据列表接口"""
    response = client.get("/api/v1/data")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data

def test_get_specific_data(client: TestClient):
    """测试获取特定数据接口"""
    # 先获取数据列表
    response = client.get("/api/v1/data")
    data = response.json()
    if data["data"]:
        # 获取第一个数据项的ID
        item_id = data["data"][0]["id"]
        response = client.get(f"/api/v1/data/{{item_id}}")
        assert response.status_code == 200

def test_analyze_data(client: TestClient):
    """测试数据分析接口"""
    analysis_request = {
        "dataset": "test_dataset",
        "variables": ["var1", "var2"],
        "analysis_type": "statistical"
    }
    response = client.post("/api/v1/analyze", json=analysis_request)
    assert response.status_code == 200
    data = response.json()
    assert "analysis_id" in data
    assert "statistics" in data

def test_user_login_invalid(client: TestClient):
    """测试用户登录失败情况"""
    login_data = {
        "username": "invalid_user",
        "password": "wrong_password"
    }
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401

def test_user_register(client: TestClient):
    """测试用户注册接口"""
    user_data = {
        "username": "test_user",
        "email": "test@example.com",
        "password": "test_password",
        "full_name": "测试用户"
    }
    response = client.post("/api/v1/auth/register", json=user_data)
    # 注册可能成功或失败（取决于是否已存在）
    assert response.status_code in [200, 201, 400]

def test_protected_endpoint_without_token(client: TestClient):
    """测试需要认证的接口（无令牌）"""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401

def test_protected_endpoint_with_invalid_token(client: TestClient):
    """测试需要认证的接口（无效令牌）"""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 401
