import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { CartRecoveryPage } from '../../pages/CartRecoveryPage';
import { renderWithProviders } from '../render';

describe('CartRecoveryPage', () => {
  it('renders cart abandonment summary, quality evidence, and recovery queue', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CartRecoveryPage />);

    expect(await screen.findByText('购物车流失与召回机会')).toBeInTheDocument();
    expect(await screen.findByText('购物车召回契约 v1')).toBeInTheDocument();
    expect(await screen.findByText(/当前输入窗口不足/)).toBeInTheDocument();
    expect(await screen.findByText('召回动作结构')).toBeInTheDocument();

    await user.click(await screen.findByText('查看召回机会队列明细'));
    expect(await screen.findByRole('table', { name: '购物车召回机会队列' })).toBeInTheDocument();

    await user.click(await screen.findByText('查看商品流失明细'));
    expect(await screen.findByRole('table', { name: '商品购物车流失优先级' })).toBeInTheDocument();

    await user.click(await screen.findByText('查看品类流失明细'));
    expect(await screen.findByRole('table', { name: '品类购物车流失结构' })).toBeInTheDocument();
    expect(await screen.findByText('1005115')).toBeInTheDocument();
  });

  it('lets operators filter by category and recovery action', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CartRecoveryPage />);

    await screen.findByRole('option', { name: 'electronics' });
    await user.selectOptions(await screen.findByLabelText('品类'), 'electronics');
    expect(await screen.findByText('1005115')).toBeInTheDocument();

    await user.selectOptions(await screen.findByLabelText('召回动作'), 'recovery_offer_or_reminder');
    expect((await screen.findAllByText('优惠或提醒召回')).length).toBeGreaterThan(0);
  });
});
