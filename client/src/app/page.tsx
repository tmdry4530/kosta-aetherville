import Link from 'next/link';
import { CityPlaceholder } from '@/components/CityPlaceholder';
import { ConnectionBridge } from '@/components/ConnectionBridge';
import { SidePanels } from '@/components/SidePanels';
import { getClientConfig } from '@/lib/config';
import { fetchInitialWorldState } from '@/lib/serverWorldState';

export const dynamic = 'force-dynamic';

interface HomePageProps {
  searchParams?: {
    presenter?: string;
  };
}

export default async function HomePage({ searchParams }: HomePageProps) {
  const config = getClientConfig();
  const initialWorldState = await fetchInitialWorldState(config.orchestratorUrl);
  const presenterMode = searchParams?.presenter === '1' || searchParams?.presenter === 'true';

  return (
    <main className={`shell${presenterMode ? ' presenterShell' : ''}`}>
      <section className="hero">
        <p className="eyebrow">Project Aetherville · Live City Shell</p>
        <h1>RunPod 월드 상태를 렌더링하는 네온 도시 관제실</h1>
        <p className="lede">
          이 클라이언트는 Next.js App Router와 React Three Fiber 기반으로 동작하며,
          기본 상태에서는 mock/replay 친화적인 placeholder city를 렌더링합니다.
        </p>
        <nav className="demoNav" aria-label="Demo fallback routes">
          <Link href="/replay">Replay fallback 열기</Link>
          <Link href="/?presenter=1">Presenter mode</Link>
          <a href="#god-mode-panel">God Mode로 이동</a>
        </nav>
        <dl className="endpointGrid" aria-label="Configured endpoints">
          <div>
            <dt>REST</dt>
            <dd>{config.orchestratorUrl}</dd>
          </div>
          <div>
            <dt>Socket</dt>
            <dd>{config.socketUrl}</dd>
          </div>
        </dl>
      </section>
      <ConnectionBridge
        orchestratorUrl={config.orchestratorUrl}
        socketUrl={config.socketUrl}
        transports={config.socketTransports}
      />
      <section className="sceneColumn" aria-label="Live city state">
        <CityPlaceholder initialWorldState={initialWorldState} />
        <SidePanels orchestratorUrl={config.orchestratorUrl} initialWorldState={initialWorldState} />
      </section>
    </main>
  );
}
