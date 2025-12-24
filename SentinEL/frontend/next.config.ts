import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * Standalone 模式配置
   * 
   * 启用后，Next.js 会在构建时将所有必要的依赖打包到 .next/standalone 目录，
   * 大幅减小 Docker 镜像体积 (可减少 80% 以上)。
   * 
   * 这对于 Cloud Run 等 Serverless 平台至关重要，因为它们按内存和启动时间计费。
   */
  output: "standalone",
};

export default nextConfig;
