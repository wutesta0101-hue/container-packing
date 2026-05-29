import { useRef, useState } from 'react';
import Papa from 'papaparse';
import { useCargoStore } from '../../store/useCargoStore.js';

export default function CsvDropzone() {
  const inputRef = useRef(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const importCsvCargo = useCargoStore(s => s.importCsvCargo);
  const loadSampleData = useCargoStore(s => s.loadSampleData);

  const parseCsvFile = (file) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: ({ data }) => {
        const rows = data
          .filter(r => r.id)
          .map(r => ({
            id: String(r.id).trim(),
            type: r.type || 'normal',
            L: +r.length, W: +r.width, H: +r.height,
            weight: +r.weight,
            quantity: +(r.quantity || 1),
            stackable: r.stackable !== 'false',
            rotatable: r.rotatable !== 'false',
          }));
        importCsvCargo(rows);
        alert(`成功匯入 ${rows.length} 筆`);
      },
      error: (err) => alert(`解析失敗：${err.message}`),
    });
  };

  return (
    <div className="section">
      <div className="section-label">2b. CSV 匯入</div>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          if (e.dataTransfer.files.length) parseCsvFile(e.dataTransfer.files[0]);
        }}
        style={{
          border: `2px dashed ${isDragOver ? '#0071e3' : '#d2d2d7'}`,
          borderRadius: 8,
          padding: 20,
          textAlign: 'center',
          cursor: 'pointer',
          background: isDragOver ? '#f0f7ff' : '#fafafa',
          transition: 'all 0.2s',
        }}
      >
        <div style={{ fontSize: 13, color: '#6e6e73' }}>
          📁 拖曳 CSV 檔到此 或 點擊選檔
        </div>
        <div style={{ fontSize: 11, color: '#86868b', marginTop: 4 }}>
          欄位：id, type, length, width, height, weight, quantity, stackable, rotatable
        </div>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        style={{ display: 'none' }}
        onChange={(e) => e.target.files?.length && parseCsvFile(e.target.files[0])}
      />
      <button
        className="btn btn-secondary btn-block"
        style={{ marginTop: 8 }}
        onClick={loadSampleData}
      >
        載入範例資料
      </button>
    </div>
  );
}
