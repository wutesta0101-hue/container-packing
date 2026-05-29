# ============================================================
# Frontend Dockerfile — Container Packing Web UI
#
# 採用 multi-stage build：
#   階段 1 (builder)：Node.js 20 環境 + npm install + npm run build
#   階段 2 (serve)：  Nginx alpine + 只複製 dist/ 進去
#
# 最終 image 大約 30MB（Nginx alpine 25MB + dist 約 1-3MB）
# 對比單階段 build（~1.2GB）小 40 倍
# ============================================================

# ============================================================
# 階段 1：建置（會被丟掉，不會出現在最終 image）
# ============================================================
FROM node:20-alpine AS builder

WORKDIR /app

# 先複製 package.json 與 lock file（單獨一層，layer cache 命中率高）
# 之後改 .jsx 程式碼時 npm install 不會重跑
COPY package*.json ./

# 用 npm ci 而不是 npm install
# ci = clean install，嚴格按 package-lock.json，更快、更穩定，正式環境的標準做法
RUN npm ci

# 複製其他原始碼
COPY . .

# 執行 Vite build → 產出 dist/ 資料夾
# 這個 dist 會在下個階段被搬到 Nginx 容器
RUN npm run build


# ============================================================
# 階段 2：Nginx 提供靜態檔（這才是最終 image）
# ============================================================
FROM nginx:1.27-alpine

# 把上一階段 build 出來的靜態檔複製到 Nginx 預設目錄
# /usr/share/nginx/html 是 Nginx 的 web root
COPY --from=builder /app/dist /usr/share/nginx/html

# 覆寫 Nginx 設定（預設只 serve 靜態檔，我們需要加上 /api 反向代理）
# 這個檔案是專案根目錄的 nginx.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Nginx 預設監聽 80
EXPOSE 80

# Nginx image 已經內建 CMD，不需要寫
# 預設指令：nginx -g "daemon off;"
