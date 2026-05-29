import { useCargoStore } from '../../store/useCargoStore.js';
import { CONTAINERS } from '../../constants';

export default function UtilizationCard() {
  const utilization = useCargoStore(s => s.utilization);
  const packedItems = useCargoStore(s => s.packedItems);
  const containerType = useCargoStore(s => s.containerType);

  const cont = CONTAINERS[containerType];
  const usedVol = packedItems.reduce((s, p) => s + p.L * p.W * p.H, 0) / 1e9;
  const containerVol = (cont.L * cont.W * cont.H) / 1e9;

  // 利用率顏色：>80% 綠, >60% 黃, 否則紅
  const barColor = utilization > 80 ? '#34c759' :
                   utilization > 60 ? '#ff9500' : '#ff3b30';

  return (
    <div className="metric-card">
      <div className="metric-label">空間利用率</div>
      <div className="metric-value">
        {packedItems.length === 0 ? '—' : `${utilization.toFixed(1)}%`}
      </div>
      <div style={{
        height: 6, background: '#e5e5e7', borderRadius: 3,
        overflow: 'hidden', marginTop: 8,
      }}>
        <div style={{
          height: '100%',
          width: `${utilization}%`,
          background: barColor,
          transition: 'width 0.4s',
        }} />
      </div>
      <div className="metric-sub">
        {packedItems.length === 0
          ? '尚未計算'
          : `${usedVol.toFixed(2)} / ${containerVol.toFixed(2)} m³`}
      </div>
    </div>
  );
}
