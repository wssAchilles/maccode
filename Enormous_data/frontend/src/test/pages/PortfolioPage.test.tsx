import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { PortfolioPage } from '../../pages/PortfolioPage';
import { renderWithProviders } from '../render';

describe('PortfolioPage', () => {
  it('renders portfolio summary, price-band matrix, quality gates, and opportunity queue', async () => {
    renderWithProviders(<PortfolioPage />);

    expect(await screen.findByText('品类价格带组合经营分析')).toBeInTheDocument();
    expect(await screen.findByText('portfolio-intelligence/v1')).toBeInTheDocument();
    expect(await screen.findByText(/当前输入窗口不足/)).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '价格带组合矩阵' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '品类组合结构' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '组合经营机会队列' })).toBeInTheDocument();
    expect(await screen.findByText('history_days')).toBeInTheDocument();
    expect(await screen.findByText('price_band_revenue_pool')).toBeInTheDocument();
  });

  it('lets operators filter by category and opportunity type', async () => {
    const user = userEvent.setup();
    renderWithProviders(<PortfolioPage />);

    await screen.findByRole('option', { name: 'electronics' });
    await user.selectOptions(await screen.findByLabelText('品类'), 'electronics');
    expect(await screen.findByText('samsung')).toBeInTheDocument();

    await user.selectOptions(await screen.findByLabelText('机会类型'), 'concentration_risk');
    expect((await screen.findAllByText('concentration_risk')).length).toBeGreaterThan(0);
  });
});
