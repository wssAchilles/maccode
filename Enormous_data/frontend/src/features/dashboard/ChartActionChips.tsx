import type { DashboardFilter } from '../../context/ChartFilterContext';

export type ChartActionChip = DashboardFilter & {
  count?: number;
};

type ChartActionChipsProps = {
  label: string;
  chips: ChartActionChip[];
  activeFilters: DashboardFilter[];
  onToggle: (filter: DashboardFilter) => void;
};

export function ChartActionChips({ activeFilters, chips, label, onToggle }: ChartActionChipsProps) {
  if (!chips.length) return null;

  return (
    <div className="chart-action-chips" aria-label={label}>
      {chips.map((chip) => {
        const isActive = activeFilters.some((filter) => filter.field === chip.field && filter.value === chip.value);
        return (
          <button
            type="button"
            className={isActive ? 'active' : ''}
            key={`${chip.field}-${chip.value}`}
            aria-pressed={isActive}
            onClick={() => onToggle(chip)}
          >
            <span>{chip.label}</span>
            {typeof chip.count === 'number' ? <small>{chip.count.toLocaleString('zh-CN')}</small> : null}
          </button>
        );
      })}
    </div>
  );
}
