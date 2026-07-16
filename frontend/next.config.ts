import type { NextConfig } from "next";
import withPWAInit from "@ducanh2912/next-pwa";

const withPWA = withPWAInit({
  dest: "public",
  disable: false,
  register: false,
});

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://backend:8085';

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
        source: '/lista-telefonica/contatos/sync',
        destination: `${API_URL}/lista-telefonica/contatos/sync`,
        basePath: false,
      },
      {
        source: '/lista-telefonica/contatos/:id',
        destination: `${API_URL}/lista-telefonica/contatos/:id`,
        basePath: false,
      },
      {
        source: '/lista-telefonica/contatos',
        destination: `${API_URL}/lista-telefonica/contatos`,
        basePath: false,
      },
      {
        source: '/lista-telefonica/contatos/:path*',
        destination: `${API_URL}/lista-telefonica/contatos/:path*`,
        basePath: false,
      },
    ];
  },
};

export default withPWA(nextConfig);