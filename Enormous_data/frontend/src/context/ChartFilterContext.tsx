import { createContext, useCallback, useContext, useMemo, useState } from 'react';

export type DashboardFilter = {
  field: string;
  value: string;
  label: string;
  sourceChartId: string;
  displayValue?: string;
  sourceLabel?: string;
  operator?: 'eq';
  interactionMode?: 'filter' | 'highlight' | 'drillthrough';
  clearBehavior?: 'show_all' | 'clear_field';
  scope?: 'dashboard' | 'detail';
  affects?: string[];
};

type PieFilter = {
  selectedName: string | null;
  sourceChartId: string;
};

type ChartFilterState = {
  activeFilters: DashboardFilter[];
  applyFilters: (filters: DashboardFilter[]) => void;
  setFilter: (filter: DashboardFilter | null) => void;
  toggleFilter: (filter: DashboardFilter) => void;
  pieFilter: PieFilter;
  setPieFilter: (name: string | null, sourceChartId: string) => void;
  clearFilter: (field?: string) => void;
};

const ChartFilterContext = createContext<ChartFilterState | null>(null);

function normalizeFilter(filter: DashboardFilter): DashboardFilter {
  return {
    operator: 'eq',
    interactionMode: 'filter',
    clearBehavior: 'show_all',
    scope: 'dashboard',
    affects: ['图表高亮', '明细跳转'],
    ...filter,
  };
}

export function ChartFilterProvider({ children }: { children: React.ReactNode }) {
  const [activeFilters, setActiveFilters] = useState<DashboardFilter[]>([]);

  const applyFilters = useCallback((filters: DashboardFilter[]) => {
    setActiveFilters(filters.map(normalizeFilter));
  }, []);

  const setFilter = useCallback((filter: DashboardFilter | null) => {
    setActiveFilters((prev) => {
      if (!filter) return [];
      const others = prev.filter((item) => item.field !== filter.field);
      return [...others, normalizeFilter(filter)];
    });
  }, []);

  const toggleFilter = useCallback((filter: DashboardFilter) => {
    setActiveFilters((prev) => {
      const exists = prev.some(
        (item) => item.field === filter.field && item.value === filter.value && item.sourceChartId === filter.sourceChartId,
      );
      if (exists) {
        return prev.filter((item) => !(item.field === filter.field && item.value === filter.value && item.sourceChartId === filter.sourceChartId));
      }
      return [...prev.filter((item) => item.field !== filter.field), normalizeFilter(filter)];
    });
  }, []);

  const setPieFilter = useCallback((name: string | null, sourceChartId: string) => {
    if (!name) {
      setActiveFilters((prev) => prev.filter((item) => item.field !== 'event_type'));
      return;
    }
    toggleFilter({ field: 'event_type', value: name, label: name, sourceChartId });
  }, [toggleFilter]);

  const clearFilter = useCallback((field?: string) => {
    setActiveFilters((prev) => (field ? prev.filter((item) => item.field !== field) : []));
  }, []);

  const pieFilter = useMemo<PieFilter>(() => {
    const eventFilter = activeFilters.find((item) => item.field === 'event_type');
    return {
      selectedName: eventFilter?.value ?? null,
      sourceChartId: eventFilter?.sourceChartId ?? '',
    };
  }, [activeFilters]);

  const value = useMemo(
    () => ({ activeFilters, applyFilters, setFilter, toggleFilter, pieFilter, setPieFilter, clearFilter }),
    [activeFilters, applyFilters, setFilter, toggleFilter, pieFilter, setPieFilter, clearFilter],
  );

  return <ChartFilterContext.Provider value={value}>{children}</ChartFilterContext.Provider>;
}

export function useChartFilter() {
  const ctx = useContext(ChartFilterContext);
  if (!ctx) {
    throw new Error('useChartFilter must be used within ChartFilterProvider');
  }
  return ctx;
}
