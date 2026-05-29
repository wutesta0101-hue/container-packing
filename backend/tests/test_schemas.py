"""schemas 模組冒煙測試

跑法：cd backend && python -m tests.test_schemas
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import ValidationError
from schemas import (
    CargoInput, CargoType, PackedItem,
    ContainerType, ForkliftType, CONTAINERS, FORKLIFTS,
    PackRequest, PackResponse,
)

def test_valid_cargo_input():
    """合法輸入應該正常建立"""
    c = CargoInput(
        id="A001", type="heavy",
        L=1200, W=1000, H=800,
        weight=800.0, quantity=4, stackable=True,
    )
    assert c.id == "A001"
    assert c.type == CargoType.HEAVY
    print("✓ 合法 CargoInput 建立成功")


def test_default_values():
    """type 與 stackable 應該有預設值"""
    c = CargoInput(id="X", L=100, W=100, H=100, weight=1.0, quantity=1)
    assert c.type == CargoType.NORMAL
    assert c.stackable is True
    print("✓ 預設值正確（type=normal, stackable=True）")


def test_invalid_negative_dimension():
    """負數尺寸應該被拒絕"""
    try:
        CargoInput(id="X", L=-100, W=100, H=100, weight=1.0, quantity=1)
        assert False, "應該丟出 ValidationError"
    except ValidationError as e:
        assert "greater than 0" in str(e)
        print("✓ 負數尺寸被拒絕")


def test_invalid_cargo_type():
    """不在 enum 內的類型應該被拒絕"""
    try:
        CargoInput(id="X", type="alien", L=1, W=1, H=1, weight=1.0, quantity=1)
        assert False, "應該丟出 ValidationError"
    except ValidationError as e:
        assert "alien" in str(e) or "valid" in str(e).lower()
        print("✓ 非法 cargo type 被拒絕")


def test_id_no_whitespace():
    """ID 含空白應該被拒絕"""
    try:
        CargoInput(id="A 001", L=1, W=1, H=1, weight=1.0, quantity=1)
        assert False, "應該丟出 ValidationError"
    except ValidationError as e:
        assert "空白" in str(e)
        print("✓ ID 含空白被拒絕")


def test_container_lookup():
    """貨櫃規格表查詢"""
    spec = CONTAINERS[ContainerType.DRY_40]
    assert spec.L == 12032
    assert spec.W == 2352
    assert spec.H == 2393
    assert spec.max_weight == 26000
    print(f"✓ 40' Dry 規格：{spec.L}×{spec.W}×{spec.H}, 最大載重 {spec.max_weight}kg")


def test_forklift_lookup():
    """堆高機規格表查詢"""
    fk = FORKLIFTS[ForkliftType.E35SH]
    assert fk.W == 1325  # 通道寬度約束
    assert fk.capacity == 3500
    print(f"✓ E35 SH 規格：通道寬 {fk.W}mm, 載重 {fk.capacity}kg")


def test_pack_request():
    """完整的裝箱請求"""
    req = PackRequest(
        cargo=[
            CargoInput(id="A001", type="heavy",
                       L=1200, W=1000, H=800,
                       weight=800.0, quantity=4, stackable=True),
            CargoInput(id="V001", type="vip",
                       L=1400, W=1100, H=1000,
                       weight=600.0, quantity=2, stackable=True),
        ],
        container_type="40",
        forklift_type="E35SH",
    )
    assert len(req.cargo) == 2
    assert req.container_type == ContainerType.DRY_40
    print(f"✓ PackRequest 建立成功，含 {len(req.cargo)} 筆貨物")


def test_packed_item():
    """裝載結果含坐標"""
    item = PackedItem(
        id="A001-1", base_id="A001", type="heavy",
        L=1200, W=1000, H=800, weight=800.0, stackable=True,
        x=0, y=0, z=0, is_packed=True,
    )
    assert item.is_packed
    print(f"✓ PackedItem 建立成功，位置 ({item.x}, {item.y}, {item.z})")


def test_unpacked_item():
    """未裝入的貨物，坐標可為 None"""
    item = PackedItem(
        id="X-1", base_id="X", type="normal",
        L=100, W=100, H=100, weight=1.0, stackable=True,
        is_packed=False,
    )
    assert item.x is None
    print("✓ 未裝入物的 x/y/z 可為 None")


def test_json_serialization():
    """檢查能正確 dump 成 JSON（FastAPI 回應時會用到）"""
    req = PackRequest(
        cargo=[CargoInput(id="A", L=1, W=1, H=1, weight=1.0, quantity=1)],
        container_type="40", forklift_type="E35SH",
    )
    json_data = req.model_dump_json()
    assert '"40"' in json_data
    assert '"E35SH"' in json_data
    print("✓ JSON 序列化正常")


if __name__ == "__main__":
    print("\n=== Schemas 冒煙測試 ===\n")
    test_valid_cargo_input()
    test_default_values()
    test_invalid_negative_dimension()
    test_invalid_cargo_type()
    test_id_no_whitespace()
    test_container_lookup()
    test_forklift_lookup()
    test_pack_request()
    test_packed_item()
    test_unpacked_item()
    test_json_serialization()
    print("\n✓ 全部 11 項測試通過\n")
