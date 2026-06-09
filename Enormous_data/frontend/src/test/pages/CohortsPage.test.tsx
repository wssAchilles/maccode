import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { CohortsPage } from '../../pages/CohortsPage';
import { renderWithProviders } from '../render';

describe('CohortsPage', () => {
  it('renders cohort summary, retention matrix, intervals, value curves, and risk queue', async () => {
    renderWithProviders(<CohortsPage />);

    expect(await screen.findByText('留存复购与 Cohort 经营分析')).toBeInTheDocument();
    expect(await screen.findByText('cohort-retention/v1')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: 'Cohort 留存矩阵' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '复购间隔分布' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: 'Cohort 价值曲线' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: 'Cohort 类目风险队列' })).toBeInTheDocument();
    expect(await screen.findByText('min_cohort_users')).toBeInTheDocument();
    expect(await screen.findByText('low_repeat_purchase_rate, sparse_cohort')).toBeInTheDocument();
  });

  it('lets operators switch the retention metric and filter category risk', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CohortsPage />);

    await user.selectOptions(await screen.findByLabelText('矩阵指标'), 'revenue');
    expect((await screen.findAllByText('¥184,200.5')).length).toBeGreaterThan(0);

    await user.type(await screen.findByLabelText('类目风险'), 'apparel');
    expect(await screen.findByText('Use this cohort as a repeat-purchase benchmark.')).toBeInTheDocument();
  });
});
