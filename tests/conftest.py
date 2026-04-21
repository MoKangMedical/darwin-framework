import pytest
import asyncio
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def sample_data():
    """提供示例测试数据"""
    return {
        "name": "测试数据",
        "value": 123,
        "description": "这是一个测试数据"
    }
