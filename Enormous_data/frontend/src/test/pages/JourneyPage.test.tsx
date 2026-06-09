import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { JourneyPage } from '../../pages/JourneyPage';
import { renderWithProviders } from '../render';

describe('JourneyPage', () => {
  it('renders journey summary, transitions, exits, and path tables', async () => {
    renderWithProviders(<JourneyPage />);

    expect(await screen.findByText('用户旅程路径智能')).toBeInTheDocument();
    expect(await screen.findByText('customer-journey-intelligence/v1')).toBeInTheDocument();
    expect(await screen.findByText('cart → purchase')).toBeInTheDocument();
    expect(await screen.findByText('remove_from_cart')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '用户旅程高频路径' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '购买前路径' })).toBeInTheDocument();
    expect((await screen.findAllByText('view → cart → purchase')).length).toBeGreaterThan(0);
  });
});
