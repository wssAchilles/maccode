import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../render';
import { RecommendationsPage } from '../../pages/RecommendationsPage';

describe('RecommendationsPage', () => {
  it('renders recommendation guardrail metrics and snapshot rows', async () => {
    const user = userEvent.setup();
    renderWithProviders(<RecommendationsPage />);

    expect(await screen.findByText('准实时推荐与监控守护')).toBeInTheDocument();
    expect(await screen.findByText('推荐守护决策中心')).toBeInTheDocument();
    expect((await screen.findAllByText('发布判断')).length).toBeGreaterThan(0);
    expect(await screen.findByText('推荐覆盖')).toBeInTheDocument();
    expect(await screen.findByText('生成快照')).toBeInTheDocument();
    expect((await screen.findAllByText('质量门禁')).length).toBeGreaterThan(0);
    expect(await screen.findByText('发布/回滚')).toBeInTheDocument();
    expect(await screen.findByText(/展开离线评估、图表证据和推荐快照/)).toBeInTheDocument();

    await user.click(await screen.findByText(/展开离线评估、图表证据和推荐快照/));

    expect(await screen.findByText('推荐证据结论')).toBeInTheDocument();
    expect(await screen.findByText('来源筛选与门禁快捷检查')).toBeInTheDocument();
    expect(await screen.findByText(/真实业务提升需要后续随机实验验证/)).toBeInTheDocument();
    expect(await screen.findByText('主召回来源')).toBeInTheDocument();
    expect(await screen.findByText('排序器')).toBeInTheDocument();
    expect((await screen.findAllByText(/当前推荐快照/)).length).toBeGreaterThan(0);
    expect(await screen.findByText('风险原因')).toBeInTheDocument();
    expect((await screen.findAllByText('新鲜度延迟')).length).toBeGreaterThan(0);
    expect(await screen.findByText('模型效果、发布门禁与风险依据')).toBeInTheDocument();
    expect(await screen.findByText('老师可能会问：')).toBeInTheDocument();
    expect(await screen.findByText('风险明细表')).toBeInTheDocument();
    expect(await screen.findByText('前 K 命中矩阵')).toBeInTheDocument();
    expect(await screen.findByText('评估门禁')).toBeInTheDocument();
    expect(await screen.findByText('Precision@K')).toBeInTheDocument();
    expect(await screen.findByText('NDCG@K')).toBeInTheDocument();
    expect(await screen.findByText('召回来源流向')).toBeInTheDocument();
    expect(await screen.findByText('排序分数分布')).toBeInTheDocument();
    expect((await screen.findAllByText(/可解释规则排序器/)).length).toBeGreaterThan(0);
    expect(await screen.findByText('排序贡献结构')).toBeInTheDocument();
    expect(await screen.findByText(/图谱邻居召回/)).toBeInTheDocument();
    expect(await screen.findByText(/亲和分数/)).toBeInTheDocument();
    expect(await screen.findByText('校准分层')).toBeInTheDocument();
    expect((await screen.findAllByText('1004856')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('个性化品类')).length).toBeGreaterThan(0);
    expect(await screen.findByText('发布门禁')).toBeInTheDocument();

    await user.click((await screen.findAllByText('兜底占比'))[0]);
    expect(await screen.findByText('兜底率检查')).toBeInTheDocument();

    await user.click(await screen.findByText('风险下钻'));
    expect(await screen.findByText(/风险结构把兜底/)).toBeInTheDocument();

    await user.click(await screen.findByText('查看推荐快照明细'));
    expect(await screen.findByLabelText('推荐快照滚动区域')).toHaveClass('panel-scroll');
  });
});
