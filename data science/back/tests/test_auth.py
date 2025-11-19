"""
认证 API 测试
"""

import pytest
from flask import json


def test_health_endpoint(client):
    """测试健康检查端点"""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'ok'
    assert 'timestamp' in data


def test_index_endpoint(client):
    """测试根端点"""
    response = client.get('/')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'message' in data
    assert 'version' in data


def test_verify_token_without_auth(client):
    """测试未提供 Token 的验证请求"""
    response = client.post('/api/auth/verify')
    assert response.status_code == 401
    
    data = json.loads(response.data)
    assert 'error' in data


def test_verify_token_invalid_header(client):
    """测试无效的认证头"""
    response = client.post(
        '/api/auth/verify',
        headers={'Authorization': 'InvalidFormat token'}
    )
    assert response.status_code == 401


def test_profile_without_auth(client):
    """测试未认证的用户资料请求"""
    response = client.get('/api/auth/profile')
    assert response.status_code == 401


# 注意: 实际的 Token 验证测试需要 Firebase Admin SDK
# 和有效的测试 Token，这些应该在集成测试中进行
