import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      <main className="max-w-4xl mx-auto px-4 py-16 text-center">
        {/* Logo */}
        <div className="mb-8">
          <h1 className="text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">
            aether
          </h1>
          <p className="mt-2 text-xl text-gray-600">
            实时协作平台
          </p>
        </div>

        {/* 描述 */}
        <div className="mb-12">
          <p className="text-lg text-gray-700 max-w-2xl mx-auto">
            基于 Spring Boot 和 Firebase 的实时项目协作平台。
            <br />
            领域驱动设计 (DDD) + 事件驱动架构 (EDA)，
            <br />
            为团队提供"以太"般无所不在的丝滑协作体验。
          </p>
        </div>

        {/* 功能特性 */}
        <div className="grid md:grid-cols-3 gap-6 mb-12 max-w-3xl mx-auto">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-3xl mb-2">🔐</div>
            <h3 className="font-semibold text-gray-900 mb-2">安全认证</h3>
            <p className="text-sm text-gray-600">
              Firebase Authentication + Spring Security
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-3xl mb-2">⚡</div>
            <h3 className="font-semibold text-gray-900 mb-2">实时同步</h3>
            <p className="text-sm text-gray-600">
              WebSocket (STOMP) 实时推送
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-3xl mb-2">🎯</div>
            <h3 className="font-semibold text-gray-900 mb-2">敏捷看板</h3>
            <p className="text-sm text-gray-600">
              项目、看板、列表、卡片管理
            </p>
          </div>
        </div>

        {/* CTA 按钮 */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/register"
            className="px-8 py-3 bg-indigo-600 text-white font-medium rounded-lg shadow-md hover:bg-indigo-700 transition-colors"
          >
            立即注册
          </Link>
          <Link
            href="/login"
            className="px-8 py-3 bg-white text-indigo-600 font-medium rounded-lg shadow-md border-2 border-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            登录
          </Link>
        </div>

        {/* 技术栈 */}
        <div className="mt-16 pt-8 border-t border-gray-200">
          <p className="text-sm text-gray-500 mb-4">技术栈</p>
          <div className="flex flex-wrap justify-center gap-4 text-sm text-gray-600">
            <span className="px-3 py-1 bg-white rounded-full shadow-sm">Spring Boot 3.x</span>
            <span className="px-3 py-1 bg-white rounded-full shadow-sm">Firebase Auth</span>
            <span className="px-3 py-1 bg-white rounded-full shadow-sm">MySQL 8+</span>
            <span className="px-3 py-1 bg-white rounded-full shadow-sm">WebSocket</span>
            <span className="px-3 py-1 bg-white rounded-full shadow-sm">Next.js 16</span>
            <span className="px-3 py-1 bg-white rounded-full shadow-sm">TypeScript</span>
          </div>
        </div>
      </main>
    </div>
  );
}
