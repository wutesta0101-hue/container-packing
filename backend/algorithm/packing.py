"""3D 貨櫃裝箱演算法 — Bottom-Left-Back 啟發式

此檔案是 frontend/src/algorithm/packingHeuristic.js 的 Python 對應版本。
兩邊邏輯應保持一致：相同輸入應產生相同輸出（含順序）。

演算法核心：
  1. 展開 quantity 成單件清單
  2. 排序：VIP 優先 → 體積大優先 → 重量大優先
  3. 對每件貨物，從候選錨點 (anchors) 中找符合所有物理約束的最內側位置
  4. 物理約束：不重疊、堆疊支撐、密度上小下大、堆高機通道淨空

座標系統（與貨櫃對齊）：
  - x 軸 = 長度方向（深處 → 出口），單位 mm
  - y 軸 = 寬度方向（左 → 右），單位 mm
  - z 軸 = 高度方向（地板 → 天花板），單位 mm
  - 原點 (0, 0, 0) = 貨櫃內部最深處的左下角
  - 出口位於 x = container.L 那一端
"""
from dataclasses import dataclass, field
from typing import Iterable

from schemas import (
    CargoInput, PackedItem,
    ContainerSpec, ForkliftSpec,
    CONTAINERS, FORKLIFTS, FORK_REACH_RATIO,
    ContainerType, ForkliftType,
)


# ============================================================
# 內部資料結構（演算法迴圈用，不外露）
# ============================================================
@dataclass
class _ExpandedItem:
    """展開後的單件貨物，多了 density 欄位（內部使用）"""
    id: str
    base_id: str
    type: str
    L: int
    W: int
    H: int
    weight: float
    density: float       # kg/m³，用於密度比較
    stackable: bool
    rotatable: bool = True   # 規則 2：可旋轉（長寬互換），預設 True


@dataclass
class _PlacedItem:
    """已放置的單件貨物，多了 x/y/z"""
    id: str
    base_id: str
    type: str
    L: int               # 最終擺放尺寸（rotated 時 L 與原始 W 相同）
    W: int
    H: int
    weight: float
    density: float
    stackable: bool
    x: int
    y: int
    z: int
    rotated: bool = False  # 旋轉狀態（讓 UI 顯示「已旋轉」標記）


@dataclass
class _Anchor:
    """候選錨點"""
    x: int
    y: int
    z: int


# ============================================================
# 子函式：把 quantity 展開成單件清單
# ============================================================
def expand_cargo_items(cargo_list: Iterable[CargoInput]) -> list[_ExpandedItem]:
    items: list[_ExpandedItem] = []
    for c in cargo_list:
        for i in range(c.quantity):
            volume_m3 = c.L * c.W * c.H / 1e9
            items.append(_ExpandedItem(
                id=f"{c.id}-{i + 1}",      # 例如 'A001-1', 'A001-2'
                base_id=c.id,
                type=c.type.value if hasattr(c.type, "value") else c.type,
                L=c.L, W=c.W, H=c.H,
                weight=c.weight,
                density=c.weight / volume_m3,
                stackable=c.stackable,
                rotatable=getattr(c, "rotatable", True),
            ))
    return items


# ============================================================
# 子函式：排序策略
# 與 JS 版一致：VIP > 體積大 > 重量大
# ============================================================
def sort_items_for_packing(items: list[_ExpandedItem]) -> list[_ExpandedItem]:
    """回傳新的排序後清單（不改原列表）

    多重鍵排序在 Python 用 key 函式：tuple 比較會依序比對每個元素。
    為了得到「降冪」效果，數值欄位取負號。
    """
    def sort_key(item: _ExpandedItem):
        # 1. VIP 優先（is_vip = True 排前面 → 用 not 反轉，False < True）
        is_not_vip = item.type != "vip"
        # 2. 體積大者優先（取負）
        volume = item.L * item.W * item.H
        # 3. 重量大者優先（取負）
        return (is_not_vip, -volume, -item.weight)

    return sorted(items, key=sort_key)


