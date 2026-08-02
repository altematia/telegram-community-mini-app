FROM node:22-alpine AS build

WORKDIR /app
ENV NODE_OPTIONS=--max-old-space-size=256
RUN npm install --global pnpm@11.9.0 --no-audit --no-fund
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY index.html vite.config.js ./
COPY src ./src
RUN pnpm run build

FROM nginx:1.28-alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
USER nginx
EXPOSE 8080
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=5s \
  CMD wget -q --spider http://127.0.0.1:8080/health || exit 1
