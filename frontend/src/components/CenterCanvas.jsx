import Container3D from './scene/Container3D.jsx';
import ViewControls from './scene/ViewControls.jsx';
import PlaybackBar from './scene/PlaybackBar.jsx';

export default function CenterCanvas() {
  return (
    <main className="panel-center">
      <Container3D />
      <ViewControls />
      <PlaybackBar />
    </main>
  );
}
