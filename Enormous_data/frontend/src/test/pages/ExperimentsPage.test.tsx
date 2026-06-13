import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ExperimentsPage } from '../../pages/ExperimentsPage';
import { renderWithProviders } from '../render';

describe('ExperimentsPage', () => {
  it('renders experimentation summary, catalog, guardrails, and assignments', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ExperimentsPage />);

    expect(await screen.findByText('策略实验与效果评估')).toBeInTheDocument();
    expect(await screen.findByText('实验评估结论')).toBeInTheDocument();
    expect(await screen.findByText('离线回放')).toBeInTheDocument();
    expect((await screen.findAllByText(/不宣称真实因果提升/)).length).toBeGreaterThan(0);
    expect(await screen.findByText('因果状态')).toBeInTheDocument();
    expect(await screen.findByText('分流样本结构')).toBeInTheDocument();
    expect(await screen.findByText('样本比例失衡门禁')).toBeInTheDocument();
    expect(await screen.findByText('效果森林图')).toBeInTheDocument();
    expect(await screen.findByText('增量提升分位')).toBeInTheDocument();
    expect(await screen.findByText('累计增益曲线')).toBeInTheDocument();
    expect(await screen.findByText('离线估计仅作为规划先验，真实提升必须通过随机对照实验验证。')).toBeInTheDocument();
    expect(await screen.findByText('真实增量提升需要随机曝光、对照组和结果回流后才能判断。')).toBeInTheDocument();
    expect((await screen.findAllByText('生命周期再激活策略')).length).toBeGreaterThan(0);
    expect(await screen.findByText('最小分流用户数')).toBeInTheDocument();
    expect(screen.queryByText('min_assignment_users')).not.toBeInTheDocument();

    await user.click(await screen.findByText('查看分层均衡和实验结果明细'));
    expect(await screen.findByRole('table', { name: '实验分层均衡' })).toBeInTheDocument();
    expect((await screen.findAllByText('实验组')).length).toBeGreaterThan(0);

    await user.click(await screen.findByText('查看分流样本'));
    expect(await screen.findByRole('table', { name: '实验分流样本' })).toBeInTheDocument();
    expect(await screen.findByText('558295000')).toBeInTheDocument();
  });
});
