import { BarChart3, Bot, History, MapPinned, Radar } from "lucide-react";

export type PageKey = "realtime" | "history" | "zones" | "ai";

interface SidebarProps {
  activePage: PageKey;
  onPageChange: (page: PageKey) => void;
}

const navItems: Array<{ key: PageKey; label: string; icon: typeof Radar }> = [
  { key: "realtime", label: "实时监控", icon: Radar },
  { key: "history", label: "历史分析", icon: History },
  { key: "zones", label: "区域配置", icon: MapPinned },
  { key: "ai", label: "AI 报告", icon: Bot }
];

export function Sidebar({ activePage, onPageChange }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <BarChart3 size={22} />
        <span>TrafficPerceptionEngine</span>
      </div>
      <nav className="nav-list">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              className={item.key === activePage ? "nav-item active" : "nav-item"}
              key={item.key}
              onClick={() => onPageChange(item.key)}
              type="button"
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
