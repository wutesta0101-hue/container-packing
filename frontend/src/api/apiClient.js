import axios from 'axios';
import { runPackingHeuristic } from '../algorithm/packingHeuristic';

// 後端 API 位置 — 對應 backend/.env 的 API_PORT=9000
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:9000';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ============================================================
// 命名規範轉換
//
// 前端：camelCase (containerType, baseId, isPacked)
// 後端：snake_case (container_type, base_id, is_packed)
//
// 為什麼不統一？因為兩邊各自符合該語言的慣例：
//   - JavaScript 慣用 camelCase
//   - Python 慣用 snake_case
//
// 轉換邊界放在 apiClient — store 與 UI 元件只看到 camelCase。
// ============================================================
function toSnakeCase(str) {
  // 1. 全大寫的 key 不轉（如 'L', 'W', 'H', 'API'）
  // 2. 開頭大寫不加底線（如 'Type' → 'type'，但實務上 key 不會這樣寫）
  // 3. 中間的大寫前加底線（標準 camelCase → snake_case）
  if (!/[a-z]/.test(str)) return str;  // 全大寫直接回傳
  return str
    .replace(/([a-z])([A-Z])/g, '$1_$2')   // camelCase → camel_Case
    .toLowerCase();
}

function toCamelCase(str) {
  return str.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
}

/**
 * 遞迴轉換物件的 key（陣列也會處理）
 */
function convertKeys(obj, converter) {
  if (Array.isArray(obj)) {
    return obj.map(item => convertKeys(item, converter));
  }
  if (obj !== null && typeof obj === 'object' && obj.constructor === Object) {
    const result = {};
    for (const [key, value] of Object.entries(obj)) {
      result[converter(key)] = convertKeys(value, converter);
    }
    return result;
  }
  return obj;
}

const toSnake = (obj) => convertKeys(obj, toSnakeCase);
const toCamel = (obj) => convertKeys(obj, toCamelCase);

// ============================================================
// 友善錯誤訊息
// ============================================================
function makeFriendlyError(err) {
  if (err.code === 'ERR_NETWORK' || err.message === 'Network Error') {
    return new Error('無法連線到後端，請確認 FastAPI 已啟動 (port 9000)');
  }
  if (err.code === 'ECONNABORTED') {
    return new Error('後端回應逾時（30 秒），可能貨物太多需要更久時間');
  }
  if (err.response?.status === 422) {
    // Pydantic 驗證錯誤
    const detail = err.response.data?.detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      const field = (first.loc || []).join('.');
      return new Error(`輸入驗證失敗 [${field}]: ${first.msg}`);
    }
    return new Error('後端拒絕了請求格式');
  }
  if (err.response?.status === 404) {
    return new Error('找不到指定的任務');
  }
  if (err.response?.status >= 500) {
    return new Error(`後端錯誤 (${err.response.status})：${err.response.data?.detail || '未知錯誤'}`);
  }
  return err;
}

// ============================================================
// 公開 API
// ============================================================

/**
 * 觸發裝箱計算（呼叫後端 API）
 *
 * @param {Object} payload  前端 camelCase 格式
 * @returns {Promise<{ taskId, packed, unpacked, utilization }>}  camelCase 格式
 */
export async function packCargo(payload) {
  try {
    // 前端 camelCase → 後端 snake_case
    const requestBody = toSnake(payload);
    const res = await apiClient.post('/api/v1/pack', requestBody);
    // 後端 snake_case → 前端 camelCase
    return toCamel(res.data);
  } catch (err) {
    throw makeFriendlyError(err);
  }
}

/**
 * 查詢歷史結果
 */
export async function getResults(taskId) {
  try {
    const res = await apiClient.get(`/api/v1/results/${taskId}`);
    return toCamel(res.data);
  } catch (err) {
    throw makeFriendlyError(err);
  }
}

/**
 * 本地端裝箱計算（後端不可用時的備援）
 *
 * 介面與 packCargo 完全相同。
 * 透過 store 的 useLocalAlgorithm 開關切換。
 */
export async function packCargoLocal(payload) {
  await new Promise(resolve => setTimeout(resolve, 50));
  return runPackingHeuristic(payload);
}
