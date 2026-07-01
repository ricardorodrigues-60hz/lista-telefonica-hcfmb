import type { NextConfig } from "next";
import withPWAInit from "@ducanh2912/next-pwa";

const withPWA = withPWAInit({
  dest: "public",
  disable: false, // Let's keep it enabled so we can test PWA offline in dev
  register: false,
});

const nextConfig: NextConfig = {
  reactStrictMode: true,
  basePath: '/lista-telefonica',
  outputFileTracingRoot: __dirname,
  async redirects() {
    return [
      {
        source: '/',
        destination: '/lista-telefonica',
        permanent: false,
        basePath: false,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8085/api/:path*',
      },
    ];
  },
};

export default withPWA(nextConfig);
