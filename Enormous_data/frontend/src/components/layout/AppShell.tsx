import { useEffect, useMemo, useRef, useState } from 'react';
import clsx from 'clsx';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { animate, stagger } from 'animejs';
import {
  BellDot,
  ChevronsRight,
  Circle,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Siren,
  Sparkles,
  X,
} from 'lucide-react';
import { useJob } from '../../api/hooks';
import { CommandPalette } from './CommandPalette';
import { navGroups, navItems } from './navigation';

const shortcutItems = navItems.filter((item) => ['/anomalies', '/lifecycle', '/experiments', '/ops'].includes(item.to));

function getStoredCollapsed() {
  if (typeof window === 'undefined') {
    return false;
  }
  return window.localStorage.getItem('enormous-data-sidebar') === 'collapsed';
}

export function AppShell() {
  const job = useJob();
  const location = useLocation();
  const appMainRef = useRef<HTMLDivElement | null>(null);
  const workspaceRef = useRef<HTMLElement | null>(null);
  const [collapsed, setCollapsed] = useState(getStoredCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);
  const currentPage = useMemo(
    () => navItems.find((item) => (item.to === '/' ? location.pathname === '/' : location.pathname.startsWith(item.to))) ?? navItems[0],
    [location.pathname],
  );

  useEffect(() => {
    window.localStorage.setItem('enormous-data-sidebar', collapsed ? 'collapsed' : 'expanded');
  }, [collapsed]);

  useEffect(() => {
    setMobileOpen(false);
    window.scrollTo({ top: 0 });
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }
    const blocks = workspaceRef.current?.querySelectorAll('section, .data-panel, .metric-card');
    if (!blocks?.length) {
      return;
    }
    animate(blocks, {
      opacity: [0, 1],
      y: [10, 0],
      delay: stagger(22),
      duration: 220,
      ease: 'outQuad',
    });
  }, [location.pathname]);

  return (
    <div className={clsx('app-shell', collapsed && 'is-collapsed', mobileOpen && 'is-mobile-open')}>
      <a className="skip-link" href="#main-workspace">跳到主内容</a>
      <button className="mobile-menu-button" type="button" aria-label="打开导航" onClick={() => setMobileOpen(true)}>
        <Menu size={18} />
      </button>
      <div className="mobile-scrim" role="presentation" onClick={() => setMobileOpen(false)} />
      <aside className="sidebar">
        <div className="sidebar-head">
          <div className="brand-mark">
            <Sparkles size={22} />
            <div className="brand-copy">
              <strong>Enormous Data</strong>
              <span>Spark Commerce Lab</span>
            </div>
          </div>
          <button className="sidebar-close" type="button" aria-label="关闭导航" onClick={() => setMobileOpen(false)}>
            <X size={18} />
          </button>
          <CommandPalette />
        </div>
        <nav aria-label="主导航">
          {navGroups.map((group) => (
            <div className="nav-group" key={group}>
              <span className="nav-group-label">{group}</span>
              {navItems.filter((item) => item.group === group).map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink key={item.to} to={item.to} end={item.to === '/'} title={collapsed ? item.label : undefined}>
                    <Icon size={18} />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>
        <button
          className="collapse-button"
          type="button"
          aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
          aria-pressed={collapsed}
          onClick={() => setCollapsed((value) => !value)}
        >
          {collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
          <span>{collapsed ? '展开' : '收起导航'}</span>
        </button>
        <div className="sidebar-foot">
          <span>Flask API</span>
          <strong><Circle size={9} fill="currentColor" />{job.data?.status ?? 'ready'}</strong>
        </div>
      </aside>
      <div className="app-main" ref={appMainRef}>
        <header className="topbar">
          <div className="breadcrumb-bar" aria-label="当前位置">
            <span>{currentPage.group}</span>
            <ChevronsRight size={15} />
            <strong>{currentPage.label}</strong>
          </div>
          <div className="topbar-actions" aria-label="常用工作流">
            {shortcutItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink className="workflow-chip" key={item.to} to={item.to}>
                  <Icon size={15} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
            <span className="status-pill tone-running"><BellDot size={14} /> {job.data?.status ?? 'ready'}</span>
          </div>
        </header>
        <main className="workspace" id="main-workspace" ref={workspaceRef} tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
