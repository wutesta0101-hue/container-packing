"""真實 PostgreSQL 連線檢查（不是 pytest，是腳本）

用途：
  1. 驗證 .env 的 DATABASE_URL 設定正確
  2. 驗證 docker-compose 的 PostgreSQL 已啟動
  3. 驗證資料表已建立（請先跑 python -m db.init_db）

跑法：
    cd backend
    python verify_db.py

⚠ 檔名故意不以 test_ 開頭，避免 PyCharm 用 pytest 模式執行造成 Empty suite。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import inspect, text
from db.database import engine, get_database_url, db_session
from db import repository
from algorithm.packing import run_packing_heuristic
from schemas import CargoInput


def check_connection():
    print("=" * 50)
    print(f"DATABASE_URL: {get_database_url()}")
    print("=" * 50)

    # 1. 連線測試
    print("\n[1/4] 嘗試連線...")
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar()
        print(f"  ✓ 連線成功")
        print(f"  PostgreSQL: {version[:60]}...")

    # 2. 列出資料表
    print("\n[2/4] 檢查資料表...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if not tables:
        print("  ✗ 資料庫沒有表格，請先跑：python -m db.init_db")
        return False
    for t in tables:
        cols = inspector.get_columns(t)
        print(f"  ✓ {t}（{len(cols)} 欄位）")

    # 3. 寫入測試（建立一筆假任務）
    print("\n[3/4] 寫入測試...")
    cargo = [
        CargoInput(id="TEST", L=1000, W=1000, H=1000, weight=100.0, quantity=2),
    ]
    result = run_packing_heuristic(cargo, "40", "E35SH")
    with db_session() as db:
        task = repository.save_task(
            db,
            container_type="40",
            forklift_type="E35SH",
            result=result,
        )
        test_id = task.task_id
    print(f"  ✓ 已寫入 task_id={test_id}")

    # 4. 讀取測試
    print("\n[4/4] 讀取測試...")
    with db_session() as db:
        fetched = repository.get_task_by_id(db, test_id)
        assert fetched is not None
        print(f"  ✓ 已讀取，包含 {len(fetched.items)} 件 items")

        # 清掉測試資料
        db.delete(fetched)
        db.commit()
        print(f"  ✓ 已清除測試資料")

    print("\n" + "=" * 50)
    print("全部通過 — 資料庫設定正確 ✓")
    print("=" * 50 + "\n")
    return True


if __name__ == "__main__":
    try:
        check_connection()
    except Exception as e:
        print(f"\n✗ 失敗：{type(e).__name__}: {e}\n")
        print("可能原因：")
        print("  - PostgreSQL 沒啟動（docker compose ps 確認）")
        print("  - .env 的 DATABASE_URL 設定錯誤")
        print("  - 表格還沒建立（先跑：python -m db.init_db）")
        sys.exit(1)
