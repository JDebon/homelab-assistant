# Stage 1: build
FROM node:20-alpine AS builder

WORKDIR /app

COPY apps/frontend/package.json ./
RUN npm install

COPY apps/frontend/ ./
RUN npm run build

# Stage 2: serve
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY apps/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
