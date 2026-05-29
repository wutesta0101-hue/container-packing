"""裝箱 API 路由

對應前端 apiClient.js：
  POST /api/v1/pack              → packCargo()
  GET  /api/v1/results/{task_id}  → getResults()
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from schemas import PackRequest, PackResponse, TaskResultResponse
from services import execute_packing, get_task_result


router = APIRouter(prefix="/api/v1", tags=["packing"])


# ============================================================
# POST /api/v1/pack
# ============================================================
@router.post(
    "/pack",
    response_model=PackResponse,
    status_code=status.HTTP_200_OK,
    summary="執行裝箱計算",
    description="""輸入貨物清單、貨櫃類型、堆高機型號，回傳裝箱結果。

    處理流程：
    1. Pydantic 驗證輸入（尺寸 > 0、類型在 enum 內等）
    2. 跑 Bottom-Left-Back 啟發式演算法
    3. 結果寫入資料庫（task_id 可用於後續查詢）
    4. 回傳給前端
    """,
)
def post_pack(
    req: PackRequest,
    db: Session = Depends(get_db),
) -> PackResponse:
    try:
        return execute_packing(req, db)
    except ValueError as e:
        # 演算法層可能丟出的錯誤（例如未知的 container_type）
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================
# GET /api/v1/results/{task_id}
# ============================================================
@router.get(
    "/results/{task_id}",
    response_model=TaskResultResponse,
    summary="查詢歷史裝箱結果",
    description="依 task_id 取得之前計算的裝箱結果（含建立時間、所有貨物明細）",
    responses={
        404: {"description": "task_id 不存在"},
    },
)
def get_results(
    task_id: str,
    db: Session = Depends(get_db),
) -> TaskResultResponse:
    result = get_task_result(task_id, db)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"找不到 task_id={task_id}",
        )
    return result
