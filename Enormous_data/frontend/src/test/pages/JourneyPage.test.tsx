import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { JourneyPage } from '../../pages/JourneyPage';
import { renderWithProviders } from '../render';

describe('JourneyPage', () => {
  it('renders journey summary, transitions, exits, and path tables', async () => {
    renderWithProviders(<JourneyPage />);

    expect(await screen.findByText('用户旅程路径智能')).toBeInTheDocument();
    expect(await screen.findByText('旅程路径契约 v1')).toBeInTheDocument();
    expect(await screen.findByText('加购 → 购买')).toBeInTheDocument();
    expect(await screen.findByText('移出购物车')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '用户旅程高频路径' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '购买前路径' })).toBeInTheDocument();
    expect((await screen.findAllByText('浏览 → 加购 → 购买')).length).toBeGreaterThan(0);
  });
});
