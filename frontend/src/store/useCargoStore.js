import { create } from 'zustand';
import { CONTAINERS, FORKLIFTS } from '../constants';
import { packCargo, packCargoLocal } from '../api/apiClient';

/**
 * 全域狀態管理 — 取代原 HTML 的全域變數
 *
 * 用法：
 *   const cargoList = useCargoStore(s => s.cargoList);
 *   const addCargo  = useCargoStore(s => s.addCargo);
 *
 * 為什麼用 selector 而不是 useCargoStore() 一次取出全部？
 *   只訂閱用到的欄位，這個欄位沒變動時不會重新渲染。
 */
export const useCargoStore = create((set, get) => ({
  // ====== 輸入資料 ======
  cargoList: [],          // [{ id, type, L, W, H, weight, quantity, stackable }]
  containerType: '40',
  forkliftType: 'E35SH',

  // ====== 計算結果 ======
  packedItems: [],        // 演算法輸出（單件，含 x/y/z）
  unpackedItems: [],
  utilization: 0,
  isComputing: false,
  computeError: null,

  // ====== UI 狀態 ======
  xrayMode: false,
  viewMode: 'perspective',
  currentStep: 0,
  isPlaying: false,
  hoveredItemId: null,    // 滑鼠正在指的箱子 id

  // ====== 開關：用本地演算法 (false 才會打 API) ======
  //
  // false (預設) → 呼叫後端 FastAPI 的 /api/v1/pack
  // true         → 使用前端內建演算法（後端故障時的備援）
  //
  // 切換時機：
  //   - 開發後端時暫時改 true，前端可獨立測試
  //   - 演示時兩邊比對結果是否一致（驗證後端正確性）
  //   - 後端壞掉時臨時改 true 讓 demo 不中斷
  useLocalAlgorithm: false,

  // ====== Actions（Cargo 管理）======
  addCargo: (cargo) => set((state) => ({
    cargoList: [...state.cargoList, cargo],
  })),

  removeCargo: (idx) => set((state) => ({
    cargoList: state.cargoList.filter((_, i) => i !== idx),
  })),

  importCsvCargo: (rows) => set((state) => ({
    cargoList: [...state.cargoList, ...rows],
  })),

  clearAll: () => set({
    cargoList: [],
    packedItems: [],
    unpackedItems: [],
    utilization: 0,
    currentStep: 0,
  }),

  loadSampleData: () => set({
    cargoList: [
      { id: 'A001', type: 'heavy',   L: 1200, W: 1000, H: 800,  weight: 800,  quantity: 4, stackable: true },
      { id: 'A002', type: 'heavy',   L: 1500, W: 1200, H: 900,  weight: 1200, quantity: 3, stackable: true },
      { id: 'B001', type: 'fragile', L: 1000, W: 800,  H: 600,  weight: 150,  quantity: 5, stackable: false },
      { id: 'V001', type: 'vip',     L: 1400, W: 1100, H: 1000, weight: 600,  quantity: 2, stackable: true },
      { id: 'N001', type: 'normal',  L: 1000, W: 800,  H: 700,  weight: 250,  quantity: 8, stackable: true },
    ],
  }),

  // ====== Actions（選擇）======
  setContainer: (type) => set({ containerType: type }),
  setForklift: (type) => set({ forkliftType: type }),

  // ====== Actions（執行裝箱計算）======
  runPacking: async () => {
    const { cargoList, containerType, forkliftType, useLocalAlgorithm } = get();
    if (cargoList.length === 0) {
      alert('請先新增貨物');
      return;
    }

    set({ isComputing: true, computeError: null });
    try {
      const fn = useLocalAlgorithm ? packCargoLocal : packCargo;
      const result = await fn({ cargo: cargoList, containerType, forkliftType });

      // 計算空間利用率（如果後端沒回傳，前端自己算）
      const cont = CONTAINERS[containerType];
      const contVol = cont.L * cont.W * cont.H;
      const usedVol = (result.packed || []).reduce(
        (s, p) => s + p.L * p.W * p.H, 0
      );
      const utilization = result.utilization ?? (usedVol / contVol) * 100;

      set({
        packedItems: result.packed || [],
        unpackedItems: result.unpacked || [],
        utilization,
        currentStep: (result.packed || []).length,
        isComputing: false,
      });
    } catch (err) {
      console.error('[runPacking]', err);
      set({
        isComputing: false,
        computeError: err.message || '裝箱計算失敗',
      });
    }
  },

  // ====== Actions（UI 控制）======
  toggleXray: () => set((state) => ({ xrayMode: !state.xrayMode })),
  setViewMode: (mode) => set({ viewMode: mode }),
  setStep: (step) => set({ currentStep: step }),
  togglePlay: () => set((state) => ({ isPlaying: !state.isPlaying })),
  setHoveredItem: (id) => set({ hoveredItemId: id }),
}));

// ====== 衍生資料計算函式（純函式，給元件配 useMemo 用）======
//
// ⚠️ 重要：這不是 zustand selector，而是純計算函式
//
// 為什麼不寫成 selector？因為 selector 每次回傳新物件 {...} 會被 zustand
// 用 Object.is 判定為「資料變了」，造成無限重渲染迴圈。
//
// 正確用法：
//   const cargoList = useCargoStore(s => s.cargoList);
//   const containerType = useCargoStore(s => s.containerType);
//   const totals = useMemo(
//     () => computeTotals(cargoList, containerType),
//     [cargoList, containerType]
//   );
export function computeTotals(cargoList, containerType) {
  const totalCount = cargoList.reduce((s, c) => s + c.quantity, 0);
  const totalVolume = cargoList.reduce(
    (s, c) => s + (c.L * c.W * c.H * c.quantity) / 1e9, 0
  );
  const totalWeight = cargoList.reduce(
    (s, c) => s + c.weight * c.quantity, 0
  );
  const cont = CONTAINERS[containerType];
  const containerVolume = (cont.L * cont.W * cont.H) / 1e9;
  return { totalCount, totalVolume, totalWeight, containerVolume };
}
