"""FastAPI 應用入口

啟動方式（從 backend/ 目錄）：
    uvicorn main:app --reload --host 127.0.0.1 --port 9000

Swagger 文件：http://127.0.0.1:9000/docs
"""
from dotenv import load_dotenv

# 載入 .env（必須在其他 import 之前，因為 db.database 會讀環境變數）
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core import get_cors_origins, is_debug
from routes import pack_router


app = FastAPI(
    title="Container Packing API",
    version="0.1.0",
    description="3D 貨櫃裝箱系統後端",
    debug=is_debug(),
)


# ============================================================
# CORS — 允許前端跨域呼叫
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 路由註冊
# ============================================================
app.include_router(pack_router)


# ============================================================
# 健康檢查端點
# ============================================================
@app.get("/", tags=["health"])
def root():
    """根端點 — 確認服務可用"""
    return {"status": "ok", "service": "Container Packing API"}


@app.get("/health", tags=["health"])
def health():
    """健康檢查 — 用於部署監控"""
    return {"status": "ok"}
