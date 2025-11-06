'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';

/**
 * 注册页面
 * 用户故事："作为一名新用户，我希望能使用邮箱和密码注册一个 'aether' 账号。"
 */
export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { signUp } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');

    // 验证密码
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    if (password.length < 6) {
      setError('密码至少需要 6 个字符');
      return;
    }

    setLoading(true);

    try {
      // 调用 Firebase 注册
      await signUp(email, password);
      
      // 注册成功，跳转到仪表盘
      router.push('/dashboard');
    } catch (err: unknown) {
      console.error('注册失败:', err);
      if (err instanceof Error) {
        // 处理 Firebase 错误
        if (err.message.includes('email-already-in-use')) {
          setError('该邮箱已被注册');
        } else if (err.message.includes('invalid-email')) {
          setError('邮箱格式不正确');
        } else if (err.message.includes('weak-password')) {
          setError('密码强度太弱');
        } else if (err.message.includes('configuration-not-found')) {
          setError('Firebase 配置错误：请在 Firebase Console 启用 Email/Password 认证方法');
        } else {
          setError('注册失败：' + err.message);
        }
      } else {
        setError('注册失败，请稍后重试');
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
            创建 aether 账号
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            开始你的实时协作之旅
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
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="至少 6 个字符"
              />
            </div>

            {/* 确认密码 */}
            <div>
              <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-700">
                确认密码
              </label>
              <input
                id="confirm-password"
                name="confirm-password"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="再次输入密码"
              />
            </div>
          </div>

          {/* 注册按钮 */}
          <div>
            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? '注册中...' : '注册'}
            </button>
          </div>

          {/* 登录链接 */}
          <div className="text-center text-sm">
            <span className="text-gray-600">已有账号？</span>{' '}
            <Link href="/login" className="font-medium text-indigo-600 hover:text-indigo-500">
              立即登录
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
