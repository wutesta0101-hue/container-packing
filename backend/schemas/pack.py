"""裝箱 API 的請求 / 回應結構

對應前端 apiClient.js 的 packCargo() 與 getResults() 介面。
"""
from datetime import datetime
from pydantic import BaseModel, Field

from .cargo import CargoInput, PackedItem
from .container import ContainerType, ForkliftType


# ============================================================
# POST /api/v1/pack
# ============================================================
class PackRequest(BaseModel):
    """裝箱計算請求

    Example:
        {
          "cargo": [{"id": "A001", "type": "heavy", "L": 1200, ...}],
          "container_type": "40",
          "forklift_type": "E35SH"
        }
    """
    cargo: list[CargoInput] = Field(..., min_length=1, max_length=500)
    container_type: ContainerType
    forklift_type: ForkliftType


class PackResponse(BaseModel):
    """裝箱計算結果"""
    task_id: str
    packed: list[PackedItem]
    unpacked: list[PackedItem]
    utilization: float = Field(..., ge=0, le=100, description="空間利用率 (%)")


# ============================================================
# GET /api/v1/results/{task_id}
# ============================================================
class TaskResultResponse(BaseModel):
    """歷史任務查詢結果（多了時間戳與輸入摘要）"""
    task_id: str
    created_at: datetime
    container_type: ContainerType
    forklift_type: ForkliftType
    packed: list[PackedItem]
    unpacked: list[PackedItem]
    utilization: float
