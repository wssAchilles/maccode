import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { CohortsPage } from '../../pages/CohortsPage';
import { renderWithProviders } from '../render';

describe('CohortsPage', () => {
  it('renders cohort summary, retention matrix, intervals, value curves, and risk queue', async () => {
    renderWithProviders(<CohortsPage />);

    expect(await screen.findByText('留存复购与分群经营分析')).toBeInTheDocument();
    expect(await screen.findByText('分群经营契约 v1')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '留存分群矩阵' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '复购间隔分布' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '分群价值曲线' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '留存分群类目风险队列' })).toBeInTheDocument();
    expect(await screen.findByText('最小分群用户数')).toBeInTheDocument();
    expect(await screen.findByText('复购率偏低、稀疏留存分群')).toBeInTheDocument();
  });

  it('lets operators switch the retention metric and filter category risk', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CohortsPage />);

    await user.selectOptions(await screen.findByLabelText('矩阵指标'), 'revenue');
    expect((await screen.findAllByText('¥184,200.5')).length).toBeGreaterThan(0);

    await user.type(await screen.findByLabelText('类目风险'), 'apparel');
    expect(await screen.findByText('可作为复购经营的基准分群。')).toBeInTheDocument();
  });
});
