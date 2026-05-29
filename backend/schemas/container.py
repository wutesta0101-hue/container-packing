"""貨櫃與堆高機規格定義

對應前端 constants/index.js 的 CONTAINERS 與 FORKLIFTS。
未來如果要更動規格表，這裡是唯一來源（routes 接到請求後從這裡查）。
"""
from enum import Enum
from pydantic import BaseModel


# ============================================================
# 貨櫃
# ============================================================
class ContainerType(str, Enum):
    """合法的貨櫃類型 — Pydantic 會自動拒絕非清單內的值"""
    DRY_20 = "20"
    DRY_40 = "40"
    HQ_40 = "40HQ"


class ContainerSpec(BaseModel):
    """貨櫃內部尺寸與承重上限"""
    name: str
    L: int  # 長度 (mm)
    W: int  # 寬度 (mm)
    H: int  # 高度 (mm)
    max_weight: int  # 最大載重 (kg)


CONTAINERS: dict[ContainerType, ContainerSpec] = {
    ContainerType.DRY_20: ContainerSpec(name="20' Dry",  L=5898,  W=2352, H=2393, max_weight=28000),
    ContainerType.DRY_40: ContainerSpec(name="40' Dry",  L=12032, W=2352, H=2393, max_weight=26000),
    ContainerType.HQ_40:  ContainerSpec(name="40' HQ",   L=12032, W=2352, H=2698, max_weight=26000),
}


# ============================================================
# 堆高機（Linde E25/E30/E35 系列）
# ============================================================
class ForkliftType(str, Enum):
    E25 = "E25"
    E25S = "E25S"
    E25SH = "E25SH"
    E30S = "E30S"
    E30SH = "E30SH"
    E35SH = "E35SH"


class ForkliftSpec(BaseModel):
    name: str
    L: int           # 車身長 (mm)
    W: int           # 車身寬 (mm) — 通道寬度約束
    H: int           # 車身高 (mm) — 通道高度約束
    capacity: int    # 額定載重 (kg)
    fork_length: int # 牙叉長度 (mm) — 通道淨空判斷時的容忍距離（90% × 此值）


# 牙叉延伸的安全係數 — 業界經驗 0.9
FORK_REACH_RATIO = 0.9


FORKLIFTS: dict[ForkliftType, ForkliftSpec] = {
    ForkliftType.E25:    ForkliftSpec(name="Linde E25",    L=3427, W=1175, H=2200, capacity=2500, fork_length=1150),
    ForkliftType.E25S:   ForkliftSpec(name="Linde E25 S",  L=3427, W=1175, H=2200, capacity=2500, fork_length=1150),
    ForkliftType.E25SH:  ForkliftSpec(name="Linde E25 SH", L=3427, W=1228, H=2200, capacity=2500, fork_length=1150),
    ForkliftType.E30S:   ForkliftSpec(name="Linde E30 S",  L=3430, W=1228, H=2200, capacity=3000, fork_length=1150),
    ForkliftType.E30SH:  ForkliftSpec(name="Linde E30 SH", L=3430, W=1228, H=2200, capacity=3000, fork_length=1150),
    ForkliftType.E35SH:  ForkliftSpec(name="Linde E35 SH", L=3435, W=1325, H=2200, capacity=3500, fork_length=1150),
}
