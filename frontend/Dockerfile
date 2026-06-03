# ===== 前端多阶段构建：Vue 3 + Vite =====

# ---- 构建阶段 ----
FROM node:18-alpine AS builder

WORKDIR /app

# 复制依赖文件并安装
COPY package*.json ./
RUN npm install

# 复制源码并构建
COPY . .
RUN npm run build

# ---- 生产阶段 ----
FROM nginx:alpine

# 复制构建产物到 nginx 静态目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制自定义 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
