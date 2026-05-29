"""ORM 模型 — 對應資料庫的 tasks 與 packed_items 兩張表

設計重點：
  - tasks 是「一次裝箱計算」的紀錄
  - packed_items 是該次計算的所有貨物明細（含未裝入的，用 is_packed 區分）
  - 一對多關聯（Task → PackedItem），刪除 Task 連同 items 一起刪除
"""
from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _new_task_id() -> str:
    """產生新的 task_id，格式：task_<uuid hex 前 12 碼>"""
    return f"task_{uuid4().hex[:12]}"


# ============================================================
# Task 表 — 一次裝箱計算紀錄
# ============================================================
class Task(Base):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=_new_task_id,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    container_type: Mapped[str] = mapped_column(String(10), nullable=False)
    forklift_type: Mapped[str] = mapped_column(String(10), nullable=False)

    # 統計欄位（避免每次查詢都要 join 計算）
    total_input: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_packed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    utilization: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # 關聯（一對多，刪除 Task 連動刪除 items）
    items: Mapped[list["PackedItem"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",   # 查 Task 時自動把 items 一起載入（避免 N+1）
    )

    def __repr__(self) -> str:
        return (
            f"<Task {self.task_id} {self.container_type}/{self.forklift_type} "
            f"packed={self.total_packed}/{self.total_input} util={self.utilization:.1f}%>"
        )


# ============================================================
# PackedItem 表 — 單件貨物明細
# ============================================================
class PackedItem(Base):
    __tablename__ = "packed_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("tasks.task_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 貨物基本資料
    item_id: Mapped[str] = mapped_column(String(50), nullable=False)         # 'A001-1'
    base_id: Mapped[str] = mapped_column(String(50), nullable=False)         # 'A001'
    type: Mapped[str] = mapped_column(String(20), nullable=False)            # 'heavy'
    length: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    is_stackable: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # 裝載資訊（未裝入時這三個為 None）
    x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    z: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_packed: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    rotated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 反向關聯
    task: Mapped["Task"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        pos = f"({self.x},{self.y},{self.z})" if self.is_packed else "(unpacked)"
        return f"<PackedItem {self.item_id} {pos}>"
