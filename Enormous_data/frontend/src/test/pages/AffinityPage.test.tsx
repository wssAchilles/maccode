import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { AffinityPage } from '../../pages/AffinityPage';
import { renderWithProviders } from '../render';

describe('AffinityPage', () => {
  it('renders affinity summary, graph evidence, opportunities, and quality gates', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AffinityPage />);

    expect(await screen.findByText('商品关系图谱与搭配洞察')).toBeInTheDocument();
    expect(await screen.findByText('图谱证据结论')).toBeInTheDocument();
    expect(await screen.findByText(/真实社区算法和线上策略效果仍需单独评估/)).toBeInTheDocument();
    expect(await screen.findByText('中心商品')).toBeInTheDocument();
    expect(await screen.findByText('商品关系力导向图')).toBeInTheDocument();
    expect(await screen.findByText('中心性排行')).toBeInTheDocument();
    expect(await screen.findByText('关系类型结构')).toBeInTheDocument();
    expect(await screen.findByText('社区边规模')).toBeInTheDocument();
    expect((await screen.findAllByText('有效会话')).length).toBeGreaterThan(0);
    expect(screen.queryByText('eligible_session_count')).not.toBeInTheDocument();
    expect(screen.queryByText('add_bundle_or_complete-the-look_slot')).not.toBeInTheDocument();

    await user.click(await screen.findByText('查看商品节点和关系明细'));
    expect(await screen.findByRole('table', { name: '商品关系边' })).toBeInTheDocument();
    expect(await screen.findAllByText('商品 1004856')).not.toHaveLength(0);
    expect(screen.queryByText('product 1004856')).not.toBeInTheDocument();
    expect((await screen.findAllByText('共同购买')).length).toBeGreaterThan(0);

    await user.click(await screen.findByText('查看搭配、替代和社区证据'));
    expect(await screen.findByRole('table', { name: '搭配与替代机会' })).toBeInTheDocument();
    expect(await screen.findByText('增加组合搭配位')).toBeInTheDocument();
  });

  it('lets operators choose a product node as the graph focus', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AffinityPage />);

    const appleButtons = await screen.findAllByRole('button', { name: /apple 1004767/ });
    await user.click(appleButtons[0]);
    await user.click(await screen.findByText('查看搭配、替代和社区证据'));

    expect(await screen.findByText('1004767 · apple')).toBeInTheDocument();
  });
});
