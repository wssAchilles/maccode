import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { LifecyclePage } from '../../pages/LifecyclePage';
import { renderWithProviders } from '../render';

describe('LifecyclePage', () => {
  it('renders lifecycle summary, segments, risk queue, and category affinity', async () => {
    renderWithProviders(<LifecyclePage />);

    expect(await screen.findByText('用户生命周期与价值分层')).toBeInTheDocument();
    expect(await screen.findByText('customer-lifecycle-intelligence/v1')).toBeInTheDocument();
    expect(await screen.findByText('536017300')).toBeInTheDocument();
    expect((await screen.findAllByText('high_value')).length).toBeGreaterThan(0);
    expect(await screen.findByRole('table', { name: '用户生命周期运营动作队列' })).toBeInTheDocument();
  });
});
