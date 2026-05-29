import LeftPanel from './components/LeftPanel.jsx';
import CenterCanvas from './components/CenterCanvas.jsx';
import RightPanel from './components/RightPanel.jsx';

export default function App() {
  return (
    <div className="app-grid">
      <LeftPanel />
      <CenterCanvas />
      <RightPanel />
    </div>
  );
}
