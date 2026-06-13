import clsx from 'clsx';
import { BellDot } from 'lucide-react';
import type { ReactNode } from 'react';
import { statusLabel } from '../i18n/displayText';

type LocalizedStatusPillProps = {
  status?: string | null;
  tone?: string;
  className?: string;
  icon?: ReactNode;
  ariaLabel?: string;
};

export function LocalizedStatusPill({ status, tone, className, icon, ariaLabel }: LocalizedStatusPillProps) {
  const text = statusLabel(status);

  return (
    <span className={clsx('status-pill', tone && `tone-${tone}`, className)} aria-label={ariaLabel ?? `状态：${text}`}>
      {icon ?? <BellDot size={14} />}
      {text}
    </span>
  );
}
