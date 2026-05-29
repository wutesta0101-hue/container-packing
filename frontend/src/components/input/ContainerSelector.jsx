import { useCargoStore } from '../../store/useCargoStore.js';
import { CONTAINERS, FORKLIFTS } from '../../constants';

export default function ContainerSelector() {
  const containerType = useCargoStore(s => s.containerType);
  const forkliftType = useCargoStore(s => s.forkliftType);
  const setContainer = useCargoStore(s => s.setContainer);
  const setForklift = useCargoStore(s => s.setForklift);

  return (
    <div className="section">
      <div className="section-label">1. 選擇貨櫃</div>
      <select value={containerType} onChange={e => setContainer(e.target.value)}>
        {Object.entries(CONTAINERS).map(([key, c]) => (
          <option key={key} value={key}>
            {c.name} ({c.L} × {c.W} × {c.H} mm, {c.maxWeight} kg)
          </option>
        ))}
      </select>

      <div className="section-label" style={{ marginTop: 12 }}>
        堆高機型號（決定通道寬度）
      </div>
      <select value={forkliftType} onChange={e => setForklift(e.target.value)}>
        {Object.entries(FORKLIFTS).map(([key, f]) => (
          <option key={key} value={key}>
            {f.name} ({f.L} × {f.W} mm, {f.capacity / 1000}t)
          </option>
        ))}
      </select>

      <div style={{ fontSize: 11, color: '#86868b', marginTop: 6, lineHeight: 1.5 }}>
        💡 裝箱會「由內到外」進行 — 堆高機從貨櫃出口進入，故先放最內側貨物，避免擋住通道
      </div>
    </div>
  );
}
