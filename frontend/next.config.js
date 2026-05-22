/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Avoid stale chunk errors after hot reload in dev
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = { poll: 1000, aggregateTimeout: 300 };
    }
    return config;
  },
};

module.exports = nextConfig;
