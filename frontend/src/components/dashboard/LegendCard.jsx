import { CARGO_TYPES } from '../../constants';

export default function LegendCard() {
  return (
    <div style={{ marginTop: 16 }}>
      <div className="section-label">顏色圖例</div>
      {Object.entries(CARGO_TYPES).map(([key, t]) => (
        <LegendItem key={key} color={t.color} label={t.label} />
      ))}
      <LegendItem
        striped
        label="不可堆疊（條紋）"
      />
    </div>
  );
}

function LegendItem({ color, label, striped }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      fontSize: 12,
      marginBottom: 6,
    }}>
      <div style={{
        width: 14,
        height: 14,
        borderRadius: 3,
        background: striped
          ? 'repeating-linear-gradient(45deg,#aaa,#aaa 3px,#fff 3px,#fff 6px)'
          : color,
      }} />
      {label}
    </div>
  );
}
