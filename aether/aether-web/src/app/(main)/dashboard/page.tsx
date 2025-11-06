'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import apiClient from '@/lib/apiClient';

/**
 * 仪表盘页面
 * 这是用户登录后的主页面
 * 
 * 功能：
 * 1. 显示当前登录用户信息
 * 2. 提供登出功能
 * 3. 测试后端认证闭环
 */
export default function DashboardPage() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [testResult, setTestResult] = useState<string>('');
  const [testLoading, setTestLoading] = useState(false);

  /**
   * 处理登出
   */
  const handleSignOut = async () => {
    try {
      await signOut();
      router.push('/login');
    } catch (error) {
      console.error('登出失败:', error);
    }
  };

  /**
   * 测试后端认证
   * 调用后端的 /auth/me 端点，验证认证闭环是否成功
   */
  const testBackendAuth = async () => {
    setTestResult('');
    setTestLoading(true);

    try {
      // apiClient 会自动附加 Firebase Token
      const response = await apiClient.get('/auth/me');
      
      setTestResult(JSON.stringify(response.data, null, 2));
    } catch (error: unknown) {
      console.error('调用后端失败:', error);
      if (error instanceof Error) {
        setTestResult(`错误: ${error.message}`);
      } else {
        setTestResult('调用后端失败');
      }
    } finally {
      setTestLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 导航栏 */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-indigo-600">aether</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-700">
                {user?.email}
              </span>
              <button
                onClick={handleSignOut}
                className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                登出
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* 主内容 */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          {/* 欢迎卡片 */}
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              欢迎来到 aether！
            </h2>
            <p className="text-gray-600">
              你已成功登录。这是你的协作仪表盘。
            </p>
          </div>

          {/* 用户信息卡片 */}
          <div className="bg-white shadow rounded-lg p-6 mb-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              用户信息
            </h3>
            <div className="space-y-2">
              <div>
                <span className="text-sm font-medium text-gray-500">UID:</span>
                <span className="ml-2 text-sm text-gray-900">{user?.uid}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-gray-500">邮箱:</span>
                <span className="ml-2 text-sm text-gray-900">{user?.email}</span>
              </div>
              <div>
                <span className="text-sm font-medium text-gray-500">邮箱验证:</span>
                <span className="ml-2 text-sm text-gray-900">
                  {user?.emailVerified ? '已验证' : '未验证'}
                </span>
              </div>
            </div>
          </div>

          {/* 后端认证测试卡片 */}
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              后端认证测试
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              点击下方按钮测试与后端的认证闭环。如果成功，说明前后端认证已完全打通。
            </p>
            <button
              onClick={testBackendAuth}
              disabled={testLoading}
              className="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {testLoading ? '测试中...' : 'Test Backend Auth'}
            </button>

            {/* 测试结果 */}
            {testResult && (
              <div className="mt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">响应:</h4>
                <pre className="bg-gray-50 border border-gray-200 rounded p-4 text-xs overflow-x-auto">
                  {testResult}
                </pre>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
