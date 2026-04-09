import { useState, ReactNode } from 'react';
import Header from '@/components/Header/Header';
import Sidebar from '@/components/Sidebar/Sidebar';
import styles from './Layout.module.scss';

interface Props {
  children: ReactNode;
}

export default function Layout({ children }: Props) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className={styles.root}>
      <Header />
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen((v) => !v)} />
      <main className={`${styles.main} ${!sidebarOpen ? styles.mainExpanded : ''}`}>
        {children}
      </main>
    </div>
  );
}
