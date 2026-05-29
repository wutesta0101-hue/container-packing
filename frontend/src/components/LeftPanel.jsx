import ContainerSelector from './input/ContainerSelector.jsx';
import CargoForm from './input/CargoForm.jsx';
import CsvDropzone from './input/CsvDropzone.jsx';
import CargoList from './input/CargoList.jsx';
import SummaryPanel from './input/SummaryPanel.jsx';

export default function LeftPanel() {
  return (
    <aside className="panel-left">
      <h1 className="panel-title">📦 貨櫃裝箱系統</h1>
      <ContainerSelector />
      <CargoForm />
      <CsvDropzone />
      <CargoList />
      <SummaryPanel />
    </aside>
  );
}
