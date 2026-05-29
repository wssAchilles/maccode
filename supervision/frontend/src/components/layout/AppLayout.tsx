import type { ReactNode } from "react";

import { Header } from "./Header";
import { Sidebar, type PageKey } from "./Sidebar";
import type { RealtimeStatus } from "../../hooks/useRealtimeStats";

interface AppLayoutProps {
  activePage: PageKey;
  children: ReactNode;
  onPageChange: (page: PageKey) => void;
  status: RealtimeStatus;
}

export function AppLayout({ activePage, children, onPageChange, status }: AppLayoutProps) {
  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} onPageChange={onPageChange} />
      <main className="workspace">
        <Header status={status} />
        {children}
      </main>
    </div>
  );
}
