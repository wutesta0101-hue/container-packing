"""演算法測試 — 三層防護

1. 黃金對照（golden）：用前端 JS 演算法產出的結果作為「正確答案」，
   驗證 Python 版逐欄位完全一致。這保證未來改任何一邊時，
   立刻能發現邏輯偏離。

2. 不變式：跑完任何輸入後，輸出必須滿足物理約束（不重疊、邊界內、
   通道規則、重物在下）。這抓得到「結果不一致但都還是物理合法」
   的演算法漏洞。

3. 單元測試：每個約束函式（is_overlap, check_stack_support,
   is_aisle_clear）的正反案例。

跑法：
    cd backend
    pytest tests/test_algorithm.py -v
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import (
    CargoInput, ContainerType, ForkliftType, CONTAINERS, FORKLIFTS,
)
from algorithm.packing import (
    run_packing_heuristic,
    expand_cargo_items, sort_items_for_packing,
    is_overlap, check_stack_support, is_aisle_clear,
    _PlacedItem, _ExpandedItem,
)


GOLDEN_PATH = Path(__file__).parent / "fixtures" / "golden.json"


# ============================================================
# Helper：把 golden.json 中的 cargo dict 轉成 CargoInput
# ============================================================
def _parse_cargo(raw_cargo: list[dict]) -> list[CargoInput]:
    return [CargoInput(**c) for c in raw_cargo]


# ============================================================
# 1. 黃金對照測試 — 確保 Python 版輸出與 JS 版完全一致
# ============================================================
@pytest.fixture(scope="module")
def golden():
    with open(GOLDEN_PATH) as f:
        return json.load(f)


@pytest.mark.parametrize("case_name", [
    "sample", "single", "stacked", "too_big", "smaller_forklift", "fork_reach", "rotation",
])
def test_golden_packed_count(golden, case_name):
    """裝入件數要與 JS 版一致"""
    case = golden[case_name]
    cargo = _parse_cargo(case["input"]["cargo"])
    result = run_packing_heuristic(
        cargo=cargo,
        container_type=case["input"]["container"],
        forklift_type=case["input"]["forklift"],
    )
    assert len(result.packed) == len(case["output"]["packed"])
    assert len(result.unpacked) == len(case["output"]["unpacked"])


@pytest.mark.parametrize("case_name", [
    "sample", "single", "stacked", "too_big", "smaller_forklift", "fork_reach", "rotation",
])
def test_golden_packed_positions(golden, case_name):
    """每件貨物的位置（id, x, y, z）要與 JS 版完全一致

    這個測試是最強的保證 — 若兩邊邏輯有任何偏差（排序、約束、錨點處理）
    都會在這裡被抓到。
    """
    case = golden[case_name]
    cargo = _parse_cargo(case["input"]["cargo"])
    result = run_packing_heuristic(
        cargo=cargo,
        container_type=case["input"]["container"],
        forklift_type=case["input"]["forklift"],
    )

    expected = case["output"]["packed"]
    actual = result.packed
    assert len(actual) == len(expected)

    for i, (e, a) in enumerate(zip(expected, actual)):
        assert a.id == e["id"], f"案例 {case_name} 第 {i} 件 id 不一致"
        assert a.x == e["x"], f"案例 {case_name} {a.id}: x 不一致 (Python={a.x}, JS={e['x']})"
        assert a.y == e["y"], f"案例 {case_name} {a.id}: y 不一致 (Python={a.y}, JS={e['y']})"
        assert a.z == e["z"], f"案例 {case_name} {a.id}: z 不一致 (Python={a.z}, JS={e['z']})"
        # 旋轉後最終尺寸與 rotated 旗標
        assert a.L == e["L"], f"案例 {case_name} {a.id}: L 不一致 (Python={a.L}, JS={e['L']})"
        assert a.W == e["W"], f"案例 {case_name} {a.id}: W 不一致 (Python={a.W}, JS={e['W']})"
        assert a.rotated == e["rotated"], f"案例 {case_name} {a.id}: rotated 不一致"


@pytest.mark.parametrize("case_name", [
    "sample", "single", "stacked", "too_big", "smaller_forklift", "fork_reach", "rotation",
])
def test_golden_utilization(golden, case_name):
    """空間利用率與 JS 版一致（容差 0.01%）"""
    case = golden[case_name]
    cargo = _parse_cargo(case["input"]["cargo"])
    result = run_packing_heuristic(
        cargo=cargo,
        container_type=case["input"]["container"],
        forklift_type=case["input"]["forklift"],
    )
    assert abs(result.utilization - case["output"]["utilization"]) < 0.01


# ============================================================
# 2. 不變式測試 — 物理約束必須成立
# ============================================================
def test_invariant_no_overlap():
    """sample 案例的所有箱子兩兩不重疊"""
    with open(GOLDEN_PATH) as f:
        case = json.load(f)["sample"]
    cargo = _parse_cargo(case["input"]["cargo"])
    result = run_packing_heuristic(cargo, "40", "E35SH")
    placed = result.packed

    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            a, b = placed[i], placed[j]
            assert not is_overlap(a.x, a.y, a.z, a.L, a.W, a.H, b), \
                f"{a.id} 與 {b.id} 重疊"


def test_invariant_within_bounds():
    """所有箱子在貨櫃邊界內"""
    with open(GOLDEN_PATH) as f:
        case = json.load(f)["sample"]
    cargo = _parse_cargo(case["input"]["cargo"])
    result = run_packing_heuristic(cargo, "40", "E35SH")
    cont = CONTAINERS[ContainerType.DRY_40]

    for p in result.packed:
        assert p.x >= 0
        assert p.y >= 0
        assert p.z >= 0
        assert p.x + p.L <= cont.L
        assert p.y + p.W <= cont.W
        assert p.z + p.H <= cont.H


def test_invariant_vip_first():
    """VIP 客戶應該出現在裝載順序最前面"""
    with open(GOLDEN_PATH) as f:
        case = json.load(f)["sample"]
    cargo = _parse_cargo(case["input"]["cargo"])
    result = run_packing_heuristic(cargo, "40", "E35SH")

    # 找出第一個非 VIP 的位置
    for i, p in enumerate(result.packed):
        if p.type != "vip":
            # 之前的應該全是 VIP
            for j in range(i):
                assert result.packed[j].type == "vip", \
                    f"VIP 排序錯誤：第 {j} 件是 {result.packed[j].type}"
            return
    # 全都是 VIP 也沒問題


def test_invariant_aisle_at_placement():
    """每件貨物放置「當下」，通道應淨空（依放置順序檢查）"""
    with open(GOLDEN_PATH) as f:
        case = json.load(f)["sample"]
    cargo = _parse_cargo(case["input"]["cargo"])
    result = run_packing_heuristic(cargo, "40", "E35SH")
    cont = CONTAINERS[ContainerType.DRY_40]
    fk = FORKLIFTS[ForkliftType.E35SH]

    placed_so_far: list[_PlacedItem] = []
    for item in result.packed:
        assert is_aisle_clear(
            item.x, item.y, item.z, item.L, item.W, item.H,
            placed_so_far, cont, fk,
        ), f"{item.id} 放置時通道被擋"
        placed_so_far.append(item)


def test_invariant_stack_support():
    """z>0 的箱子下方都有支撐物且密度條件成立"""
    with open(GOLDEN_PATH) as f:
        case = json.load(f)["sample"]
    cargo = _parse_cargo(case["input"]["cargo"])
    result = run_packing_heuristic(cargo, "40", "E35SH")

    for p in result.packed:
        if p.z == 0:
            continue
        # 找下方有接觸的支撐物
        supports = [
            s for s in result.packed
            if abs(s.z + s.H - p.z) < 1
            and not (
                p.x + p.L <= s.x or s.x + s.L <= p.x or
                p.y + p.W <= s.y or s.y + s.W <= p.y
            )
        ]
        assert len(supports) > 0, f"{p.id} 在 z={p.z} 但下方無支撐"
        for s in supports:
            assert s.stackable, f"{p.id} 的支撐物 {s.id} 標記為不可堆疊"
            assert p.density <= s.density * 1.05, \
                f"{p.id}({p.density:.0f}) 密度大於 {s.id}({s.density:.0f})"


# ============================================================
# 3. 單元測試 — 個別約束函式
# ============================================================
class TestIsOverlap:
    def _box(self, x, y, z, L=100, W=100, H=100):
        return _PlacedItem(
            id="t", base_id="t", type="normal",
            L=L, W=W, H=H, weight=1, density=1, stackable=True,
            x=x, y=y, z=z,
        )

    def test_clearly_separated(self):
        b = self._box(1000, 0, 0)
        assert is_overlap(0, 0, 0, 100, 100, 100, b) is False

    def test_clearly_overlapping(self):
        b = self._box(50, 50, 50)
        assert is_overlap(0, 0, 0, 100, 100, 100, b) is True

    def test_face_touching_no_overlap(self):
        """剛好貼齊（面接觸）不算重疊"""
        b = self._box(100, 0, 0)
        assert is_overlap(0, 0, 0, 100, 100, 100, b) is False

    def test_corner_touching_no_overlap(self):
        b = self._box(100, 100, 100)
        assert is_overlap(0, 0, 0, 100, 100, 100, b) is False


class TestCheckStackSupport:
    def _box(self, x, y, z, L=100, W=100, H=100, stackable=True, density=1.0):
        return _PlacedItem(
            id=f"b{x}_{y}_{z}", base_id="t", type="normal",
            L=L, W=W, H=H, weight=1, density=density,
            stackable=stackable, x=x, y=y, z=z,
        )

    def _item(self, density=1.0):
        return _ExpandedItem(
            id="new", base_id="t", type="normal",
            L=100, W=100, H=100, weight=1, density=density, stackable=True,
        )

    def test_on_floor_always_ok(self):
        """z=0 直接放地板，不需檢查"""
        assert check_stack_support(0, 0, 0, 100, 100, self._item(), []) is True

    def test_floating_rejected(self):
        """z>0 但下方無物件 → 浮空，拒絕"""
        assert check_stack_support(0, 0, 100, 100, 100, self._item(), []) is False

    def test_with_support(self):
        """z>0 且下方有支撐 → OK"""
        support = self._box(0, 0, 0, H=100)  # 頂面在 z=100
        assert check_stack_support(0, 0, 100, 100, 100, self._item(), [support]) is True

    def test_non_stackable_support_rejected(self):
        """支撐物標記 stackable=False → 拒絕"""
        support = self._box(0, 0, 0, H=100, stackable=False)
        assert check_stack_support(0, 0, 100, 100, 100, self._item(), [support]) is False

    def test_density_condition_violated(self):
        """上方密度遠大於下方 → 拒絕（重物在下原則）"""
        light_support = self._box(0, 0, 0, H=100, density=50)
        heavy_item = self._item(density=200)  # 200 > 50 * 1.05
        assert check_stack_support(0, 0, 100, 100, 100, heavy_item, [light_support]) is False

    def test_density_condition_within_tolerance(self):
        """密度差距在 5% 容差內 → OK"""
        support = self._box(0, 0, 0, H=100, density=100)
        item = self._item(density=104)  # 104 < 100 * 1.05 = 105
        assert check_stack_support(0, 0, 100, 100, 100, item, [support]) is True

    # ====== 90% 覆蓋率規則（規則 3）======
    def _big_item(self, L=1000, W=1000, density=1.0):
        return _ExpandedItem(
            id="new", base_id="t", type="normal",
            L=L, W=W, H=100, weight=1, density=density, stackable=True,
        )

    def test_full_coverage_passes(self):
        """100% 覆蓋 → 通過"""
        # 上方 1000×1000 物件，下方一個 1000×1000 支撐物剛好完整覆蓋
        sup = self._box(0, 0, 0, L=1000, W=1000, H=500)
        assert check_stack_support(
            0, 0, 500, 1000, 1000, self._big_item(), [sup]
        ) is True

    def test_95pct_coverage_passes(self):
        """95% 覆蓋率（懸空 5%）→ 通過

        上方 1000×1000，下方一個 1000×950 支撐 → 覆蓋率 95%
        """
        sup = self._box(0, 0, 0, L=1000, W=950, H=500)
        assert check_stack_support(
            0, 0, 500, 1000, 1000, self._big_item(), [sup]
        ) is True

    def test_85pct_coverage_rejected(self):
        """85% 覆蓋率（懸空 15%）→ 拒絕

        上方 1000×1000，下方一個 1000×850 支撐 → 覆蓋率 85%（不到 90%）
        """
        sup = self._box(0, 0, 0, L=1000, W=850, H=500)
        assert check_stack_support(
            0, 0, 500, 1000, 1000, self._big_item(), [sup]
        ) is False

    def test_cross_gap_with_sufficient_coverage(self):
        """跨縫但覆蓋足夠 → 通過

        上方 1000×1000，下方兩個 450×1000 支撐 + 100mm 縫
        覆蓋面積 = 2 × 450 × 1000 = 900000，佔比 90%（剛好過關）
        """
        sup1 = self._box(0,   0, 0, L=450, W=1000, H=500)
        sup2 = self._box(550, 0, 0, L=450, W=1000, H=500)
        assert check_stack_support(
            0, 0, 500, 1000, 1000, self._big_item(), [sup1, sup2]
        ) is True

    def test_cross_gap_insufficient_coverage(self):
        """跨縫且覆蓋不足 → 拒絕

        上方 1000×1000，下方兩個 400×1000 支撐 + 200mm 縫
        覆蓋面積 = 2 × 400 × 1000 = 800000，佔比 80%（不足 90%）
        """
        sup1 = self._box(0,   0, 0, L=400, W=1000, H=500)
        sup2 = self._box(600, 0, 0, L=400, W=1000, H=500)
        assert check_stack_support(
            0, 0, 500, 1000, 1000, self._big_item(), [sup1, sup2]
        ) is False

    def test_overlapping_supports_no_double_count(self):
        """支撐物部分重疊 → 重疊區只算一次

        上方 1000×1000，兩個 600×1000 支撐物，重疊 200mm
        若不去重 = 1200×1000 (錯，超過底面)；去重 = 1000×1000 (對)
        應該過關（覆蓋 100%）
        """
        sup1 = self._box(0,   0, 0, L=600, W=1000, H=500)
        sup2 = self._box(400, 0, 0, L=600, W=1000, H=500)
        assert check_stack_support(
            0, 0, 500, 1000, 1000, self._big_item(), [sup1, sup2]
        ) is True


# ============================================================
# 掃描線聯集面積單元測試
# ============================================================
class TestRectangleUnionArea:
    def test_empty_returns_zero(self):
        from algorithm.packing import compute_rectangle_union_area
        assert compute_rectangle_union_area([]) == 0

    def test_single_rect(self):
        from algorithm.packing import compute_rectangle_union_area
        # (0,0) 到 (10,10) → 100
        assert compute_rectangle_union_area([(0, 0, 10, 10)]) == 100

    def test_disjoint_rects(self):
        from algorithm.packing import compute_rectangle_union_area
        # 兩個不相交矩形 → 面積相加
        rects = [(0, 0, 10, 10), (20, 0, 30, 10)]
        assert compute_rectangle_union_area(rects) == 200

    def test_overlapping_rects(self):
        from algorithm.packing import compute_rectangle_union_area
        # 兩個 10×10 矩形 5×5 重疊
        # 聯集 = 10×10 + 10×10 - 5×5 = 175
        rects = [(0, 0, 10, 10), (5, 5, 15, 15)]
        assert compute_rectangle_union_area(rects) == 175

    def test_complete_overlap(self):
        from algorithm.packing import compute_rectangle_union_area
        # 一個矩形完全包含另一個
        rects = [(0, 0, 100, 100), (10, 10, 90, 90)]
        # 聯集 = 大的那個 = 10000
        assert compute_rectangle_union_area(rects) == 10000

    def test_three_rects_chain(self):
        from algorithm.packing import compute_rectangle_union_area
        # 三個矩形依序重疊
        rects = [(0, 0, 10, 10), (5, 0, 15, 10), (10, 0, 20, 10)]
        # 第 1 與 2 重疊 5 寬，第 2 與 3 接觸不重疊
        # 聯集 = 完整 0~20 寬度 = 200
        assert compute_rectangle_union_area(rects) == 200


class TestIsAisleClear:
    def _box(self, x, y, z, L=1000, W=1000, H=1000):
        return _PlacedItem(
            id=f"b{x}_{y}_{z}", base_id="t", type="normal",
            L=L, W=W, H=H, weight=1, density=1, stackable=True,
            x=x, y=y, z=z,
        )

    def setup_method(self):
        self.cont = CONTAINERS[ContainerType.DRY_40]
        self.fk = FORKLIFTS[ForkliftType.E35SH]

    def test_empty_aisle(self):
        """無已放置物 → 通道淨空"""
        assert is_aisle_clear(0, 0, 0, 1000, 1000, 1000, [], self.cont, self.fk) is True

    def test_blocking_box_rejects(self):
        """放置位置正前方遠處（超過牙叉延伸）有箱子 → 通道被擋

        E35SH 的 forkLength = 1150，90% = 1035mm 容忍。
        貨物 (0,0,0,1000) 的「擋路門檻」= 1000 + 1035 = 2035。
        箱子在 x=3000 遠超過門檻 → 應該被判擋路。
        """
        block = self._box(3000, 0, 0)
        assert is_aisle_clear(0, 0, 0, 1000, 1000, 1000, [block], self.cont, self.fk) is False

    def test_within_fork_reach_passes(self):
        """貨物正前方但在牙叉延伸範圍內 → 不算擋路（牙叉可伸進去）"""
        # 貨物 (0,0,0,1000)，門檻 = 1000 + 1035 = 2035
        # 箱子在 x=1500（門檻內 535mm）→ 牙叉可以伸進去 → 不擋
        block = self._box(1500, 0, 0)
        assert is_aisle_clear(0, 0, 0, 1000, 1000, 1000, [block], self.cont, self.fk) is True

    def test_box_above_aisle_height_passes(self):
        """已存在箱子高過堆高機車身 → 不算擋路"""
        # 堆高機高 2200，箱子 z=2200 開始 → 不影響通道
        block = self._box(3000, 0, 2200)
        assert is_aisle_clear(0, 0, 0, 1000, 1000, 1000, [block], self.cont, self.fk) is True

    def test_box_behind_does_not_block(self):
        """已存在箱子在「內側」（更深處）→ 不擋通道"""
        # 我要放 (5000, 0, 0)，已存在的在 (1000, 0, 0)
        # p.x=1000 < ax+aL+reach，所以條件不成立 → 不擋
        block = self._box(1000, 0, 0)
        assert is_aisle_clear(5000, 0, 0, 1000, 1000, 1000, [block], self.cont, self.fk) is True


# ============================================================
# 4. 排序測試
# ============================================================
def test_sort_vip_first():
    items = [
        _ExpandedItem(id="a", base_id="a", type="normal", L=2000, W=2000, H=2000,
                      weight=100, density=12.5, stackable=True),
        _ExpandedItem(id="b", base_id="b", type="vip", L=100, W=100, H=100,
                      weight=10, density=10000, stackable=True),
    ]
    sorted_items = sort_items_for_packing(items)
    assert sorted_items[0].type == "vip"


def test_sort_volume_then_weight():
    """非 VIP 中：體積大者優先；體積近似時，重量大者優先"""
    items = [
        # 大體積、輕：應該排前面
        _ExpandedItem(id="big_light", base_id="big_light", type="normal",
                      L=2000, W=2000, H=2000, weight=10, density=1.25, stackable=True),
        # 小體積、重：排後面
        _ExpandedItem(id="small_heavy", base_id="small_heavy", type="normal",
                      L=500, W=500, H=500, weight=1000, density=8000, stackable=True),
    ]
    sorted_items = sort_items_for_packing(items)
    assert sorted_items[0].id == "big_light"


# ============================================================
# 5. 展開測試
# ============================================================
def test_expand_quantity():
    cargo = [
        CargoInput(id="A", L=100, W=100, H=100, weight=1.0, quantity=3),
    ]
    expanded = expand_cargo_items(cargo)
    assert len(expanded) == 3
    assert expanded[0].id == "A-1"
    assert expanded[1].id == "A-2"
    assert expanded[2].id == "A-3"
    assert all(e.base_id == "A" for e in expanded)


def test_density_calculation():
    """密度 = 重量 / 體積（m³）"""
    cargo = [CargoInput(id="X", L=1000, W=1000, H=1000, weight=500.0, quantity=1)]
    # 體積 = 1000³ mm³ = 1 m³
    # 密度 = 500 / 1 = 500 kg/m³
    expanded = expand_cargo_items(cargo)
    assert abs(expanded[0].density - 500.0) < 0.01


# ============================================================
# 6. 主入口測試
# ============================================================
def test_run_packing_main_entry():
    """主入口能正確接收 enum / 字串雙形式輸入"""
    cargo = [CargoInput(id="A", L=1000, W=1000, H=1000, weight=100.0, quantity=1)]

    # 用字串
    r1 = run_packing_heuristic(cargo, "40", "E35SH")
    # 用 enum
    r2 = run_packing_heuristic(cargo, ContainerType.DRY_40, ForkliftType.E35SH)

    assert len(r1.packed) == len(r2.packed) == 1
    assert r1.utilization == r2.utilization


# ============================================================
# 規則 2：旋轉邏輯
# ============================================================
class TestRotation:
    def test_no_rotation_when_disabled(self):
        """rotatable=False → 永遠不旋轉，原方向放不下就 unpacked"""
        # 貨物 2400 寬，超過貨櫃 W=2352
        # rotatable=False 即使旋轉後 L=2400×W=600 也應該不會嘗試
        cargo = [
            CargoInput(id="X", type="normal",
                       L=600, W=2400, H=500, weight=100.0,
                       quantity=1, stackable=True, rotatable=False),
        ]
        # 用 20' 貨櫃（W=2352），原方向 W=2400 > 2352 放不下
        result = run_packing_heuristic(cargo, "20", "E25")
        assert len(result.packed) == 0
        assert len(result.unpacked) == 1

    def test_rotation_used_when_needed(self):
        """rotatable=True，原方向放不下時演算法會嘗試旋轉"""
        # 同上情境但 rotatable=True
        # 旋轉後 L=2400, W=600 → L 也超過 5898（20' 長），但這次 X 軸 5898 > 2400 放得下
        cargo = [
            CargoInput(id="X", type="normal",
                       L=600, W=2400, H=500, weight=100.0,
                       quantity=1, stackable=True, rotatable=True),
        ]
        result = run_packing_heuristic(cargo, "20", "E25")
        assert len(result.packed) == 1
        # 應該被旋轉了
        assert result.packed[0].rotated is True
        # 旋轉後 L 與 W 互換
        assert result.packed[0].L == 2400
        assert result.packed[0].W == 600

    def test_square_item_no_rotation_attempt(self):
        """正方形物件（L == W）不會浪費時間嘗試旋轉"""
        cargo = [
            CargoInput(id="SQ", type="normal",
                       L=1000, W=1000, H=500, weight=100.0,
                       quantity=1, stackable=True, rotatable=True),
        ]
        result = run_packing_heuristic(cargo, "20", "E25")
        assert len(result.packed) == 1
        # 正方形不算旋轉（兩種方向等效）
        assert result.packed[0].rotated is False

    def test_rotation_affects_anchor_offsets(self):
        """旋轉後新增的錨點要以「最終尺寸」為基準

        放一件 (L=600, W=2400) 旋轉後 (L=2400, W=600) 在原點
        新增的錨點應為:
          (2400, 0, 0)   ← 沿 X 用最終 L
          (0, 600, 0)    ← 沿 Y 用最終 W
          (0, 0, 500)    ← 沿 Z 用 H
        若用原始尺寸算錯，會導致下一件物件放錯位置
        """
        cargo = [
            CargoInput(id="A", type="normal",
                       L=600, W=2400, H=500, weight=100.0,
                       quantity=2, stackable=True, rotatable=True),
        ]
        result = run_packing_heuristic(cargo, "20", "E25")
        # 兩件都應裝入；第二件位置應該避開第一件的最終佔位
        assert len(result.packed) == 2
        a, b = result.packed
        # 確保 b 沒踩到 a
        assert not (a.x < b.x + b.L and b.x < a.x + a.L
                    and a.y < b.y + b.W and b.y < a.y + a.W
                    and a.z < b.z + b.H and b.z < a.z + a.H)
