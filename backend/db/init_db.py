"""建表腳本 — 在現有資料庫上建立 ORM 定義的所有表

跑法：
    cd backend
    python -m db.init_db

開發階段直接用 create_all() 就好；正式環境之後再導入 Alembic 做版本控制。
"""
import sys
from pathlib import Path

# 讓 import 從 backend/ 起算
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import Base, engine, get_database_url
from db import models  # noqa: F401 — 觸發 ORM 模型註冊到 Base.metadata


def init_db():
    print(f"連線到：{get_database_url()}")
    print("\n建立表格中...")
    Base.metadata.create_all(bind=engine)

    # 列出建好的表
    table_names = sorted(Base.metadata.tables.keys())
    for name in table_names:
        print(f"  ✓ {name}")
    print(f"\n完成！共 {len(table_names)} 張表。\n")


if __name__ == "__main__":
    init_db()
