/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: [],
  },
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  // TypeScript 체크
  typescript: {
    ignoreBuildErrors: false,
  },
  // 실험적 기능으로 빌드 속도 향상
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons'],
  },
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        path: false,
        crypto: false,
      };
    }
    config.cache = {
      type: 'filesystem',
      buildDependencies: {
        config: [__filename],
      },
    };
    return config;
  },
  turbopack: {},
}
module.exports = nextConfig

