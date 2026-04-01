FROM node:20-alpine AS deps
WORKDIR /app/web
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:20-alpine AS builder
WORKDIR /app/web
COPY --from=deps /app/web/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app/web
ENV NODE_ENV=production
ENV GATEWAY_BASE_URL=http://backend-api:7000

COPY --from=builder /app/web/public ./public
COPY --from=builder /app/web/.next/standalone ./
COPY --from=builder /app/web/.next/static ./.next/static

ENV PORT=7002
ENV HOSTNAME=0.0.0.0
ENV NEXT_TELEMETRY_DISABLED=1
EXPOSE 7002
CMD ["node", "server.js"]