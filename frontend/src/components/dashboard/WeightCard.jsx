import { useCargoStore } from '../../store/useCargoStore.js';
import { CONTAINERS } from '../../constants';

export default function WeightCard() {
  const packedItems = useCargoStore(s => s.packedItems);
  const unpackedItems = useCargoStore(s => s.unpackedItems);
  const containerType = useCargoStore(s => s.containerType);
  const cont = CONTAINERS[containerType];

  if (packedItems.length === 0) {
    return (
      <>
        <Card label="總重量" value="—" sub="—" />
        <Card label="重心位置 (X, Y, Z)" value="—" sub="—" mono />
        <Card label="已裝入 / 未裝入" value="— / —" sub="—" />
      </>
    );
  }

  const totalWt = packedItems.reduce((s, p) => s + p.weight, 0);
  // 加權重心
  let cx = 0, cy = 0, cz = 0;
  packedItems.forEach(p => {
    cx += (p.x + p.L / 2) * p.weight;
    cy += (p.y + p.W / 2) * p.weight;
    cz += (p.z + p.H / 2) * p.weight;
  });
  cx /= totalWt; cy /= totalWt; cz /= totalWt;

  const xOffset = Math.abs(cx - cont.L / 2) / (cont.L / 2);
  const cogOk = xOffset < 0.15 && cz < cont.H * 0.5;

  const total = packedItems.length + unpackedItems.length;

  return (
    <>
      <Card
        label="總重量"
        value={`${totalWt.toLocaleString()} kg`}
        sub={`上限 ${cont.maxWeight.toLocaleString()} kg · 剩餘 ${(cont.maxWeight - totalWt).toLocaleString()} kg`}
      />
      <Card
        label="重心位置 (X, Y, Z)"
        value={`(${(cx / 1000).toFixed(2)}, ${(cy / 1000).toFixed(2)}, ${(cz / 1000).toFixed(2)}) m`}
        sub={cogOk ? '✓ 重心穩定' : '⚠ 重心偏移，建議調整'}
        subColor={cogOk ? '#34c759' : '#ff9500'}
        mono
        smallValue
      />
      <Card
        label="已裝入 / 未裝入"
        value={`${packedItems.length} / ${total}`}
        sub={unpackedItems.length === 0 ? '✓ 全部裝入' : `${unpackedItems.length} 件未裝入`}
      />
    </>
  );
}

function Card({ label, value, sub, subColor, mono, smallValue }) {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div
        className="metric-value"
        style={{
          fontFamily: mono ? 'monospace' : 'inherit',
          fontSize: smallValue ? 14 : undefined,
        }}
      >
        {value}
      </div>
      <div className="metric-sub" style={{ color: subColor }}>{sub}</div>
    </div>
  );
}
