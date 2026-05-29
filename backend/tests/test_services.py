"""Service 層測試 — 驗證 algorithm + db + schema 串接正常

跑法：cd backend && pytest tests/test_services.py -v
"""
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import Base
from services.packing_service import execute_packing, get_task_result
from schemas import (
    PackRequest, CargoInput, ContainerType, ForkliftType,
)


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture
def db_session():
    """記憶體 SQLite session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def sample_request() -> PackRequest:
    """標準範例請求"""
    return PackRequest(
        cargo=[
            CargoInput(id="A001", type="heavy",
                       L=1200, W=1000, H=800, weight=800.0,
                       quantity=4, stackable=True),
            CargoInput(id="V001", type="vip",
                       L=1400, W=1100, H=1000, weight=600.0,
                       quantity=2, stackable=True),
            CargoInput(id="B001", type="fragile",
                       L=1000, W=800, H=600, weight=150.0,
                       quantity=3, stackable=False),
        ],
        container_type=ContainerType.DRY_40,
        forklift_type=ForkliftType.E35SH,
    )


# ============================================================
# execute_packing
# ============================================================
def test_execute_packing_returns_response(db_session, sample_request):
    """主流程：執行 → 回傳含 task_id 與結果"""
    response = execute_packing(sample_request, db_session)

    assert response.task_id.startswith("task_")
    # 演算法已驗證 (test_algorithm)，這裡只確認介面對接
    assert len(response.packed) + len(response.unpacked) == 9  # 4+2+3
    assert 0 <= response.utilization <= 100


def test_execute_packing_persisted(db_session, sample_request):
    """執行完應該寫進資料庫，能查得到"""
    response = execute_packing(sample_request, db_session)

    # 用 get_task_result 查詢同一 task_id
    fetched = get_task_result(response.task_id, db_session)
    assert fetched is not None
    assert fetched.task_id == response.task_id
    assert len(fetched.packed) == len(response.packed)


def test_execute_packing_packed_items_have_coords(db_session, sample_request):
    """已裝入的 items 必須有完整 x/y/z 坐標"""
    response = execute_packing(sample_request, db_session)
    for item in response.packed:
        assert item.is_packed is True
        assert item.x is not None
        assert item.y is not None
        assert item.z is not None
        assert item.x >= 0
        assert item.y >= 0
        assert item.z >= 0


def test_execute_packing_unpacked_have_no_coords(db_session):
    """未裝入的 items 坐標應為 None"""
    # 建立一個放不下的請求（單件超過貨櫃）
    req = PackRequest(
        cargo=[CargoInput(id="HUGE", L=9999, W=2000, H=2000,
                          weight=100.0, quantity=1)],
        container_type=ContainerType.DRY_20,  # 20 呎放不下
        forklift_type=ForkliftType.E35SH,
    )
    response = execute_packing(req, db_session)
    assert len(response.unpacked) == 1
    assert response.unpacked[0].x is None
    assert response.unpacked[0].y is None
    assert response.unpacked[0].z is None
    assert response.unpacked[0].is_packed is False


# ============================================================
# get_task_result
# ============================================================
def test_get_task_result_not_found(db_session):
    """不存在的 task_id 回傳 None"""
    assert get_task_result("task_nonexistent", db_session) is None


def test_get_task_result_includes_metadata(db_session, sample_request):
    """查詢結果含建立時間、貨櫃/堆高機類型"""
    response = execute_packing(sample_request, db_session)
    fetched = get_task_result(response.task_id, db_session)

    assert fetched.container_type == ContainerType.DRY_40
    assert fetched.forklift_type == ForkliftType.E35SH
    assert fetched.created_at is not None
    assert abs(fetched.utilization - response.utilization) < 0.01


def test_round_trip_consistency(db_session, sample_request):
    """寫入 + 讀取後，所有貨物資料應與原始一致"""
    response = execute_packing(sample_request, db_session)
    fetched = get_task_result(response.task_id, db_session)

    # 已裝入物應該完全一致
    assert len(fetched.packed) == len(response.packed)
    for original, restored in zip(response.packed, fetched.packed):
        assert original.id == restored.id
        assert original.x == restored.x
        assert original.y == restored.y
        assert original.z == restored.z
        assert original.weight == restored.weight
