import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ForecastingPage } from '../../pages/ForecastingPage';
import { renderWithProviders } from '../render';

vi.mock('../../components/ChartPanel', () => ({
  ChartPanel: ({ title, subtitle }: { title: string; subtitle: string }) => (
    <section aria-label={title}>
      <h2>{title}</h2>
      <p>{subtitle}</p>
    </section>
  ),
}));

describe('ForecastingPage', () => {
  it('renders sparse forecasting status, quality checks, and risk evidence', async () => {
    renderWithProviders(<ForecastingPage />);

    expect(await screen.findByText('需求预测与营收风险')).toBeInTheDocument();
    expect(await screen.findByText('demand-forecasting/v1')).toBeInTheDocument();
    expect(await screen.findAllByText('needs_review')).toHaveLength(1);
    expect(await screen.findByText(/sparse baseline fallback/)).toBeInTheDocument();
    expect(await screen.findByText('minimum_history_days')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '实体预测与风险队列' })).toBeInTheDocument();
    expect((await screen.findAllByText('sparse_baseline_fallback')).length).toBeGreaterThan(0);
    expect(await screen.findByText('insufficient_history')).toBeInTheDocument();
  });

  it('lets operators switch forecast entity from the risk queue', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ForecastingPage />);

    await user.click(await screen.findByRole('button', { name: '类目 · electronics' }));

    expect((await screen.findAllByText('类目 · electronics')).length).toBeGreaterThan(0);
    expect(await screen.findByText('¥1,176,000')).toBeInTheDocument();
  });
});
