import UtilizationCard from './dashboard/UtilizationCard.jsx';
import WeightCard from './dashboard/WeightCard.jsx';
import DirectionCard from './dashboard/DirectionCard.jsx';
import LegendCard from './dashboard/LegendCard.jsx';

export default function RightPanel() {
  return (
    <aside className="panel-right">
      <h2 className="panel-title">📊 裝箱結果</h2>
      <UtilizationCard />
      <WeightCard />
      <DirectionCard />
      <LegendCard />
    </aside>
  );
}
