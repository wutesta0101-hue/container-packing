"""資料庫 CRUD 操作 — Repository 層

把 SQLAlchemy 的 session 操作集中在這裡，service 層不需要知道 ORM 細節。

對外只暴露兩個主要動作：
  - save_task         — 把演算法結果存進資料庫
  - get_task_by_id    — 依 task_id 查詢結果（給 GET /api/v1/results/{id} 用）
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from algorithm.packing import PackingResult, _PlacedItem, _ExpandedItem
from .models import Task, PackedItem


# ============================================================
# 寫入：把裝箱結果存進資料庫
# ============================================================
def save_task(
    db: Session,
    *,
    container_type: str,
    forklift_type: str,
    result: PackingResult,
) -> Task:
    """把演算法結果寫入資料庫，回傳建立好的 Task ORM 物件"""
    total_input = len(result.packed) + len(result.unpacked)

    task = Task(
        container_type=container_type,
        forklift_type=forklift_type,
        total_input=total_input,
        total_packed=len(result.packed),
        utilization=result.utilization,
    )

    # 已裝入的
    for p in result.packed:
        task.items.append(_to_orm_packed(p))

    # 未裝入的
    for u in result.unpacked:
        task.items.append(_to_orm_unpacked(u))

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# ============================================================
# 查詢：依 ID 取得任務
# ============================================================
def get_task_by_id(db: Session, task_id: str) -> Task | None:
    """查詢任務（含所有 items，因為 model 設定了 lazy='selectin'）"""
    stmt = select(Task).where(Task.task_id == task_id)
    return db.scalars(stmt).first()


def list_recent_tasks(db: Session, limit: int = 20) -> list[Task]:
    """列出最近 N 筆任務（給未來歷史頁用，不含 items）"""
    stmt = select(Task).order_by(Task.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


# ============================================================
# 內部：演算法結構 → ORM 物件
# ============================================================
def _to_orm_packed(p: _PlacedItem) -> PackedItem:
    return PackedItem(
        item_id=p.id,
        base_id=p.base_id,
        type=p.type,
        length=p.L,
        width=p.W,
        height=p.H,
        weight=p.weight,
        is_stackable=p.stackable,
        x=p.x, y=p.y, z=p.z,
        is_packed=True,
        rotated=p.rotated,
    )


def _to_orm_unpacked(u: _ExpandedItem) -> PackedItem:
    return PackedItem(
        item_id=u.id,
        base_id=u.base_id,
        type=u.type,
        length=u.L,
        width=u.W,
        height=u.H,
        weight=u.weight,
        is_stackable=u.stackable,
        x=None, y=None, z=None,
        is_packed=False,
    )