# ============================================================
# 子函式：兩個 AABB 是否相交（不重疊檢測）
# ============================================================
def is_overlap(
    ax: int, ay: int, az: int,
    aL: int, aW: int, aH: int,
    p: _PlacedItem,
) -> bool:
    """候選位置 (ax, ay, az, aL, aW, aH) 是否與已放置物 p 相交"""
    return not (
        ax + aL <= p.x or p.x + p.L <= ax or
        ay + aW <= p.y or p.y + p.W <= ay or
        az + aH <= p.z or p.z + p.H <= az
    )


# ============================================================
# 子函式：堆疊支撐檢查（含懸空判斷）
#
# 若 z > 0，必須滿足以下條件：
#   1. 至少一個支撐物（頂面接觸 + 水平投影重疊）
#   2. 所有支撐物 stackable = True
#   3. 上方密度 ≤ 下方密度（重物在下，5% 容差）
#   4. ★ 支撐覆蓋率 ≥ 90%（懸空 + 縫隙合計不超過 10%）
# ============================================================
COVERAGE_RATIO = 0.9  # 90% 覆蓋率門檻（懸空 ≤ 10%）


def check_stack_support(
    ax: int, ay: int, az: int,
    aL: int, aW: int,
    item: _ExpandedItem,
    placed: list[_PlacedItem],
) -> bool:
    if az == 0:
        return True  # 直接放地板，免檢查

    # 找所有「頂面剛好等於 az」且「水平投影有重疊」的物件
    supports = [
        p for p in placed
        if abs(p.z + p.H - az) < 1
        and not (
            ax + aL <= p.x or p.x + p.L <= ax or
            ay + aW <= p.y or p.y + p.W <= ay
        )
    ]

    if not supports:
        return False  # 浮空
    if any(not s.stackable for s in supports):
        return False  # 支撐物標記不可堆疊
    if any(item.density > s.density * 1.05 for s in supports):
        return False  # 密度條件（重物在下）

    # ★ 覆蓋率檢查：所有支撐物與貨物底面相交矩形的聯集面積
    intersections = []
    for s in supports:
        x0 = max(ax, s.x)
        y0 = max(ay, s.y)
        x1 = min(ax + aL, s.x + s.L)
        y1 = min(ay + aW, s.y + s.W)
        if x0 < x1 and y0 < y1:
            intersections.append((x0, y0, x1, y1))
    union_area = compute_rectangle_union_area(intersections)
    item_area = aL * aW
    if union_area / item_area < COVERAGE_RATIO:
        return False

    return True


# ============================================================
# 掃描線演算法：計算多個矩形的聯集面積
#
# 演算法：
#   1. 收集所有矩形的 X 邊界，去重後排序
#   2. 對每對相鄰 X，找出在此切片內覆蓋的矩形
#   3. 把覆蓋的矩形投影到 Y 軸算線段聯集長度
#   4. 切片面積 = (x1 - x0) × Y 覆蓋長度
#
# 複雜度 O(N²)，對 N < 10 的場景非常快
# ============================================================
def compute_rectangle_union_area(rects: list[tuple[int, int, int, int]]) -> float:
    """rects 是 (x0, y0, x1, y1) 元組列表。回傳聯集面積。"""
    if not rects:
        return 0.0

    # 收集並排序所有 X 邊界
    xs = set()
    for r in rects:
        xs.add(r[0])
        xs.add(r[2])
    sorted_xs = sorted(xs)

    total_area = 0.0
    for i in range(len(sorted_xs) - 1):
        x0 = sorted_xs[i]
        x1 = sorted_xs[i + 1]
        if x0 == x1:
            continue

        # 收集在此 X 切片內覆蓋的矩形（投影到 Y 軸）
        y_intervals = []
        for r in rects:
            if r[0] <= x0 and r[2] >= x1:
                y_intervals.append((r[1], r[3]))
        if not y_intervals:
            continue

        # 算 Y 軸線段聯集長度
        y_intervals.sort()
        y_cover = 0
        cur_start, cur_end = y_intervals[0]
        for s, e in y_intervals[1:]:
            if s > cur_end:
                y_cover += cur_end - cur_start
                cur_start, cur_end = s, e
            else:
                cur_end = max(cur_end, e)
        y_cover += cur_end - cur_start

        total_area += (x1 - x0) * y_cover
    return total_area


