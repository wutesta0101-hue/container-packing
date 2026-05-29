import { useState } from 'react';
import { useCargoStore } from '../../store/useCargoStore.js';
import { CONTAINERS } from '../../constants';

const EMPTY_FORM = {
  id: '', type: 'normal', L: '', W: '', H: '',
  weight: '', quantity: 1, stackable: 'true', rotatable: 'true',
};

export default function CargoForm() {
  const [form, setForm] = useState(EMPTY_FORM);
  const containerType = useCargoStore(s => s.containerType);
  const addCargo = useCargoStore(s => s.addCargo);

  const update = (key, val) => setForm(f => ({ ...f, [key]: val }));

  const handleSubmit = () => {
    const { id, type, L, W, H, weight, quantity, stackable, rotatable } = form;
    if (!id || !L || !W || !H || !weight) {
      alert('請填完所有欄位');
      return;
    }
    const c = CONTAINERS[containerType];
    if (+L > c.L || +W > c.W || +H > c.H) {
      alert(`貨物尺寸 ${L}×${W}×${H} 超過貨櫃內徑 ${c.L}×${c.W}×${c.H}`);
      return;
    }
    addCargo({
      id,
      type,
      L: +L, W: +W, H: +H,
      weight: +weight,
      quantity: +quantity || 1,
      stackable: stackable === 'true',
      rotatable: rotatable === 'true',
    });
    setForm(EMPTY_FORM);
  };

  return (
    <div className="section">
      <div className="section-label">2a. 手動新增貨物</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <input
          type="text" placeholder="貨物 ID"
          value={form.id} onChange={e => update('id', e.target.value)}
        />
        <select value={form.type} onChange={e => update('type', e.target.value)}>
          <option value="normal">一般</option>
          <option value="heavy">重物（深藍）</option>
          <option value="fragile">易碎品（橘色）</option>
          <option value="vip">VIP（金色）</option>
        </select>
        <input
          type="number" placeholder="長 (mm)"
          value={form.L} onChange={e => update('L', e.target.value)}
        />
        <input
          type="number" placeholder="寬 (mm)"
          value={form.W} onChange={e => update('W', e.target.value)}
        />
        <input
          type="number" placeholder="高 (mm)"
          value={form.H} onChange={e => update('H', e.target.value)}
        />
        <input
          type="number" placeholder="重量 (kg)"
          value={form.weight} onChange={e => update('weight', e.target.value)}
        />
        <input
          type="number" placeholder="數量" min="1"
          value={form.quantity} onChange={e => update('quantity', e.target.value)}
        />
        <select
          value={form.stackable} onChange={e => update('stackable', e.target.value)}
        >
          <option value="true">可堆疊</option>
          <option value="false">不可堆疊</option>
        </select>
        <select
          value={form.rotatable} onChange={e => update('rotatable', e.target.value)}
        >
          <option value="true">可旋轉（長寬互換）</option>
          <option value="false">不可旋轉（固定方向）</option>
        </select>
        <button
          className="btn btn-primary"
          style={{ gridColumn: 'span 2' }}
          onClick={handleSubmit}
        >
          + 新增到清單
        </button>
      </div>
    </div>
  );
}
