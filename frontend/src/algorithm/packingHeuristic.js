/**
 * 3D 貨櫃裝箱演算法 — Bottom-Left-Back 啟發式
 *
 * 此檔案是「臨時的本地實作」，提供前端在後端完成前能立刻看到結果。
 * 後端 Python 完成 + 串接 API 後，此檔案應該保留，作為：
 *   - 後端輸出的「黃金標準」對照組（給定相同輸入，前後端結果應該一致）
 *   - 演算法邏輯的可讀文件（純 JS 比 Python + FastAPI 容易追）
 *
 * 演算法核心：
 *   1. 把所有貨物展開（quantity = 3 變成 3 件單獨物件）
 *   2. 排序：VIP 優先 → 體積大優先 → 重量大優先
 *   3. 對每件貨物，從候選錨點（anchors）中找符合所有物理約束的最內側位置
 *   4. 物理約束：不重疊、堆疊支撐、密度上小下大、堆高機通道淨空
 *
 * 座標系統（與貨櫃對齊）：
 *   - x 軸 = 長度方向（深處→出口），單位 mm
 *   - y 軸 = 寬度方向（左→右），單位 mm
 *   - z 軸 = 高度方向（地板→天花板），單位 mm
 *   - 原點 (0,0,0) = 貨櫃內部最深處的左下角
 *   - 出口位於 x = container.L 那一端
 */

import { CONTAINERS, FORKLIFTS } from '../constants';

// ============================================================
// 子函式：把 quantity 展開成單件清單
// ============================================================
function expandCargoItems(cargoList) {
  const items = [];
  for (const c of cargoList) {
    for (let i = 0; i < c.quantity; i++) {
      items.push({
        id: `${c.id}-${i + 1}`,    // 展開後的唯一 ID，例如 'A001-1'、'A001-2'
        baseId: c.id,               // 原本的批次 ID
        type: c.type,
        L: c.L, W: c.W, H: c.H,
        weight: c.weight,
        density: c.weight / (c.L * c.W * c.H / 1e9),  // kg/m³
        stackable: c.stackable,
        rotatable: c.rotatable !== false,  // 預設 true（規則 2：在地上轉 90 度）
      });
    }
  }
  return items;
}

// ============================================================
// 子函式：排序策略
// ============================================================
function sortItemsForPacking(items) {
  return [...items].sort((a, b) => {
    // 1. VIP 客戶優先
    if (a.type === 'vip' && b.type !== 'vip') return -1;
    if (b.type === 'vip' && a.type !== 'vip') return 1;
    // 2. 體積大者優先（差距 > 1cm³ 才比較）
    const va = a.L * a.W * a.H;
    const vb = b.L * b.W * b.H;
    if (Math.abs(vb - va) > 1e6) return vb - va;
    // 3. 重量大者優先（穩定底層）
    return b.weight - a.weight;
  });
}

// ============================================================
// 子函式：兩個 AABB 是否相交（不重疊檢測）
//   anchor + size 形成 box A
//   p (含 x,y,z,L,W,H) 是 box B
// ============================================================
function isOverlap(ax, ay, az, aL, aW, aH, p) {
  return !(
    ax + aL <= p.x || p.x + p.L <= ax ||
    ay + aW <= p.y || p.y + p.W <= ay ||
    az + aH <= p.z || p.z + p.H <= az
  );
}

// ============================================================
// 子函式：堆疊支撐檢查
//   若 z > 0，必須有支撐物，且：
//     - 所有支撐物 stackable = true
//     - 上方密度 ≤ 下方密度（重物在下原則，5% 容差）
// ============================================================
// ============================================================
// 子函式：堆疊支撐檢查（含懸空判斷）
//
// 若 z > 0，必須滿足以下條件：
//   1. 至少一個支撐物（接觸頂面 + 水平投影重疊）
//   2. 所有支撐物 stackable = true
//   3. 上方密度 ≤ 下方密度（重物在下原則，5% 容差）
//   4. ★ 支撐覆蓋率 ≥ 90%（懸空 + 縫隙合計不超過 10%）
//
// 覆蓋率計算：
//   - 所有支撐物與貨物底面相交的「矩形聯集面積」
//   - 用掃描線（sweep line）演算法精確計算
//   - 相對於貨物底面 (L × W) 的比例
// ============================================================
const COVERAGE_RATIO = 0.9;  // 90% 覆蓋率門檻（懸空 ≤ 10%）

