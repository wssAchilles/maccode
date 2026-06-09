import { type KeyboardEvent as ReactKeyboardEvent, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { animate, stagger } from 'animejs';
import { Search, X } from 'lucide-react';
import { navItems } from './navigation';

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function CommandPalette() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const wasOpenRef = useRef(false);
  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return navItems;
    }
    return navItems.filter((item) => `${item.label} ${item.detail} ${item.group} ${item.to}`.toLowerCase().includes(normalized));
  }, [query]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setOpen((value) => !value);
      }
      if (event.key === 'Escape') {
        setOpen(false);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  useEffect(() => {
    if (!open) {
      setQuery('');
      setActiveIndex(0);
      if (wasOpenRef.current) {
        triggerRef.current?.focus();
      }
      return;
    }
    wasOpenRef.current = true;
    inputRef.current?.focus();
    if (!prefersReducedMotion() && dialogRef.current) {
      animate(dialogRef.current, { opacity: [0, 1], y: [-10, 0], duration: 180, ease: 'outQuad' });
      animate(dialogRef.current.querySelectorAll('.command-option'), {
        opacity: [0, 1],
        x: [-8, 0],
        delay: stagger(18),
        duration: 180,
        ease: 'outQuad',
      });
    }
  }, [open, filtered.length]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  function go(to: string) {
    navigate(to);
    setOpen(false);
  }

  function keepFocusInsideDialog(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key !== 'Tab' || !dialogRef.current) {
      return;
    }
    const focusable = Array.from(
      dialogRef.current.querySelectorAll<HTMLElement>('button, input, [href], [tabindex]:not([tabindex="-1"])'),
    ).filter((element) => !element.hasAttribute('disabled'));
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (!first || !last) {
      return;
    }
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function onSearchKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((index) => (filtered.length ? (index + 1) % filtered.length : 0));
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((index) => (filtered.length ? (index - 1 + filtered.length) % filtered.length : 0));
    }
    if (event.key === 'Enter' && filtered[activeIndex]) {
      event.preventDefault();
      go(filtered[activeIndex].to);
    }
  }

  return (
    <>
      <button ref={triggerRef} className="command-trigger" type="button" aria-label="打开命令面板" onClick={() => setOpen(true)}>
        <Search size={17} />
      </button>
      {open ? (
        <div className="command-overlay" role="presentation" onMouseDown={() => setOpen(false)}>
          <div
            aria-modal="true"
            aria-labelledby="command-palette-title"
            className="command-dialog"
            ref={dialogRef}
            role="dialog"
            onKeyDown={keepFocusInsideDialog}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <h2 className="visually-hidden" id="command-palette-title">
              命令面板
            </h2>
            <div className="command-dialog-head">
              <span>快速跳转</span>
              <button type="button" aria-label="关闭命令面板" onClick={() => setOpen(false)}>
                <X size={17} />
              </button>
            </div>
            <label className="command-search">
              <Search size={18} />
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={onSearchKeyDown}
                placeholder="搜索页面、指标或工作流"
                aria-activedescendant={filtered[activeIndex] ? `command-option-${filtered[activeIndex].to}` : undefined}
                aria-controls="command-list"
                aria-autocomplete="list"
                aria-label="搜索页面、指标或工作流"
              />
            </label>
            <div className="command-list" id="command-list" role="listbox">
              {filtered.map((item, index) => {
                const Icon = item.icon;
                return (
                  <button
                    aria-selected={index === activeIndex}
                    className="command-option"
                    id={`command-option-${item.to}`}
                    key={item.to}
                    role="option"
                    type="button"
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => go(item.to)}
                  >
                    <Icon size={18} />
                    <span>
                      <strong>{item.label}</strong>
                      <small>{item.group} · {item.detail}</small>
                    </span>
                  </button>
                );
              })}
              {filtered.length === 0 ? <div className="command-empty">没有匹配结果</div> : null}
            </div>
            <div className="command-footer" aria-hidden="true">
              <kbd>↑↓</kbd><span>选择</span>
              <kbd>Enter</kbd><span>打开</span>
              <kbd>Esc</kbd><span>关闭</span>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
