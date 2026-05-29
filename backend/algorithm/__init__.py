"""演算法模組 — 純函式，不依賴 web 框架或資料庫"""
from .packing import (
    run_packing_heuristic,
    PackingResult,
    to_packed_item_schema,
    to_unpacked_item_schema,
    # 子函式（給測試或進階呼叫使用）
    expand_cargo_items,
    sort_items_for_packing,
    is_overlap,
    check_stack_support,
    is_aisle_clear,
    place_items,
    compute_rectangle_union_area,
    COVERAGE_RATIO,
)

__all__ = [
    "run_packing_heuristic",
    "PackingResult",
    "to_packed_item_schema",
    "to_unpacked_item_schema",
    "expand_cargo_items",
    "sort_items_for_packing",
    "is_overlap",
    "check_stack_support",
    "is_aisle_clear",
    "place_items",
    "compute_rectangle_union_area",
    "COVERAGE_RATIO",
]
