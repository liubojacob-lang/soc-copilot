FROM node:22-alpine AS deps

WORKDIR /app
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm npm install --legacy-peer-deps

FROM node:22-alpine AS builder

WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_URL=http://backend:8000
RUN --mount=type=cache,target=/app/.next/cache npm run build

# 把 standalone 摊平成运行镜像期望的布局。
#
# next.config.js 的 outputFileTracingRoot 指向 frontend/ 的上一级，容器内构建时即 /app，
# 于是 Next 以该根的 basename 建一层子目录，产物落在 /app/.next/standalone/app/ 而不是
# /app/.next/standalone/。顶层 server.js / node_modules 与内层 .next 必须合并到 /app：
# 原 Dockerfile 只拷 .next/standalone/ 根，产物整包被丢掉，运行时报
# "Could not find a production build in the './.next' directory"。
# 这里放在 builder 阶段做，结果直接落在 /app，runner 只需一次 COPY。
RUN set -e; \
    if [ -f /app/.next/standalone/server.js ]; then STANDALONE=/app/.next/standalone; \
    else STANDALONE="$(dirname "$(find /app/.next/standalone -maxdepth 3 -name server.js -print -quit)")"; fi; \
    if [ ! -f "$STANDALONE/server.js" ]; then \
        echo "standalone/server.js not found; 实际布局："; \
        find /app/.next/standalone -maxdepth 3 | head -30; \
        exit 1; \
    fi; \
    if [ "$STANDALONE" != "/app/.next/standalone" ]; then \
        for entry in "$STANDALONE"/* "$STANDALONE"/.[!.]*; do [ -e "$entry" ] && mv "$entry" /app/.next/standalone/; done; \
        rm -rf "$STANDALONE"; \
    fi; \
    cp -a /app/.next/standalone/. /app/; \
    cp -a /app/.next/standalone/.next/. /app/.next/; \
    rm -rf /app/.next/standalone; \
    test -f /app/.next/BUILD_ID; \
    test -f /app/server.js

FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs && \
    apk add --no-cache curl

COPY --from=builder /app/public ./public
COPY --from=builder /app/server.js ./server.js
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/.next ./.next
# .next/static 不在 standalone 产物内（standalone 只含运行时依赖与 manifests），
# 必须单独拷贝，否则页面能开但 CSS/JS 全 404。
COPY --from=builder /app/.next/static ./.next/static

RUN test -f /app/.next/BUILD_ID && \
    test -d /app/.next/static/css && \
    chown -R nextjs:nodejs /app/.next && \
    chown -R nextjs:nodejs /app/public

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f -L http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
