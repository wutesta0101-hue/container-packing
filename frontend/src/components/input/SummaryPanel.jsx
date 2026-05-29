import { useMemo } from 'react';
import { useCargoStore, computeTotals } from '../../store/useCargoStore.js';
import { CONTAINERS } from '../../constants';

export default function SummaryPanel() {
  // 個別訂閱（每個 selector 只回傳原本就在 store 裡的引用，不是新物件）
  const cargoList = useCargoStore(s => s.cargoList);
  const containerType = useCargoStore(s => s.containerType);
  const isComputing = useCargoStore(s => s.isComputing);
  const computeError = useCargoStore(s => s.computeError);
  const runPacking = useCargoStore(s => s.runPacking);

  // 衍生資料用 useMemo 計算 — 只在 cargoList 或 containerType 變動時重算
  const totals = useMemo(
    () => computeTotals(cargoList, containerType),
    [cargoList, containerType]
  );

  const cont = CONTAINERS[containerType];
  const { totalCount, totalVolume, totalWeight, containerVolume } = totals;

  // 容量警告判斷
  const warnings = [];
  if (totalVolume > containerVolume) {
    warnings.push(
      `⚠️ 總體積 ${totalVolume.toFixed(2)} m³ 超過貨櫃容積 ${containerVolume.toFixed(2)} m³` +
      `（超出 ${((totalVolume / containerVolume - 1) * 100).toFixed(1)}%）`
    );
  } else if (totalVolume > containerVolume * 0.85) {
    warnings.push(
      `📐 體積已達貨櫃 ${(totalVolume / containerVolume * 100).toFixed(1)}%，` +
      `實際裝載率約 75-85%（受擺放限制）`
    );
  }
  if (totalWeight > cont.maxWeight) {
    warnings.push(
      `⚠️ 總重量 ${totalWeight.toLocaleString()} kg 超過貨櫃最大載重 ` +
      `${cont.maxWeight.toLocaleString()} kg`
    );
  }
  const isDanger = totalVolume > containerVolume || totalWeight > cont.maxWeight;

  return (
    <div className="section">
      <div className="section-label">4. 確認與計算</div>

      {warnings.length > 0 && (
        <div style={{
          padding: '10px 12px',
          borderRadius: 6,
          fontSize: 12,
          marginBottom: 12,
          background: isDanger ? '#ffe5e5' : '#fff4e5',
          color: isDanger ? '#c00' : '#b85c00',
          border: `1px solid ${isDanger ? '#ffb8b8' : '#ffd9a8'}`,
          lineHeight: 1.5,
        }}>
          {warnings.map((w, i) => <div key={i}>{w}</div>)}
        </div>
      )}

      <div style={{
        background: '#f5f5f7',
        borderRadius: 8,
        padding: 12,
        marginBottom: 12,
      }}>
        <SummaryRow label="總件數：" value={`${totalCount} 件`} />
        <SummaryRow label="總體積：" value={`${totalVolume.toFixed(2)} m³`} />
        <SummaryRow label="總重量：" value={`${totalWeight.toLocaleString()} kg`} />
        <SummaryRow label="貨櫃容積：" value={`${containerVolume.toFixed(2)} m³`} />
      </div>

      {computeError && (
        <div style={{ color: '#c00', fontSize: 12, marginBottom: 8 }}>
          {computeError}
        </div>
      )}

      <button
        className="btn btn-success btn-block"
        onClick={runPacking}
        disabled={isComputing}
      >
        {isComputing ? '計算中...' : '🚀 開始裝箱計算'}
      </button>
    </div>
  );
}

function SummaryRow({ label, value }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      fontSize: 13,
      marginBottom: 4,
    }}>
      <span style={{ color: '#6e6e73' }}>{label}</span>
      <span style={{ fontWeight: 600 }}>{value}</span>
    </div>
  );
}
