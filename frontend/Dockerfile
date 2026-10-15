# Knowledge-transfer web UI (Next.js standalone server).
#
# The proxy target and every NEXT_PUBLIC_* value are fixed when the image is built:
#   docker build -t kt-ui \
#     --build-arg API_URL=http://api:8000 \
#     --build-arg NEXT_PUBLIC_VOICE_WS_URL=wss://api.example.com \
#     --build-arg HTTPS_ONLY=true \
#     frontend
#   docker run -p 3001:3001 kt-ui

FROM node:24-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:24-slim AS build
WORKDIR /app
ARG API_URL=http://api:8000
ARG NEXT_PUBLIC_VOICE_WS_URL=
ARG NEXT_PUBLIC_OPERATOR_NAME=
ARG NEXT_PUBLIC_CONTACT_EMAIL=
ARG NEXT_PUBLIC_POLICY_DATE=
ARG HTTPS_ONLY=false
ENV API_URL=$API_URL \
    NEXT_PUBLIC_VOICE_WS_URL=$NEXT_PUBLIC_VOICE_WS_URL \
    NEXT_PUBLIC_OPERATOR_NAME=$NEXT_PUBLIC_OPERATOR_NAME \
    NEXT_PUBLIC_CONTACT_EMAIL=$NEXT_PUBLIC_CONTACT_EMAIL \
    NEXT_PUBLIC_POLICY_DATE=$NEXT_PUBLIC_POLICY_DATE \
    HTTPS_ONLY=$HTTPS_ONLY \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:24-slim
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3001 \
    HOSTNAME=0.0.0.0
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3001
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3001/privacy').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"]
CMD ["node", "server.js"]
