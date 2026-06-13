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
    expect(await screen.findByText('需求预测契约 v1')).toBeInTheDocument();
    expect(await screen.findAllByText('需复核')).toHaveLength(1);
    expect(await screen.findByText(/稀疏基线兜底/)).toBeInTheDocument();
    expect(await screen.findByText('最小历史天数')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '实体预测与风险队列' })).toBeInTheDocument();
    expect((await screen.findAllByText('稀疏基线回退')).length).toBeGreaterThan(0);
    expect(await screen.findByText('历史不足')).toBeInTheDocument();
  });

  it('lets operators switch forecast entity from the risk queue', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ForecastingPage />);

    await user.click(await screen.findByRole('button', { name: '类目 · electronics' }));

    expect((await screen.findAllByText('类目 · electronics')).length).toBeGreaterThan(0);
    expect(await screen.findByText('¥1,176,000')).toBeInTheDocument();
  });
});
