import ProtectedLayout from '@/components/auth/ProtectedLayout';

/**
 * 主应用布局
 * 包裹所有需要认证的页面（如 dashboard）
 */
export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ProtectedLayout>{children}</ProtectedLayout>;
}
