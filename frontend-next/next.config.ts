import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow dev origins for local development
  allowedDevOrigins: [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.21.199:3000",
  ],
  // Set correct workspace root
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
