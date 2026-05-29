# ============================================================
# Backend Dockerfile — Container Packing API
#
# 採用 Python 3.12 slim image（~50MB base），相對於完整版（~1GB）
# 已大幅縮小，且包含絕大多數 pure Python 套件需要的工具
#
# psycopg2-binary 是 wheel 套件，不需要編譯，slim image 也能裝
# 若未來改用 psycopg2（非 binary），則需要安裝 libpq-dev、gcc
# ============================================================

FROM python:3.12-slim

# ====== 環境變數設定 ======
# PYTHONDONTWRITEBYTECODE: 不產生 .pyc 檔（容器是不可變的，沒必要快取）
# PYTHONUNBUFFERED: stdout/stderr 不要 buffer，這樣 docker logs 能即時看到輸出
# PIP_NO_CACHE_DIR: 不快取 pip 下載的檔案，縮小 image 體積
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ====== 工作目錄 ======
WORKDIR /app

# ====== 安裝套件 ======
# 先複製 requirements.txt（單檔變動少），這層 cache 命中率高
# 之後改 .py 程式碼時，pip install 不會重跑
COPY requirements.txt .
RUN pip install -r requirements.txt

# ====== 複製程式碼 ======
# .dockerignore 已過濾掉 __pycache__、.venv、tests 等不需要的檔案
COPY . .

# ====== 對外開放的 port ======
# 此宣告純粹是文件用途，實際開放在 docker-compose.yml 控制
EXPOSE 9000

# ====== 啟動指令 ======
# 容器啟動時做兩件事：
#   1. python -m db.init_db    建表（重複跑沒問題，create_all 是冪等的）
#   2. uvicorn 啟動 API
#
# --host 0.0.0.0 是必須的：容器內服務必須監聽所有介面，
# 才能從容器外（其他容器、主機）連進來。本機開發的 127.0.0.1 在這裡會無效
CMD ["sh", "-c", "python -m db.init_db && uvicorn main:app --host 0.0.0.0 --port 9000"]
