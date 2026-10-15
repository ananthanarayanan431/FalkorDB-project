import type { NextConfig } from "next";

// The FastAPI backend. The browser only talks to this Next server; /api/v1 is
// proxied so the API needs no CORS setup. The voice WebSocket connects to the
// API directly (see NEXT_PUBLIC_VOICE_WS_URL in src/lib/voice.ts).
const API_URL = process.env.API_URL ?? "http://localhost:8000";

const isDev = process.env.NODE_ENV === "development";
// Set HTTPS_ONLY=true when the site is served over HTTPS: adds HSTS and upgrades requests.
const httpsOnly = process.env.HTTPS_ONLY === "true";

/** Where the browser may open the voice WebSocket (connect-src). */
function voiceSocketOrigins(): string {
  const configured = process.env.NEXT_PUBLIC_VOICE_WS_URL;
  if (configured) return new URL(configured).origin;
  // Matches the default in src/lib/voice.ts when the app is opened on localhost.
  return "ws://localhost:8000 ws://127.0.0.1:8000";
}

// Static CSP (no nonces), so pages stay prerendered. Next's bootstrap scripts are inline,
// hence 'unsafe-inline' for scripts; the app never renders user-supplied HTML.
// 'unsafe-eval' is only for React's development tooling.
const CSP = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  `connect-src 'self' ${voiceSocketOrigins()}`,
  "media-src 'self' blob:",
  "worker-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  ...(httpsOnly ? ["upgrade-insecure-requests"] : []),
].join("; ");

// Sent with every page. The microphone stays allowed for this origin only, for voice interviews.
const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: CSP },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), geolocation=(), microphone=(self), payment=(), usb=(), browsing-topics=()",
  },
  ...(httpsOnly ? [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" }] : []),
];

const nextConfig: NextConfig = {
  // A self-contained server in .next/standalone, used by the Dockerfile.
  output: "standalone",
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
    return [
      // Every path except the proxied Swagger UI, which loads its scripts from a CDN and
      // gets its headers from the API.
      { source: "/((?!docs$|openapi\\.json$).*)", headers: SECURITY_HEADERS },
    ];
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
