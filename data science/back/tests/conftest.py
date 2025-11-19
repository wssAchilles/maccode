"""
Pytest 配置文件
提供测试夹具和公共配置
"""

import pytest
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import create_app
from services.firebase_service import FirebaseService


@pytest.fixture
def app():
    """创建测试应用实例"""
    os.environ['FLASK_ENV'] = 'testing'
    app = create_app('development')
    app.config['TESTING'] = True
    yield app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """创建 CLI 测试运行器"""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers():
    """提供认证头部（用于测试需要认证的端点）"""
    # 在实际测试中，应该使用真实的测试 Token
    # 这里仅作示例
    return {
        'Authorization': 'Bearer test-token-12345'
    }


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        'uid': 'test-user-123',
        'email': 'test@example.com',
        'name': 'Test User',
        'email_verified': True
    }


@pytest.fixture
def sample_file_data():
    """示例文件数据"""
    return {
        'filename': 'test_data.csv',
        'content_type': 'text/csv',
        'size': 1024
    }
