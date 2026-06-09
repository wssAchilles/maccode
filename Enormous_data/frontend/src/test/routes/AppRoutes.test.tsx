import { QueryClientProvider } from '@tanstack/react-query';
import { cleanup, render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { navItems } from '../../components/layout/navigation';
import { AppRoutes, appRoutes } from '../../routes/AppRoutes';
import { createTestQueryClient } from '../render';

vi.mock('../../components/ChartPanel', () => ({
  ChartPanel: ({ title }: { title: string }) => <div role="img" aria-label={title} />,
}));

function renderRoute(path: string) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
});

describe('AppRoutes module registry', () => {
  it('keeps every navigation item backed by a registered route', () => {
    const registeredPaths = new Set(appRoutes.map((route) => route.path));

    expect(navItems.map((item) => item.to).sort()).toEqual([...registeredPaths].sort());
  });

  it.each(navItems)('renders the registered module route: $to', async (item) => {
    renderRoute(item.to);

    const breadcrumb = await screen.findByLabelText('当前位置');
    expect(within(breadcrumb).getByText(item.label)).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
