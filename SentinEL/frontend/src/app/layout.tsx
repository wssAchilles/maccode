import type { Metadata, Viewport } from "next";
import "./globals.css";

// 元数据配置
export const metadata: Metadata = {
  title: "SentinEL Command Center | AI-Powered Customer Retention",
  description: "企业级 AI 客户流失预测与挽留平台 - 基于 Vertex AI 和 Gemini 构建",
  keywords: ["AI", "Customer Retention", "Churn Prediction", "SaaS", "Enterprise"],
  authors: [{ name: "SentinEL Team" }],
};

// Viewport 配置
export const viewport: Viewport = {
  themeColor: "#0F172A",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="dark">
      <head>
        {/* 预连接 Google Fonts */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="font-sans antialiased bg-slate-950 text-slate-100 min-h-screen">
        {children}
      </body>
    </html>
  );
}
