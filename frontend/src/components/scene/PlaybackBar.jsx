import { useEffect, useRef } from 'react';
import { useCargoStore } from '../../store/useCargoStore.js';

/**
 * 底部播放控制列
 * - 時間軸：拖拉檢視第 N 件被放入的瞬間
 * - 播放鍵：自動 200ms 一格往前播
 * - X 光模式：切換所有箱子半透明
 */
export default function PlaybackBar() {
  const packedItems = useCargoStore(s => s.packedItems);
  const currentStep = useCargoStore(s => s.currentStep);
  const isPlaying = useCargoStore(s => s.isPlaying);
  const xrayMode = useCargoStore(s => s.xrayMode);
  const setStep = useCargoStore(s => s.setStep);
  const togglePlay = useCargoStore(s => s.togglePlay);
  const toggleXray = useCargoStore(s => s.toggleXray);

  // 播放動畫
  const intervalRef = useRef(null);
  useEffect(() => {
    if (!isPlaying) {
      clearInterval(intervalRef.current);
      return;
    }
    if (currentStep >= packedItems.length) {
      setStep(0); // 從頭開始
    }
    intervalRef.current = setInterval(() => {
      const cur = useCargoStore.getState().currentStep;
      const total = useCargoStore.getState().packedItems.length;
      if (cur >= total) {
        clearInterval(intervalRef.current);
        useCargoStore.setState({ isPlaying: false });
        return;
      }
      setStep(cur + 1);
    }, 200);
    return () => clearInterval(intervalRef.current);
  }, [isPlaying, packedItems.length, currentStep, setStep]);

  const total = packedItems.length;

  return (
    <div style={{
      position: 'absolute',
      bottom: 16, left: 16, right: 16,
      background: 'rgba(255,255,255,0.95)',
      backdropFilter: 'blur(10px)',
      borderRadius: 10,
      padding: '12px 16px',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      zIndex: 10,
    }}>
      <button
        onClick={togglePlay}
        disabled={total === 0}
        style={{
          background: '#0071e3',
          color: 'white',
          border: 'none',
          width: 32, height: 32,
          borderRadius: '50%',
          cursor: total === 0 ? 'not-allowed' : 'pointer',
          opacity: total === 0 ? 0.4 : 1,
          fontSize: 14,
        }}
      >
        {isPlaying ? '⏸' : '▶'}
      </button>

      <input
        type="range"
        min="0"
        max={total}
        value={currentStep}
        onChange={(e) => setStep(+e.target.value)}
        style={{ flex: 1, height: 6 }}
        disabled={total === 0}
      />

      <span style={{ fontSize: 12, color: '#6e6e73', minWidth: 70 }}>
        {currentStep} / {total}
      </span>

      <button
        onClick={toggleXray}
        style={{
          background: xrayMode ? '#0071e3' : '#f5f5f7',
          color: xrayMode ? 'white' : '#1d1d1f',
          border: `1px solid ${xrayMode ? '#0071e3' : '#d2d2d7'}`,
          padding: '4px 10px',
          borderRadius: 4,
          fontSize: 11,
          cursor: 'pointer',
        }}
      >
        👁 X 光模式
      </button>
    </div>
  );
}
