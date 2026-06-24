import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { CohortsPage } from '../../pages/CohortsPage';
import { renderWithProviders } from '../render';

describe('CohortsPage', () => {
  it('renders cohort summary, retention matrix, intervals, value curves, and risk queue', async () => {
    renderWithProviders(<CohortsPage />);

    expect(await screen.findByText('留存复购与分群经营分析')).toBeInTheDocument();
    expect(await screen.findByRole('region', { name: '留存复购首屏控制台' })).toBeInTheDocument();
    expect(await screen.findByText('首屏分群工作台')).toBeInTheDocument();
    expect(await screen.findByText('先回答问题，再看证据')).toBeInTheDocument();
    expect(await screen.findByText('我现在看的是谁？')).toBeInTheDocument();
    expect(await screen.findByText('这些卡片到底代表什么？')).toBeInTheDocument();
    expect(await screen.findByText('分群经营契约 v1')).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '留存分群矩阵' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '复购间隔分布' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '分群价值曲线' })).toBeInTheDocument();
    expect(await screen.findByRole('table', { name: '留存分群类目风险队列' })).toBeInTheDocument();
    expect(await screen.findByText('分群覆盖工作台')).toBeInTheDocument();
    expect(await screen.findByText('首购分群矩阵')).toBeInTheDocument();
    expect(await screen.findByText('复购区间覆盖')).toBeInTheDocument();
    expect(await screen.findByText('类目风险覆盖')).toBeInTheDocument();
    expect((await screen.findAllByText('两月后复购')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('长期复购')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('高风险')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('健康')).length).toBeGreaterThan(0);
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
