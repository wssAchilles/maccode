import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { AffinityPage } from '../../pages/AffinityPage';
import { renderWithProviders } from '../render';

describe('AffinityPage', () => {
  it('renders affinity summary, graph evidence, opportunities, and quality gates', async () => {
    renderWithProviders(<AffinityPage />);

    expect(await screen.findByText('商品关系图谱与搭配洞察')).toBeInTheDocument();
    expect(await screen.findByText('product-affinity-graph/v1')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '商品关系边' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '搭配与替代机会' })).toBeInTheDocument();
    expect(await screen.findByText('eligible_session_count')).toBeInTheDocument();
    expect(await screen.findByText('add_bundle_or_complete-the-look_slot')).toBeInTheDocument();
    expect((await screen.findAllByText('共购')).length).toBeGreaterThan(0);
  });

  it('lets operators choose a product node as the graph focus', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AffinityPage />);

    await user.click(await screen.findByRole('button', { name: /product 1004767/ }));

    expect(await screen.findByText('1004767 · apple')).toBeInTheDocument();
  });
});
