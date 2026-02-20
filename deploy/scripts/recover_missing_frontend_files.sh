#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
DOCKERFILE_PATH="$FRONTEND_DIR/Dockerfile"
NGINX_PATH="$FRONTEND_DIR/nginx.conf"

mkdir -p "$FRONTEND_DIR"

write_dockerfile() {
  cat > "$DOCKERFILE_PATH" <<'DOCKER'
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./
RUN if [ -f yarn.lock ]; then yarn install --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; \
    else npm install; fi

COPY . .

ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL}

RUN if [ -f yarn.lock ]; then yarn build; else npm run build; fi

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
DOCKER
}

write_nginx() {
  cat > "$NGINX_PATH" <<'NGINX'
server {
  listen 80;
  server_name _;

  root /usr/share/nginx/html;
  index index.html;

  location / {
    try_files $uri /index.html;
  }
}
NGINX
}

needs_dockerfile=false
needs_nginx=false

if [[ ! -s "$DOCKERFILE_PATH" ]]; then
  needs_dockerfile=true
fi

if [[ ! -s "$NGINX_PATH" ]]; then
  needs_nginx=true
fi

if [[ "$needs_dockerfile" == false && "$needs_nginx" == false ]]; then
  echo "No recovery needed: frontend/Dockerfile and frontend/nginx.conf already exist and are non-empty."
  exit 0
fi

[[ "$needs_dockerfile" == true ]] && write_dockerfile && echo "Recovered frontend/Dockerfile"
[[ "$needs_nginx" == true ]] && write_nginx && echo "Recovered frontend/nginx.conf"

echo "Done. You can now run:"
echo "  cd "$ROOT_DIR"/deploy"
echo "  docker compose --env-file .env.private -f docker-compose.private.yml up -d --build"