function checkStackSupport(ax, ay, az, aL, aW, item, placed) {
  if (az === 0) return true;  // 直接放地板，免檢查

  // 找所有「頂面剛好等於 az」且「水平投影有重疊」的物件
  const supports = placed.filter(p =>
    Math.abs(p.z + p.H - az) < 1 &&
    !(ax + aL <= p.x || p.x + p.L <= ax ||
      ay + aW <= p.y || p.y + p.W <= ay)
  );

  if (supports.length === 0) return false;                    // 浮空
  if (supports.some(s => !s.stackable)) return false;         // 支撐物標記不可堆疊
  if (supports.some(s => item.density > s.density * 1.05))    // 密度條件
    return false;

  // ★ 覆蓋率檢查：把每個支撐物與貨物底面的相交矩形蒐集起來，
  //   算這些矩形的聯集面積佔貨物底面的比例
  const intersections = [];
  for (const s of supports) {
    const x0 = Math.max(ax, s.x);
    const y0 = Math.max(ay, s.y);
    const x1 = Math.min(ax + aL, s.x + s.L);
    const y1 = Math.min(ay + aW, s.y + s.W);
    if (x0 < x1 && y0 < y1) {
      intersections.push({ x0, y0, x1, y1 });
    }
  }
  const unionArea = computeRectangleUnionArea(intersections);
  const itemArea = aL * aW;
  if (unionArea / itemArea < COVERAGE_RATIO) return false;

  return true;
}

// ============================================================
// 掃描線演算法：計算多個矩形的聯集面積
//
// 演算法核心：
//   1. 收集所有矩形的 X 座標邊界，去重後排序
//   2. 對每對相鄰 X，計算這個垂直切片內被多少矩形覆蓋
//   3. 在切片內，把覆蓋的矩形依 Y 投影成線段，算線段聯集長度
//   4. 切片面積 = (x1 - x0) × Y 覆蓋長度
//
// 複雜度 O(N²)，對 N < 10 的場景非常快
// ============================================================
function computeRectangleUnionArea(rects) {
  if (rects.length === 0) return 0;

  // 收集並排序所有 X 邊界
  const xs = new Set();
  for (const r of rects) { xs.add(r.x0); xs.add(r.x1); }
  const sortedXs = [...xs].sort((a, b) => a - b);

  let totalArea = 0;
  for (let i = 0; i < sortedXs.length - 1; i++) {
    const x0 = sortedXs[i];
    const x1 = sortedXs[i + 1];
    if (x0 === x1) continue;

    // 收集在此 X 切片內的所有矩形（投影到 Y 軸成為線段）
    const yIntervals = [];
    for (const r of rects) {
      if (r.x0 <= x0 && r.x1 >= x1) {
        yIntervals.push([r.y0, r.y1]);
      }
    }
    if (yIntervals.length === 0) continue;

    // 算 Y 軸線段聯集長度
    yIntervals.sort((a, b) => a[0] - b[0]);
    let yCover = 0, curStart = yIntervals[0][0], curEnd = yIntervals[0][1];
    for (let j = 1; j < yIntervals.length; j++) {
      const [s, e] = yIntervals[j];
      if (s > curEnd) {
        yCover += curEnd - curStart;
        curStart = s; curEnd = e;
      } else {
        curEnd = Math.max(curEnd, e);
      }
    }
    yCover += curEnd - curStart;

    totalArea += (x1 - x0) * yCover;
  }
  return totalArea;
}

// ============================================================
// 子函式：堆高機通道淨空檢查（含牙叉延伸）
//
//   假設貨櫃出口在 x = container.L 端
//   放置貨物 (ax, ay, az, L, W, H) 後，從這件貨物正前方到出口
//   的「通道空間」內必須沒有已放置的貨物（在堆高機高度內）
//
//   ★ 牙叉延伸：堆高機的牙叉可以「伸進」貨物正前方一段距離壓著
//     前面的貨物作業。所以「正前方 + 90% 牙叉長度」之內可以有東西。
//
//   通道 X 範圍：(ax + L + reach, container.L)  ← 加上 reach
//   通道 Y 範圍：以放置物 Y 中線為中心，寬 max(item.W, forklift.W)
//   通道 Z 範圍：(0, forklift.H) 即堆高機車身高度內
// ============================================================
function isAisleClear(ax, ay, az, aL, aW, aH, placed, container, forklift) {
  // 通道 Y 範圍
  const aisleW = Math.max(aW, forklift.W);
  const yCenter = ay + aW / 2;
  const aisleY0 = Math.max(0, yCenter - aisleW / 2);
  const aisleY1 = Math.min(container.W, yCenter + aisleW / 2);

  // 牙叉容忍範圍 — 貨物正前方 forkReach 距離內可以有箱子
  const forkReach = (forklift.forkLength || 0) * 0.9;

  for (const p of placed) {
    // p 必須在「貨物正前方 + 牙叉容忍距離」之外，才算擋路
    if (p.x >= ax + aL + forkReach) {
      // y 與通道重疊？
      const yOverlap = Math.max(p.y, aisleY0) < Math.min(p.y + p.W, aisleY1);
      // z 在堆高機車身高度範圍內？
      const zOverlap = p.z < forklift.H;
      if (yOverlap && zOverlap) return false;  // 通道被擋
    }
  }
  return true;
}

