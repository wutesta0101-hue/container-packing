"""Repository 層測試（用 in-memory SQLite 不依賴 Docker）

跑法：
    cd backend
    pytest tests/test_repository.py -v

注意：實際 PostgreSQL 連線測試在 test_db_connection.py 另外做。
"""
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import Base
from db import repository
from algorithm.packing import (
    PackingResult, _PlacedItem, _ExpandedItem,
    run_packing_heuristic,
)
from schemas import CargoInput


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture
def db_session():
    """每個測試一個獨立的 in-memory SQLite session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def sample_result() -> PackingResult:
    """跑一次標準範例的演算法結果"""
    cargo = [
        CargoInput(id="A001", type="heavy",
                   L=1200, W=1000, H=800, weight=800.0,
                   quantity=4, stackable=True),
        CargoInput(id="V001", type="vip",
                   L=1400, W=1100, H=1000, weight=600.0,
                   quantity=2, stackable=True),
    ]
    return run_packing_heuristic(cargo, "40", "E35SH")


# ============================================================
# 寫入測試
# ============================================================
def test_save_task_basic(db_session, sample_result):
    """save_task 能建立 Task 與所有 PackedItem 紀錄"""
    task = repository.save_task(
        db_session,
        container_type="40",
        forklift_type="E35SH",
        result=sample_result,
    )

    # Task 基本欄位
    assert task.task_id.startswith("task_")
    assert task.container_type == "40"
    assert task.forklift_type == "E35SH"
    assert task.total_input == len(sample_result.packed) + len(sample_result.unpacked)
    assert task.total_packed == len(sample_result.packed)

    # items 數量正確
    assert len(task.items) == task.total_input


def test_save_task_packed_items_have_coords(db_session, sample_result):
    """已裝入的 items 必須有 x/y/z；未裝入的必須是 None"""
    task = repository.save_task(
        db_session, container_type="40", forklift_type="E35SH",
        result=sample_result,
    )

    for item in task.items:
        if item.is_packed:
            assert item.x is not None
            assert item.y is not None
            assert item.z is not None
        else:
            assert item.x is None
            assert item.y is None
            assert item.z is None


def test_save_task_persisted_to_db(db_session, sample_result):
    """寫入後可以從 DB 重新讀取"""
    task = repository.save_task(
        db_session, container_type="40", forklift_type="E35SH",
        result=sample_result,
    )
    saved_id = task.task_id

    # 強制清除 session cache，確保是從 DB 讀取
    db_session.expunge_all()

    fetched = repository.get_task_by_id(db_session, saved_id)
    assert fetched is not None
    assert fetched.task_id == saved_id
    assert len(fetched.items) == task.total_input


# ============================================================
# 查詢測試
# ============================================================
def test_get_task_by_id_not_found(db_session):
    """查詢不存在的 task_id 應回傳 None"""
    result = repository.get_task_by_id(db_session, "task_nonexistent")
    assert result is None


def test_list_recent_tasks(db_session, sample_result):
    """list_recent_tasks 應依時間倒序回傳"""
    # 建立 3 筆
    ids = []
    for i in range(3):
        task = repository.save_task(
            db_session, container_type="40", forklift_type="E35SH",
            result=sample_result,
        )
        ids.append(task.task_id)

    recent = repository.list_recent_tasks(db_session, limit=10)
    assert len(recent) == 3
    # 最新的（最後建的）應該排第一
    assert recent[0].task_id == ids[-1]


def test_list_recent_tasks_limit(db_session, sample_result):
    """limit 應正確限制回傳數量"""
    for _ in range(5):
        repository.save_task(
            db_session, container_type="40", forklift_type="E35SH",
            result=sample_result,
        )
    recent = repository.list_recent_tasks(db_session, limit=2)
    assert len(recent) == 2


# ============================================================
# 級聯刪除測試
# ============================================================
def test_cascade_delete(db_session, sample_result):
    """刪除 Task 時，關聯的 items 也應一起刪除"""
    from db.models import PackedItem, Task

    task = repository.save_task(
        db_session, container_type="40", forklift_type="E35SH",
        result=sample_result,
    )
    item_count = len(task.items)
    assert item_count > 0

    # 刪除 task
    db_session.delete(task)
    db_session.commit()

    # items 應該也被刪除
    remaining_items = db_session.query(PackedItem).all()
    assert len(remaining_items) == 0

    remaining_tasks = db_session.query(Task).all()
    assert len(remaining_tasks) == 0


# ============================================================
# 邊界案例
# ============================================================
def test_save_empty_result(db_session):
    """空結果（packed 與 unpacked 都空）也能寫入"""
    empty_result = PackingResult(packed=[], unpacked=[], utilization=0.0)
    task = repository.save_task(
        db_session, container_type="20", forklift_type="E25",
        result=empty_result,
    )
    assert task.total_input == 0
    assert task.total_packed == 0
    assert len(task.items) == 0
