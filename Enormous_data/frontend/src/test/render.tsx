import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderOptions } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter } from 'react-router-dom';

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

type RenderWithProvidersOptions = RenderOptions & {
  route?: string;
};

export function renderWithProviders(ui: ReactElement, options?: RenderWithProvidersOptions) {
  const queryClient = createTestQueryClient();
  const { route = '/', ...renderOptions } = options ?? {};
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
    renderOptions,
  );
}
