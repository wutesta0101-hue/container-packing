import { useCargoStore } from '../../store/useCargoStore.js';
import { VIEW_MODES, VIEW_LABELS } from '../../constants';

/**
 * 視角切換按鈕（右上角）
 *
 * 按鈕只更新 store 的 viewMode，實際的相機跳轉由 Container3D 訂閱 store
 * 變化後處理（applyViewMode 函式）
 */
export default function ViewControls() {
  const viewMode = useCargoStore(s => s.viewMode);
  const setViewMode = useCargoStore(s => s.setViewMode);

  return (
    <div style={{
      position: 'absolute',
      top: 16,
      right: 16,
      display: 'flex',
      gap: 6,
      zIndex: 10,
    }}>
      {VIEW_MODES.map(mode => (
        <button
          key={mode}
          onClick={() => setViewMode(mode)}
          style={{
            background: viewMode === mode ? '#0071e3' : 'rgba(255,255,255,0.9)',
            color: viewMode === mode ? 'white' : '#1d1d1f',
            border: 'none',
            padding: '6px 12px',
            borderRadius: 4,
            fontSize: 12,
            cursor: 'pointer',
            fontWeight: 500,
          }}
        >
          {VIEW_LABELS[mode]}
        </button>
      ))}
    </div>
  );
}
