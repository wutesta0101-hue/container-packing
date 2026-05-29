import { useCargoStore } from '../../store/useCargoStore.js';
import { FORKLIFTS } from '../../constants';

export default function DirectionCard() {
  const forkliftType = useCargoStore(s => s.forkliftType);
  const fk = FORKLIFTS[forkliftType];

  return (
    <div
      className="metric-card"
      style={{ background: '#fff4e5', borderLeft: '3px solid #ff9500' }}
    >
      <div className="metric-label" style={{ color: '#b85c00' }}>
        📐 裝載方向
      </div>
      <div style={{
        fontSize: 13,
        color: '#1d1d1f',
        lineHeight: 1.6,
        marginTop: 4,
      }}>
        由內到外（紅色箭頭側為出口）<br />
        <span style={{ color: '#6e6e73', fontSize: 11 }}>
          堆高機：{fk.name}（通道寬 {fk.W} mm）
        </span>
      </div>
    </div>
  );
}
