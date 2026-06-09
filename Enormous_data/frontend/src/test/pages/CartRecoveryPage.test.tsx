import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { CartRecoveryPage } from '../../pages/CartRecoveryPage';
import { renderWithProviders } from '../render';

describe('CartRecoveryPage', () => {
  it('renders cart abandonment summary, quality evidence, and recovery queue', async () => {
    renderWithProviders(<CartRecoveryPage />);

    expect(await screen.findByText('购物车流失与召回机会')).toBeInTheDocument();
    expect(await screen.findByText('cart-recovery-intelligence/v1')).toBeInTheDocument();
    expect(await screen.findByText(/当前输入窗口不足/)).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '购物车召回机会队列' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '商品购物车流失优先级' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '品类购物车流失结构' })).toBeInTheDocument();
    expect(await screen.findByText('apple / electronics / 1005115')).toBeInTheDocument();
  });

  it('lets operators filter by category and recovery action', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CartRecoveryPage />);

    await screen.findByRole('option', { name: 'electronics' });
    await user.selectOptions(await screen.findByLabelText('品类'), 'electronics');
    expect(await screen.findByText('1005115')).toBeInTheDocument();

    await user.selectOptions(await screen.findByLabelText('召回动作'), 'recovery_offer_or_reminder');
    expect((await screen.findAllByText('recovery_offer_or_reminder')).length).toBeGreaterThan(0);
  });
});
