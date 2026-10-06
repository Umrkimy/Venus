# Venus web for server mode. Build from apps/web:
#   docker compose --profile server build web
FROM node:22-alpine AS build

WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Next.js writes the /api forward address into the build, so Core's
# address inside the compose network must be known here.
ARG CORE_URL=http://core:9000
ENV CORE_URL=$CORE_URL NEXT_OUTPUT=standalone
RUN npm run build

# Final image: only the standalone server, no node_modules or source.
FROM node:22-alpine

WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static

USER node
EXPOSE 3000

CMD ["node", "server.js"]
