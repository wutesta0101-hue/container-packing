// 貨櫃規格 — 內部尺寸 (mm) 與最大載重 (kg)
export const CONTAINERS = {
  '20':   { name: "20' Dry",  L: 5898,  W: 2352, H: 2393, maxWeight: 28000 },
  '40':   { name: "40' Dry",  L: 12032, W: 2352, H: 2393, maxWeight: 26000 },
  '40HQ': { name: "40' HQ",   L: 12032, W: 2352, H: 2698, maxWeight: 26000 },
};

// 堆高機規格 — 通道寬度約束來源（資料來源：Linde E25/E30/E35 系列技術文件）
// 通道寬度 = max(貨物寬度, 堆高機寬度)
// 通道高度 = 0 ~ 堆高機車身高度
// forkLength = 牙叉長度（mm）— 通道淨空判斷時，貨物正前方 + 90% 牙叉長度
//              範圍內可以有箱子（牙叉伸進去抬走）
export const FORKLIFTS = {
  'E25':    { name: 'Linde E25',     L: 3427, W: 1175, H: 2200, capacity: 2500, forkLength: 1150 },
  'E25S':   { name: 'Linde E25 S',   L: 3427, W: 1175, H: 2200, capacity: 2500, forkLength: 1150 },
  'E25SH':  { name: 'Linde E25 SH',  L: 3427, W: 1228, H: 2200, capacity: 2500, forkLength: 1150 },
  'E30S':   { name: 'Linde E30 S',   L: 3430, W: 1228, H: 2200, capacity: 3000, forkLength: 1150 },
  'E30SH':  { name: 'Linde E30 SH',  L: 3430, W: 1228, H: 2200, capacity: 3000, forkLength: 1150 },
  'E35SH':  { name: 'Linde E35 SH',  L: 3435, W: 1325, H: 2200, capacity: 3500, forkLength: 1150 },
};

// 牙叉延伸的安全係數（90% 是業界經驗值）
export const FORK_REACH_RATIO = 0.9;

// 貨物類型與顏色
export const CARGO_TYPES = {
  normal:  { label: '一般',  color: '#34c759', hex: 0x34c759 },
  heavy:   { label: '重物',  color: '#0a3d91', hex: 0x0a3d91 },
  fragile: { label: '易碎品', color: '#ff9500', hex: 0xff9500 },
  vip:     { label: 'VIP',  color: '#ffd60a', hex: 0xffd60a },
};

// 視角預設（用於 ViewControls）
export const VIEW_MODES = ['perspective', 'top', 'side', 'front'];
export const VIEW_LABELS = {
  perspective: '透視',
  top: '鳥瞰',
  side: '側視',
  front: '正視',
};
