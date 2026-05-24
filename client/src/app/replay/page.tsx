import { CityPlaceholder } from '@/components/CityPlaceholder';
import { ReplayDriver } from '@/components/ReplayDriver';
import { SidePanels } from '@/components/SidePanels';

export default function ReplayPage() {
  return (
    <main className="shell replayShell">
      <section className="hero replayHero">
        <p className="eyebrow">Project Aetherville · Replay Mode</p>
        <h1>클라우드 없이도 재생되는 도시 상태</h1>
        <p className="lede">
          RunPod 연결이 불안정한 데모 상황에서도 deterministic fallback state를 사용해
          도시, 패널, tick 흐름을 검증합니다.
        </p>
      </section>
      <ReplayDriver />
      <section className="sceneColumn" aria-label="Replay city state">
        <CityPlaceholder />
        <SidePanels />
      </section>
    </main>
  );
}
