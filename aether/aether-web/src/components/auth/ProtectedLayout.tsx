'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';

/**
 * 受保护的布局组件
 * 用于包裹需要认证才能访问的页面
 * 
 * 功能：
 * 1. 检查用户是否已登录
 * 2. 如果未登录，重定向到登录页
 * 3. 显示加载状态
 */
export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // 如果加载完成且用户未登录，重定向到登录页
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  // 显示加载状态
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
          <p className="mt-4 text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  // 如果未登录，显示空白（即将重定向）
  if (!user) {
    return null;
  }

  // 已登录，渲染子组件
  return <>{children}</>;
}
