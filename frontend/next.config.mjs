/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 在 Docker 中以 standalone 模式输出，体积更小
  output: "standalone",
  // 后端 API 代理（开发期可选，前端默认直接走 NEXT_PUBLIC_API_URL）
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
