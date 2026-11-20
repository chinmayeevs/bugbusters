// Enable WebAssembly SWC transforms to run smoothly in restricted environments
process.versions.webcontainer = '1';

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Proxy /graphql to FastAPI backend
  async rewrites() {
    return [
      {
        source: '/graphql/:path*',
        destination: 'http://127.0.0.1:8000/graphql/:path*',
      },
      {
        source: '/health',
        destination: 'http://127.0.0.1:8000/health',
      },
    ];
  },
};

module.exports = nextConfig;