# ============================================================
# 子函式：堆高機通道淨空檢查（含牙叉延伸）
#
# 假設貨櫃出口在 x = container.L 端
# 放置貨物 (ax, ay, az, L, W, H) 後，從這件貨物正前方到出口
# 的「通道空間」內必須沒有已放置的貨物（在堆高機高度內）
#
# ★ 牙叉延伸：堆高機的牙叉可以「伸進」貨物正前方一段距離壓著
#   前面的貨物作業。所以「正前方 + 90% 牙叉長度」之內可以有東西。
#
# 通道 X 範圍：(ax + L + reach, container.L)  ← 加上 reach
# 通道 Y 範圍：以放置物 Y 中線為中心，寬 max(item.W, forklift.W)
# 通道 Z 範圍：(0, forklift.H) 即堆高機車身高度內
# ============================================================
def is_aisle_clear(
    ax: int, ay: int, az: int,
    aL: int, aW: int, aH: int,
    placed: list[_PlacedItem],
    container: ContainerSpec,
    forklift: ForkliftSpec,
) -> bool:
    aisle_w = max(aW, forklift.W)
    y_center = ay + aW / 2
    aisle_y0 = max(0, y_center - aisle_w / 2)
    aisle_y1 = min(container.W, y_center + aisle_w / 2)

    # 牙叉容忍範圍 — 貨物正前方 fork_reach 距離內可以有箱子
    fork_reach = forklift.fork_length * FORK_REACH_RATIO

    for p in placed:
        # p 必須在「貨物正前方 + 牙叉容忍距離」之外，才算擋路
        if p.x >= ax + aL + fork_reach:
            # y 與通道重疊？
            y_overlap = max(p.y, aisle_y0) < min(p.y + p.W, aisle_y1)
            # z 在堆高機車身高度範圍內？
            z_overlap = p.z < forklift.H
            if y_overlap and z_overlap:
                return False  # 通道被擋
    return True


# ============================================================
# 主函式：執行裝箱
# ============================================================
def place_items(
    sorted_items: list[_ExpandedItem],
    container: ContainerSpec,
    forklift: ForkliftSpec,
) -> tuple[list[_PlacedItem], list[_ExpandedItem]]:
    """執行 BLB 裝箱

    Returns:
        (placed, unplaced) — 已放置物（含坐標）與未放置物（保留原資料）
    """
    placed: list[_PlacedItem] = []
    unplaced: list[_ExpandedItem] = []

    # 候選錨點：每放一個箱子就會新增 3 個（往 x、y、z 三個方向）
    anchors: list[_Anchor] = [_Anchor(x=0, y=0, z=0)]

    for item in sorted_items:
        best_pos: _Anchor | None = None
        best_rotated: bool = False

        # 排序候選錨點：x 小（內側）→ z 小（底部）→ y 小（後）
        # 體現「由內到外、由下到上」策略
        anchors.sort(key=lambda a: (a.x, a.z, a.y))

        # 旋轉候選 — 規則 2：可旋轉 = 長寬互換（高度永遠不變）
        # 不可旋轉的物件只試原方向；正方形物件兩種旋轉等效，也只試一次
        rotations = [False, True] if (item.rotatable and item.L != item.W) else [False]

        # Python 沒有 labelled break，用 flag 跳出雙層迴圈
        found = False
        for a in anchors:
            for rotated in rotations:
                cur_L = item.W if rotated else item.L
                cur_W = item.L if rotated else item.W
                cur_H = item.H

                # 1. 邊界檢查
                if (a.x + cur_L > container.L or
                    a.y + cur_W > container.W or
                    a.z + cur_H > container.H):
                    continue

                # 2. 不重疊檢查
                if any(is_overlap(a.x, a.y, a.z, cur_L, cur_W, cur_H, p)
                       for p in placed):
                    continue

                # 3. 堆疊支撐檢查
                if not check_stack_support(a.x, a.y, a.z, cur_L, cur_W,
                                           item, placed):
                    continue

                # 4. 堆高機通道淨空檢查
                if not is_aisle_clear(a.x, a.y, a.z, cur_L, cur_W, cur_H,
                                      placed, container, forklift):
                    continue

                best_pos = a
                best_rotated = rotated
                found = True
                break
            if found:
                break

        if best_pos is not None:
            # 把 L/W 換成最終擺放尺寸（rotated 時長寬互換）
            final_L = item.W if best_rotated else item.L
            final_W = item.L if best_rotated else item.W
            placed_item = _PlacedItem(
                id=item.id, base_id=item.base_id, type=item.type,
                L=final_L, W=final_W, H=item.H,
                weight=item.weight, density=item.density,
                stackable=item.stackable,
                x=best_pos.x, y=best_pos.y, z=best_pos.z,
                rotated=best_rotated,
            )
            placed.append(placed_item)

            # 新增 3 個候選錨點（用最終尺寸算）
            anchors.append(_Anchor(x=placed_item.x + placed_item.L,
                                   y=placed_item.y, z=placed_item.z))
            anchors.append(_Anchor(x=placed_item.x,
                                   y=placed_item.y + placed_item.W,
                                   z=placed_item.z))
            anchors.append(_Anchor(x=placed_item.x, y=placed_item.y,
                                   z=placed_item.z + placed_item.H))

            # 移除被佔用的錨點
            anchors = [an for an in anchors
                       if not (an.x == best_pos.x
                               and an.y == best_pos.y
                               and an.z == best_pos.z)]
        else:
            unplaced.append(item)

    return placed, unplaced


