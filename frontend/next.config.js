const path = require("path");
const createNextIntlPlugin = require("next-intl/plugin");
const { withSentryConfig } = require("@sentry/nextjs");

const withNextIntl = createNextIntlPlugin();

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,
  output: "standalone",
  // Pin the Turbopack workspace root to the monorepo root in development.
  // In production builds, omitting this ensures output: standalone generates server.js at the project root.
  ...(process.env.NODE_ENV !== "production"
    ? {
        turbopack: {
          root: path.join(__dirname, ".."),
        },
      }
    : {}),
  // Type errors now fail the build. Keep this off: it previously masked a
  // runtime crash (/cases), a broken endpoint and two build-breaking imports.
  typescript: {
    ignoreBuildErrors: false,
  },
  images: {
    formats: ["image/avif", "image/webp"],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048],
    imageSizes: [16, 32, 48, 64, 96, 128, 256],
    minimumCacheTTL: 60,
  },
  experimental: {
    // Critters runs a heavy CSS pipeline per compile; in dev this spawns
    // node workers on every cold start and can exhaust memory. Prod only.
    optimizeCss: process.env.NODE_ENV === "production",
    optimizePackageImports: ["lucide-react", "recharts", "reactflow"],
  },
  compiler: {
    removeConsole: process.env.NODE_ENV === "production" ? { exclude: ["error", "warn"] } : false,
  },
  // Optimize webpack file watcher to prevent CPU spikes / overheating
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        aggregateTimeout: 300,
        poll: false,
        ignored: [
          "**/node_modules/**",
          "**/.next/**",
          "**/backend/**",
          "**/coverage/**",
          "**/playwright-report/**",
          "**/test-results/**",
          "**/.git/**",
          "**/docs/**",
          "**/__pycache__/**",
          "**/.pytest_cache/**",
        ],
      };
    }
    return config;
  },
  async rewrites() {
    const backendUrl = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8088").replace(
      "localhost",
      "127.0.0.1"
    );
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
  async headers() {
    const securityHeaders = [
      { key: "X-Frame-Options", value: "DENY" },
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
      ...(process.env.NODE_ENV === "production" && process.env.ENABLE_HSTS === "true"
        ? [
            {
              key: "Strict-Transport-Security",
              value: "max-age=31536000; includeSubDomains; preload",
            },
          ]
        : []),
      ...(process.env.NODE_ENV !== "production"
        ? [
            {
              key: "Content-Security-Policy",
              // Development only: HMR needs 'unsafe-eval'. In production the
              // nonce-based CSP is issued per request by middleware.ts.
              value: [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: blob: https:",
                "font-src 'self' data:",
                "connect-src 'self' ws://localhost:* wss:",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
              ].join("; "),
            },
          ]
        : []),
    ];

    return [
      {
        source: "/api/:path*",
        headers: [
          {
            key: "Access-Control-Allow-Origin",
            value: process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
          },
          { key: "Access-Control-Allow-Credentials", value: "true" },
          { key: "Access-Control-Allow-Methods", value: "GET,DELETE,PATCH,POST,PUT" },
          {
            key: "Access-Control-Allow-Headers",
            value:
              "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version",
          },
        ],
      },
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
};

// Sentry configuration (only applied when SENTRY_DSN is set)
const sentryConfig = {
  // For all available options, see:
  // https://github.com/getsentry/sentry-webpack-plugin#options
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,

  // Only print logs for uploading source maps in CI
  silent: process.env.NODE_ENV !== "production",

  // For all available options, see:
  // https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/
  widenClientFileUpload: true,

  // Automatically annotate React components to show their full name in breadcrumbs
  reactComponentAnnotation: {
    enabled: true,
  },

  // Route browser requests to Sentry through a Next.js rewrite to circumvent ad-blockers
  tunnelRoute: "/monitoring",

  // Hide source maps from generated client bundles
  hideSourceMaps: true,

  // Automatically tree-shake Sentry logger statements to reduce bundle size
  disableLogger: true,

  // Enables automatic instrumentation of Vercel Cron Monitors
  automaticVercelMonitors: true,
};

// Wrap with Sentry only if DSN is configured
const withSentry = (config) => {
  if (process.env.NEXT_PUBLIC_SENTRY_DSN || process.env.SENTRY_DSN) {
    return withSentryConfig(config, sentryConfig);
  }
  return config;
};

// Export with both plugins applied
module.exports = withSentry(withNextIntl(nextConfig));
