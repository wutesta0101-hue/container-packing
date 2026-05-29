"""API 整合測試 — 用 FastAPI TestClient 模擬 HTTP 請求

跑法：cd backend && pytest tests/test_api.py -v

這比直接呼叫 service 多測了：
  - HTTP 請求/回應序列化
  - Pydantic 邊界驗證
  - 路由註冊
  - 錯誤代碼（400/404）
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import Base, get_db


# ============================================================
# 測試專用 app — 把 get_db 換成 in-memory SQLite
# ============================================================
@pytest.fixture
def client():
    """每個測試一個獨立的記憶體資料庫 + TestClient

    SQLite + FastAPI TestClient 跨 thread 設定：
      - check_same_thread=False：允許多執行緒共用連線
      - StaticPool：所有連線指向同一物件（避免每個 thread 開新的記憶體 DB）
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)

    # 覆寫 get_db dependency
    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    # 延後 import main 以避免它在 module load 時連 PostgreSQL
    from main import app
    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)

    # 清理
    app.dependency_overrides.clear()
    engine.dispose()


# ============================================================
# 健康檢查
# ============================================================
def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200


# ============================================================
# POST /api/v1/pack
# ============================================================
def test_pack_basic(client):
    """完整流程：送請求 → 拿結果"""
    response = client.post("/api/v1/pack", json={
        "cargo": [
            {"id": "A001", "type": "heavy",
             "L": 1200, "W": 1000, "H": 800,
             "weight": 800.0, "quantity": 4, "stackable": True},
            {"id": "V001", "type": "vip",
             "L": 1400, "W": 1100, "H": 1000,
             "weight": 600.0, "quantity": 2, "stackable": True},
        ],
        "container_type": "40",
        "forklift_type": "E35SH",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"].startswith("task_")
    assert len(data["packed"]) + len(data["unpacked"]) == 6  # 4+2
    assert "utilization" in data


def test_pack_validation_negative_dimension(client):
    """負數尺寸應該被 Pydantic 攔下，回 422"""
    response = client.post("/api/v1/pack", json={
        "cargo": [{"id": "X", "L": -100, "W": 100, "H": 100,
                   "weight": 1.0, "quantity": 1}],
        "container_type": "40",
        "forklift_type": "E35SH",
    })
    assert response.status_code == 422  # Unprocessable Entity


def test_pack_validation_invalid_container_type(client):
    """非法的 container_type 應該被攔下"""
    response = client.post("/api/v1/pack", json={
        "cargo": [{"id": "X", "L": 100, "W": 100, "H": 100,
                   "weight": 1.0, "quantity": 1}],
        "container_type": "BAD",
        "forklift_type": "E35SH",
    })
    assert response.status_code == 422


def test_pack_validation_empty_cargo(client):
    """空貨物清單應該被攔下（schema 規定 min_length=1）"""
    response = client.post("/api/v1/pack", json={
        "cargo": [],
        "container_type": "40",
        "forklift_type": "E35SH",
    })
    assert response.status_code == 422


def test_pack_validation_id_with_whitespace(client):
    """ID 含空白應被自訂 validator 攔下"""
    response = client.post("/api/v1/pack", json={
        "cargo": [{"id": "A 001", "L": 100, "W": 100, "H": 100,
                   "weight": 1.0, "quantity": 1}],
        "container_type": "40",
        "forklift_type": "E35SH",
    })
    assert response.status_code == 422


# ============================================================
# GET /api/v1/results/{task_id}
# ============================================================
def test_get_results_after_pack(client):
    """先 pack 拿到 task_id，再查得到完整結果"""
    pack_response = client.post("/api/v1/pack", json={
        "cargo": [{"id": "A", "L": 1000, "W": 1000, "H": 1000,
                   "weight": 100.0, "quantity": 1}],
        "container_type": "40",
        "forklift_type": "E35SH",
    })
    task_id = pack_response.json()["task_id"]

    get_response = client.get(f"/api/v1/results/{task_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["task_id"] == task_id
    assert "created_at" in data
    assert data["container_type"] == "40"
    assert data["forklift_type"] == "E35SH"


def test_get_results_not_found(client):
    """不存在的 task_id 回 404"""
    response = client.get("/api/v1/results/task_nonexistent")
    assert response.status_code == 404
    assert "找不到" in response.json()["detail"]


# ============================================================
# CORS 測試
# ============================================================
def test_cors_header_present(client):
    """OPTIONS preflight 應該有 CORS header"""
    response = client.options(
        "/api/v1/pack",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    # CORS middleware 應該回 access-control-allow-origin
    assert "access-control-allow-origin" in {
        k.lower() for k in response.headers.keys()
    }
