'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';

/**
 * 登录页面
 * 用户故事："作为一名用户,我希望能登录系统。"
 */
export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { signIn } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // 调用 Firebase 登录
      await signIn(email, password);
      
      // 登录成功，跳转到仪表盘
      router.push('/dashboard');
    } catch (err: unknown) {
      console.error('登录失败:', err);
      if (err instanceof Error) {
        // 处理 Firebase 错误
        if (err.message.includes('user-not-found')) {
          setError('用户不存在');
        } else if (err.message.includes('wrong-password')) {
          setError('密码错误');
        } else if (err.message.includes('invalid-email')) {
          setError('邮箱格式不正确');
        } else if (err.message.includes('invalid-credential')) {
          setError('邮箱或密码错误');
        } else {
          setError('登录失败：' + err.message);
        }
      } else {
        setError('登录失败，请稍后重试');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-xl shadow-lg">
        {/* 头部 */}
        <div>
          <h2 className="text-center text-3xl font-extrabold text-gray-900">
            登录 aether
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            欢迎回来！继续你的协作之旅
          </p>
        </div>

        {/* 表单 */}
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {/* 错误提示 */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative">
              {error}
            </div>
          )}

          <div className="space-y-4">
            {/* 邮箱 */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                邮箱地址
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="your@email.com"
              />
            </div>

            {/* 密码 */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                密码
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="输入密码"
              />
            </div>
          </div>

          {/* 登录按钮 */}
          <div>
            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '登录中...' : '登录'}
            </button>
          </div>

          {/* 注册链接 */}
          <div className="text-center text-sm">
            <span className="text-gray-600">还没有账号？</span>{' '}
            <Link href="/register" className="font-medium text-indigo-600 hover:text-indigo-500">
              立即注册
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
