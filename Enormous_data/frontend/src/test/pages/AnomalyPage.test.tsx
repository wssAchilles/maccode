import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AnomalyPage } from '../../pages/AnomalyPage';
import { renderWithProviders } from '../render';

describe('AnomalyPage', () => {
  it('renders anomaly radar summary, rules, timeline, and alert evidence', async () => {
    renderWithProviders(<AnomalyPage />);

    expect(await screen.findByText('运营异常雷达')).toBeInTheDocument();
    expect(await screen.findByText('ops-anomaly-radar/v1')).toBeInTheDocument();
    expect(await screen.findByText('category_revenue_spike')).toBeInTheDocument();
    expect(await screen.findByText('critical_robust_z')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '异常告警证据' })).toBeInTheDocument();
  });
});
