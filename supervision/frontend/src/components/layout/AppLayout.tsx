import type { ReactNode } from "react";

import { Header } from "./Header";
import { Sidebar, type PageKey } from "./Sidebar";

interface AppLayoutProps {
  activePage: PageKey;
  children: ReactNode;
  onPageChange: (page: PageKey) => void;
  status: "demo" | "live" | "error";
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