// ============================================================
// 主函式：執行裝箱
//
//   輸入：sortedItems, container, forklift
//   輸出：{ packed: [{...item, x, y, z}], unpacked: [...] }
// ============================================================
function placeItems(sortedItems, container, forklift) {
  const placed = [];
  const unplaced = [];

  // 候選錨點：每放一個箱子就會新增 3 個（往 x、y、z 三個方向）
  let anchors = [{ x: 0, y: 0, z: 0 }];

  for (const item of sortedItems) {
    let bestPos = null;       // 最佳位置 + 旋轉狀態
    let bestRotated = false;

    // 排序候選錨點：x 小（內側）→ z 小（底部）→ y 小（後）
    // 這個順序體現「由內到外、由下到上」的裝載策略
    anchors.sort((a, b) => a.x - b.x || a.z - b.z || a.y - b.y);

    // 旋轉候選 — 規則 2：可旋轉 = 長寬互換（高度永遠不變）
    //   rotated=false → (L, W, H)
    //   rotated=true  → (W, L, H)
    // 不可旋轉的物件只試原方向；正方形物件兩種旋轉等效，也只試一次
    const rotations = (item.rotatable && item.L !== item.W)
      ? [false, true]
      : [false];

    outer:
    for (const a of anchors) {
      for (const rotated of rotations) {
        const curL = rotated ? item.W : item.L;
        const curW = rotated ? item.L : item.W;
        const curH = item.H;

        // 1. 邊界檢查：是否超出貨櫃
        if (a.x + curL > container.L ||
            a.y + curW > container.W ||
            a.z + curH > container.H) continue;

        // 2. 不重疊檢查
        const collide = placed.some(p =>
          isOverlap(a.x, a.y, a.z, curL, curW, curH, p)
        );
        if (collide) continue;

        // 3. 堆疊支撐檢查
        if (!checkStackSupport(a.x, a.y, a.z, curL, curW, item, placed)) {
          continue;
        }

        // 4. 堆高機通道淨空檢查
        if (!isAisleClear(a.x, a.y, a.z, curL, curW, curH,
                          placed, container, forklift)) {
          continue;
        }

        // 找到合法位置
        bestPos = a;
        bestRotated = rotated;
        break outer;
      }
    }

    if (bestPos) {
      // 把 item 的 L/W 換成最終擺放尺寸（rotated 時 L 與 W 互換）
      const finalL = bestRotated ? item.W : item.L;
      const finalW = bestRotated ? item.L : item.W;
      const placedItem = {
        ...item,
        L: finalL, W: finalW,         // 覆寫成最終尺寸
        x: bestPos.x, y: bestPos.y, z: bestPos.z,
        rotated: bestRotated,         // 記錄旋轉狀態（給 UI 顯示用）
      };
      placed.push(placedItem);

      // 新增 3 個候選錨點（用最終尺寸算）
      anchors.push({ x: placedItem.x + finalL, y: placedItem.y, z: placedItem.z });
      anchors.push({ x: placedItem.x, y: placedItem.y + finalW, z: placedItem.z });
      anchors.push({ x: placedItem.x, y: placedItem.y, z: placedItem.z + placedItem.H });

      // 移除被佔用的錨點
      anchors = anchors.filter(an =>
        !(an.x === bestPos.x && an.y === bestPos.y && an.z === bestPos.z)
      );
    } else {
      unplaced.push(item);
    }
  }

  return { placed, unplaced };
}

// ============================================================
// 主入口：runPackingHeuristic
//
// 這是公開介面，介面與後端 API 對齊：
//   輸入：{ cargo: CargoInput[], containerType, forkliftType }
//   輸出：{ taskId, packed, unpacked, utilization }
// ============================================================
export function runPackingHeuristic({ cargo, containerType, forkliftType }) {
  const container = CONTAINERS[containerType];
  const forklift = FORKLIFTS[forkliftType];

  if (!container) throw new Error(`未知貨櫃類型: ${containerType}`);
  if (!forklift) throw new Error(`未知堆高機類型: ${forkliftType}`);

  // 1. 展開 quantity
  const expanded = expandCargoItems(cargo);

  // 2. 排序
  const sorted = sortItemsForPacking(expanded);

  // 3. 裝箱
  const { placed, unplaced } = placeItems(sorted, container, forklift);

  // 4. 計算利用率
  const usedVol = placed.reduce((s, p) => s + p.L * p.W * p.H, 0);
  const containerVol = container.L * container.W * container.H;
  const utilization = (usedVol / containerVol) * 100;

  return {
    taskId: `local-${Date.now()}`,
    packed: placed,
    unpacked: unplaced,
    utilization,
  };
}
