import { useCargoStore } from '../../store/useCargoStore.js';
import { CARGO_TYPES } from '../../constants';

export default function CargoList() {
  const cargoList = useCargoStore(s => s.cargoList);
  const removeCargo = useCargoStore(s => s.removeCargo);
  const clearAll = useCargoStore(s => s.clearAll);

  return (
    <div className="section">
      <div className="section-label">
        3. 貨物清單{' '}
        <span style={{ color: '#0071e3' }}>({cargoList.length})</span>
      </div>

      <div style={{ maxHeight: 280, overflowY: 'auto', marginTop: 8 }}>
        {cargoList.length === 0 ? (
          <div style={{
            textAlign: 'center', color: '#86868b',
            fontSize: 12, padding: 20,
          }}>
            尚無貨物
          </div>
        ) : (
          cargoList.map((c, i) => (
            <div
              key={`${c.id}-${i}`}
              style={{
                background: '#f5f5f7',
                borderRadius: 6,
                padding: '8px 10px',
                marginBottom: 6,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 12 }}>
                  {c.id} <span style={{ color: '#86868b' }}>×{c.quantity}</span>
                </div>
                <div style={{ color: '#6e6e73', fontSize: 11, marginTop: 2 }}>
                  {c.L}×{c.W}×{c.H}mm · {c.weight}kg ·{' '}
                  {CARGO_TYPES[c.type]?.label || c.type}
                  {!c.stackable && ' · 不可堆疊'}
                </div>
              </div>
              <button
                className="btn btn-danger"
                onClick={() => removeCargo(i)}
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>

      {cargoList.length > 0 && (
        <button
          className="btn btn-secondary btn-block"
          style={{ marginTop: 8, fontSize: 12 }}
          onClick={() => {
            if (confirm('確定清空全部貨物？')) clearAll();
          }}
        >
          清空全部
        </button>
      )}
    </div>
  );
}
