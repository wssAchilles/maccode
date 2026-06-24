import userEvent from '@testing-library/user-event';
import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../render';
import { OptimizationPage } from '../../pages/OptimizationPage';
import { envelope, optimizationPlanFixture } from '../../mocks/fixtures';
import { server } from '../server';

describe('OptimizationPage', () => {
  it('renders solver status and category coverage without listing every product', async () => {
    const user = userEvent.setup();
    renderWithProviders(<OptimizationPage />);

    expect(await screen.findByText('促销预算与推荐位优化')).toBeInTheDocument();
    expect(await screen.findByText('最优')).toBeInTheDocument();
    expect(await screen.findAllByText('推荐位加权')).toHaveLength(2);
    expect(await screen.findByText('1004856')).toBeInTheDocument();
    expect(await screen.findByText('类目覆盖矩阵')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /apparel/ })).toBeInTheDocument();
    expect(await screen.findByText('未进入候选')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /apparel/ }));

    expect(await screen.findByText('apparel 代表商品')).toBeInTheDocument();
    expect(await screen.findByText('该类目当前批次没有代表商品，说明它未进入本轮候选池或优化缓存尚未生成。')).toBeInTheDocument();
  });

  it('shows every selected product before adding candidate examples', async () => {
    const plan = Array.from({ length: 6 }, (_, index) => ({
      ...optimizationPlanFixture[index % optimizationPlanFixture.length],
      product_id: `selected-${index + 1}`,
      action: index === 5 ? 'promo_low' : 'feature_slot',
      action_type: index === 5 ? 'promo' : 'slot',
    }));
    server.use(http.get('/api/v1/optimization/plan', () => HttpResponse.json(envelope(plan))));

    renderWithProviders(<OptimizationPage />);

    expect(await screen.findByText('selected-1')).toBeInTheDocument();
    expect(await screen.findByText('selected-6')).toBeInTheDocument();
    expect(await screen.findByText('promo_low')).toBeInTheDocument();
  });
});
