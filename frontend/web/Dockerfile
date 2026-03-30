FROM node:20-alpine AS deps

WORKDIR /app/web

COPY frontend/web/package.json frontend/web/package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:20-alpine AS builder

WORKDIR /app/web

# Next.js inlined env for client-side fetches (via NEXT_PUBLIC_*).
ENV NEXT_PUBLIC_API_BASE=http://backend-api:7000/api/v1

COPY --from=deps /app/web/node_modules ./node_modules
COPY frontend/web ./

RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app/web

ENV NODE_ENV=production
ENV NEXT_PUBLIC_API_BASE=http://backend-api:7000/api/v1

COPY --from=builder /app/web ./

EXPOSE 7002

CMD ["npm", "run", "start", "--", "-p", "7002"]