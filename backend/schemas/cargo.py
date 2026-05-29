"""貨物資料模型

CargoInput   — 從前端送來的單筆貨物批次（含 quantity）
PackedItem   — 演算法輸出的單件貨物（含 x/y/z 坐標）
"""
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class CargoType(str, Enum):
    """貨物類型 — 影響顏色顯示與排序優先級"""
    NORMAL = "normal"
    HEAVY = "heavy"
    FRAGILE = "fragile"
    VIP = "vip"


# ============================================================
# 輸入
# ============================================================
class CargoInput(BaseModel):
    """前端送來的一筆貨物批次（一個 id 可有多件 = quantity）"""
    id: str = Field(..., min_length=1, max_length=50, description="貨物批次 ID")
    type: CargoType = CargoType.NORMAL
    L: int = Field(..., gt=0, le=20000, description="長 (mm)")
    W: int = Field(..., gt=0, le=20000, description="寬 (mm)")
    H: int = Field(..., gt=0, le=20000, description="高 (mm)")
    weight: float = Field(..., gt=0, le=50000, description="單件重量 (kg)")
    quantity: int = Field(..., gt=0, le=10000, description="件數")
    stackable: bool = Field(True, description="是否可堆疊（其上能否再放東西）")
    rotatable: bool = Field(True, description="是否可旋轉（規則 2：在地面上轉 90°，長寬互換）")

    @field_validator("id")
    @classmethod
    def id_no_whitespace(cls, v: str) -> str:
        """貨物 ID 內不應有空白（避免後續用 'A001-1' 格式時混淆）"""
        if " " in v or "\t" in v:
            raise ValueError("貨物 ID 不可包含空白字元")
        return v


# ============================================================
# 輸出（演算法計算後的單件結果）
# ============================================================
class PackedItem(BaseModel):
    """演算法處理後的單件貨物（quantity 已展開為個別實例）

    座標系統說明：
      原點 (0, 0, 0) = 貨櫃內部最深處的左下角
      x = 長度方向 (沿貨櫃長軸，0 = 最深處，最大值 = 出口)
      y = 寬度方向
      z = 高度方向 (0 = 地板)
    """
    id: str = Field(..., description="展開後唯一 ID，例如 'A001-3'")
    base_id: str = Field(..., description="原批次 ID，例如 'A001'")
    type: CargoType
    L: int
    W: int
    H: int
    weight: float
    stackable: bool

    # 裝載坐標（is_packed=False 時這三個欄位為 None）
    x: int | None = None
    y: int | None = None
    z: int | None = None

    is_packed: bool = Field(True, description="True = 成功裝入；False = 未裝入")
    rotated: bool = Field(False, description="是否旋轉擺放（規則 2，長寬與原始輸入互換）")
