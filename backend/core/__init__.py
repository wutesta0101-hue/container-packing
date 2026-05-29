"""核心設定 — 環境變數、CORS"""
from .config import get_cors_origins, is_debug, get_api_host, get_api_port

__all__ = ["get_cors_origins", "is_debug", "get_api_host", "get_api_port"]
