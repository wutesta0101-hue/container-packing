"""資料庫連線設定

讀 .env 的 DATABASE_URL，建立 SQLAlchemy engine + session factory。
其他模組透過 get_db() 取得 session（會在請求結束自動關閉）。
"""
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# ============================================================
# 連線字串
# ============================================================
def get_database_url() -> str:
    """從環境變數取得 DATABASE_URL，沒設則用 docker-compose 預設值"""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://cpuser:cppassword@localhost:5432/container_packing",
    )


# ============================================================
# Engine 與 Session
# ============================================================
# echo=False：不要把每條 SQL 印到 log（開發時可改 True 排錯）
# pool_pre_ping=True：每次取連線前先 ping，避免拿到斷掉的連線
engine: Engine = create_engine(
    get_database_url(),
    echo=False,
    pool_pre_ping=True,
)

# autoflush=False：不要每次查詢都自動 flush（避免意外寫入）
# autocommit=False：明確控制 transaction
SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)


# ============================================================
# Base — 所有 ORM 模型都繼承自此
# ============================================================
class Base(DeclarativeBase):
    """SQLAlchemy 2.x 的新式宣告基底（取代舊版的 declarative_base()）"""
    pass


# ============================================================
# Session 取得
# ============================================================
def get_db() -> Generator[Session, None, None]:
    """FastAPI Depends 用法：
        @router.post("/pack")
        def pack(req: PackRequest, db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """非 FastAPI 場景使用（例如腳本、測試）：
        with db_session() as db:
            db.add(...)
            db.commit()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
