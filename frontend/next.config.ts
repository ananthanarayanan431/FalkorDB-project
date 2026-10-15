import type { NextConfig } from "next";

// The FastAPI backend. The browser only talks to this Next server; /api/v1 is
// proxied so the API needs no CORS setup. The voice WebSocket connects to the
// API directly (see NEXT_PUBLIC_VOICE_WS_URL in src/lib/voice.ts).
const API_URL = process.env.API_URL ?? "http://localhost:8000";

// Sent with every response. The microphone stays allowed for this origin only, for voice
// interviews. No full Content-Security-Policy yet: Next's inline scripts would need nonces.
const SECURITY_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
  { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self), payment=(), usb=()" },
];

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  poweredByHeader: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: `${API_URL}/api/v1/:path*` },
      // FastAPI's interactive API reference and the schema it loads.
      { source: "/docs", destination: `${API_URL}/docs` },
      { source: "/openapi.json", destination: `${API_URL}/openapi.json` },
    ];
  },
};

export default nextConfig;
