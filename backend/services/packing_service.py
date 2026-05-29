"""業務邏輯層 — 串接演算法 + 資料庫

職責：
  1. 接收經過 Pydantic 驗證的請求物件
  2. 呼叫演算法計算
  3. 把結果寫入資料庫
  4. 把資料庫物件轉成 API 回應格式

不做的事：
  - HTTP 處理（那是 routes 的事）
  - 演算法細節（那是 algorithm 的事）
  - SQL 細節（那是 repository 的事）
"""
from sqlalchemy.orm import Session

from algorithm.packing import (
    run_packing_heuristic,
    to_packed_item_schema,
    to_unpacked_item_schema,
)
from db import repository
from db.models import Task as TaskOrm
from schemas import (
    PackRequest, PackResponse, TaskResultResponse,
    PackedItem, ContainerType, ForkliftType,
)


# ============================================================
# POST /pack 的業務邏輯
# ============================================================
def execute_packing(req: PackRequest, db: Session) -> PackResponse:
    """執行裝箱計算並持久化

    Args:
        req: 經 Pydantic 驗證的請求
        db: 資料庫 session

    Returns:
        PackResponse — 含 task_id、裝箱結果、利用率
    """
    # 1. 跑演算法
    result = run_packing_heuristic(
        cargo=req.cargo,
        container_type=req.container_type,
        forklift_type=req.forklift_type,
    )

    # 2. 寫入資料庫
    task = repository.save_task(
        db,
        container_type=req.container_type.value,
        forklift_type=req.forklift_type.value,
        result=result,
    )

    # 3. 轉成 API 回應格式
    return PackResponse(
        task_id=task.task_id,
        packed=[to_packed_item_schema(p) for p in result.packed],
        unpacked=[to_unpacked_item_schema(u) for u in result.unpacked],
        utilization=result.utilization,
    )


# ============================================================
# GET /results/{task_id} 的業務邏輯
# ============================================================
def get_task_result(task_id: str, db: Session) -> TaskResultResponse | None:
    """查詢歷史任務

    Returns:
        TaskResultResponse 或 None（找不到時）
    """
    task = repository.get_task_by_id(db, task_id)
    if task is None:
        return None

    return _orm_to_task_response(task)


# ============================================================
# 內部：ORM → Pydantic 轉換
# ============================================================
def _orm_to_task_response(task: TaskOrm) -> TaskResultResponse:
    """把資料庫的 Task ORM 物件轉成 API 回應"""
    packed: list[PackedItem] = []
    unpacked: list[PackedItem] = []

    for orm_item in task.items:
        item = PackedItem(
            id=orm_item.item_id,
            base_id=orm_item.base_id,
            type=orm_item.type,
            L=orm_item.length,
            W=orm_item.width,
            H=orm_item.height,
            weight=orm_item.weight,
            stackable=orm_item.is_stackable,
            x=orm_item.x,
            y=orm_item.y,
            z=orm_item.z,
            is_packed=orm_item.is_packed,
            rotated=orm_item.rotated,
        )
        if orm_item.is_packed:
            packed.append(item)
        else:
            unpacked.append(item)

    return TaskResultResponse(
        task_id=task.task_id,
        created_at=task.created_at,
        container_type=ContainerType(task.container_type),
        forklift_type=ForkliftType(task.forklift_type),
        packed=packed,
        unpacked=unpacked,
        utilization=task.utilization,
    )
