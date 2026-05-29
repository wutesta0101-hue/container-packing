"""應用設定 — 集中管理環境變數

對應 backend/.env：
    API_HOST, API_PORT, DEBUG, CORS_ORIGINS
"""
import os


def get_cors_origins() -> list[str]:
    """從 CORS_ORIGINS 讀允許的前端網址（逗號分隔）

    .env 範例：
        CORS_ORIGINS=http://localhost:5173,http://localhost:3000
    """
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


def is_debug() -> bool:
    return os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")


def get_api_host() -> str:
    return os.getenv("API_HOST", "127.0.0.1")


def get_api_port() -> int:
    return int(os.getenv("API_PORT", "9000"))
