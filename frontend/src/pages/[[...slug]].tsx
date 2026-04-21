import dynamic from 'next/dynamic';

// SSR disabled to avoid React Router / Next.js hydration conflicts
const App = dynamic(() => import('@/App'), { ssr: false });

export default function CatchAll() {
  return <App />;
}