# ============================================================
# 主入口：run_packing_heuristic
#
# 公開介面，輸入輸出對齊前端 packingHeuristic.js / API schema
# ============================================================
@dataclass
class PackingResult:
    """演算法輸出（service 層會把它轉成 PackedItem schema）"""
    packed: list[_PlacedItem]
    unpacked: list[_ExpandedItem]
    utilization: float   # 0–100 (%)


def run_packing_heuristic(
    cargo: list[CargoInput],
    container_type: ContainerType | str,
    forklift_type: ForkliftType | str,
) -> PackingResult:
    """主入口

    Args:
        cargo: CargoInput 物件清單（含 quantity）
        container_type: ContainerType enum 或對應字串
        forklift_type: ForkliftType enum 或對應字串

    Returns:
        PackingResult 含 packed, unpacked, utilization
    """
    # 容許字串輸入（方便測試與直接呼叫）
    if isinstance(container_type, str):
        container_type = ContainerType(container_type)
    if isinstance(forklift_type, str):
        forklift_type = ForkliftType(forklift_type)

    container = CONTAINERS[container_type]
    forklift = FORKLIFTS[forklift_type]

    expanded = expand_cargo_items(cargo)
    sorted_items = sort_items_for_packing(expanded)
    placed, unplaced = place_items(sorted_items, container, forklift)

    # 利用率
    used_vol = sum(p.L * p.W * p.H for p in placed)
    container_vol = container.L * container.W * container.H
    utilization = (used_vol / container_vol) * 100 if container_vol > 0 else 0.0

    return PackingResult(
        packed=placed,
        unpacked=unplaced,
        utilization=utilization,
    )


# ============================================================
# 輔助：把內部結構轉成 PackedItem schema（給 service 層用）
# ============================================================
def to_packed_item_schema(p: _PlacedItem) -> PackedItem:
    return PackedItem(
        id=p.id, base_id=p.base_id, type=p.type,
        L=p.L, W=p.W, H=p.H,
        weight=p.weight, stackable=p.stackable,
        x=p.x, y=p.y, z=p.z,
        is_packed=True,
        rotated=p.rotated,
    )


def to_unpacked_item_schema(u: _ExpandedItem) -> PackedItem:
    return PackedItem(
        id=u.id, base_id=u.base_id, type=u.type,
        L=u.L, W=u.W, H=u.H,
        weight=u.weight, stackable=u.stackable,
        x=None, y=None, z=None,
        is_packed=False,
    )
